"""Reproducible closeout build. Never rewrites legacy V1 artifacts or gold labels."""
from __future__ import annotations
import argparse, dataclasses, json, os, platform, subprocess, sys, time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from .common import ROUTES, SEED, dump_json, load_json, sha256, normalize, family_id, family_text
from .review import integrate_review
from .modeling import fit_model, group_splits, probabilities, RoutingPolicy, policy_rule
from .metrics import calculate, gates, selection_key, save_evaluation, paired_accuracy_interval
from .runtime import Resolver
from .verification import verify_runtime


def snapshot(folder:Path) -> dict:
    return {str(p.relative_to(folder)):sha256(p) for p in sorted(folder.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}

def timed_decisions(model,policy,queries):
    probabilities(model,["college search"])
    ps=[]; decisions=[]; lat=[]
    for q in queries:
        start=time.perf_counter()
        p=probabilities(model,[q])[0]
        decision=policy.decide(q,p)
        lat.append((time.perf_counter()-start)*1000)
        ps.append(p); decisions.append(decision)
    return pd.DataFrame(decisions),np.asarray(ps),lat

def method_info():
    return {"python":sys.version,"platform":platform.platform(),"processor":platform.processor(),
            "scikit_learn":sklearn.__version__,"numpy":np.__version__,"pandas":pd.__version__,
            "OMP_NUM_THREADS":os.environ.get("OMP_NUM_THREADS"),"git_source_sha":os.environ.get("GITHUB_SHA"),
            "workflow_run_id":os.environ.get("GITHUB_RUN_ID"),
            "cost":"No external model API calls are made. CPU/hosting and downstream costs are not measured; zero token calls is not zero total operating cost."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",type=Path,default=Path.cwd())
    args=parser.parse_args()
    repo=args.repo_root.resolve(); root=repo/"v1_1"; out=root/"artifacts"
    out.mkdir(parents=True,exist_ok=True)
    base=repo/"v1"; frozen=base/"artifacts"/"benchmark"
    baseline=snapshot(base)
    protocol=load_json(root/"config"/"protocol.json")
    if sha256(frozen/"benchmark_gold.csv")!=protocol["frozen_benchmark_sha256"]:
        raise ValueError("The historical benchmark hash differs from the declared protocol")
    app_manifest=load_json(root/"data"/"applicability_manifest.json")
    if sha256(root/"data"/"applicability_v1.jsonl")!=app_manifest["sha256"]:
        raise ValueError("Applicability suite changed after its freeze")
    reviewed,review=integrate_review(root/"data"/"manual_review_received.csv",base/"artifacts/data_cleanup/manual_review_queue.csv",
                                    frozen/"training_clean.csv",frozen/"benchmark_queries.csv",out/"data")
    blind=pd.read_csv(frozen/"benchmark_queries.csv",dtype=str,keep_default_na=False)
    benchmark_families=set(blind.query_text.map(family_id))
    reviewed["family_id"]=reviewed.query_text.map(family_id)
    reviewed["family_text"]=reviewed.query_text.map(family_text)
    excluded=reviewed.family_id.isin(benchmark_families)
    training=reviewed[~excluded].reset_index(drop=True)
    reviewed[excluded].to_csv(out/"data"/"excluded_benchmark_families.csv",index=False)
    training.to_csv(out/"data"/"training_strict.csv",index=False)
    if set(training.route)!=set(ROUTES):
        raise ValueError("Strict family exclusion leaves an unsupported class; stop rather than relax the evaluation")
    integrity={"legacy_files_sha256":baseline,"benchmark_sha256":sha256(frozen/"benchmark_gold.csv"),
               "blind_queries_sha256":sha256(frozen/"benchmark_queries.csv"),"reviewed_training_rows":len(reviewed),
               "strict_training_rows":len(training),"excluded_family_rows":int(excluded.sum()),
               "strict_training_distribution":training.route.value_counts().to_dict(),
               "reviewed_examples_retained_in_strict_training":int(training.label_source.ne("legacy_cleaned_corpus").sum()),
               "unique_training_families":int(training.family_id.nunique()),"legacy_template_overlap_families":len(set(reviewed.loc[reviewed.label_source.eq("legacy_cleaned_corpus"),"family_id"])&benchmark_families),
               "strict_template_overlap_families":0,"exact_overlap":0,
               "family_definition":"Fixed school/program/place/number lexical normalization. Zero overlap under this heuristic is not proof of zero semantic similarity."}
    dump_json(out/"data"/"integrity.json",integrity)
    dump_json(out/"environment.json",method_info())
    # All selection choices use training OOF only. No applicability labels are read yet.
    splits=group_splits(training,protocol["outer_group_folds"])
    fold_rows=[]
    for fold,(tr,va) in enumerate(splits):
        for idx in va: fold_rows.append({"query_id":training.iloc[idx].query_id,"family_id":training.iloc[idx].family_id,"fold":fold})
    pd.DataFrame(fold_rows).to_csv(out/"data"/"oof_folds.csv",index=False)
    rules=np.array([policy_rule(q) is not None for q in training.query_text])
    nr=int(rules.sum()); kr=int((training.route[rules]=="short_circuit").sum())
    rule_enabled=nr>=30 and kr/nr>=.95
    rule_conf=(kr+1)/(nr+2) if nr else 0.0
    rule_check={"firings":nr,"correct":kr,"precision":kr/nr if nr else None,"eligible":rule_enabled,"smoothed_confidence":rule_conf,
                "basis":"Training-only check of the preregistered lookup grammar, not a benchmark-tuned exception list."}
    options=[]; per_candidate={}
    for kind in protocol["candidates"]:
        print(f"Grouped OOF candidate: {kind}",flush=True)
        oof=np.full((len(training),len(ROUTES)),np.nan); fold_report=[]
        for fold,(tr,va) in enumerate(splits):
            start=time.perf_counter(); model=fit_model(kind,training.iloc[tr].reset_index(drop=True))
            oof[va]=probabilities(model,training.iloc[va].query_text.to_numpy())
            fold_report.append({"fold":fold,"train_rows":len(tr),"validation_rows":len(va),"fit_predict_seconds":time.perf_counter()-start})
        if not np.isfinite(oof).all(): raise AssertionError("OOF coverage is incomplete")
        path=out/"models"/kind; path.mkdir(parents=True,exist_ok=True)
        pred=training[["query_id","query_text","route","family_id"]].copy()
        for i,r in enumerate(ROUTES): pred["p_"+r]=oof[:,i]
        pred.to_csv(path/"oof_predictions.csv",index=False)
        local=[]
        for use_rules in ([False,True] if rule_enabled else [False]):
            for threshold in protocol["short_circuit_thresholds"]:
                policy=RoutingPolicy(threshold,protocol["global_low_confidence_threshold"],use_rules,rule_conf if use_rules else 0)
                d=policy.apply(training.query_text.tolist(),oof)
                m=calculate(training.route,d.route,d.confidence)
                entry={"model":kind,"policy":dataclasses.asdict(policy),"metrics":m,"gates":gates(m,protocol),"selection_key":list(selection_key(m,protocol))}
                options.append(entry); local.append(entry)
        per_candidate[kind]=max(local,key=lambda e:tuple(e["selection_key"]))
        dump_json(path/"oof_summary.json",{"folds":fold_report,"chosen_policy":per_candidate[kind]})
    selected=max(options,key=lambda e:tuple(e["selection_key"]))
    selection={"selected":selected,"per_candidate":per_candidate,"rule_check":rule_check,
               "protocol_sha256":sha256(root/"config/protocol.json"),"training_sha256":sha256(out/"data/training_strict.csv"),
               "selection_labels":"Only grouped training OOF labels; both evaluation sets remain unopened at this selection point.",
               "historical_benchmark_notice":"Its prior results are known from earlier project work; this run treats it as a regression benchmark, not newly blind evidence."}
    dump_json(out/"selection.json",selection)
    pd.DataFrame([{**{"model":e["model"]},**e["policy"],**{k:e["metrics"][k] for k in ("accuracy","macro_f1","false_short_circuit_rate","short_circuit_recall","predicted_short_circuit_count")},"all_gates":all(e["gates"].values())} for e in options]).to_csv(out/"oof_policy_comparison.csv",index=False)
    selection_hash=sha256(out/"selection.json")
    # No model or threshold choice is made after this point.
    gold=pd.read_csv(frozen/"benchmark_gold.csv",dtype=str,keep_default_na=False)
    suite=pd.read_json(root/"data/applicability_v1.jsonl",lines=True,dtype=False).rename(columns={"suite":"section","test_id":"case_id"})
    if set(gold.query_text.map(family_id))&set(training.family_id): raise AssertionError("Family exclusion did not hold")
    models={}; benchmark_results={}
    for kind in protocol["candidates"]:
        print(f"Final fit and fixed historical evaluation: {kind}",flush=True)
        start=time.perf_counter(); model=fit_model(kind,training)
        models[kind]=model; chosen=per_candidate[kind]
        policy=RoutingPolicy(**chosen["policy"])
        d,p,lat=timed_decisions(model,policy,gold.query_text.tolist())
        m=save_evaluation(out/"models"/kind/"benchmark",gold,d,p,lat)
        m["fit_seconds"]=time.perf_counter()-start
        m["gates"]=gates(m,protocol)
        m["policy_frozen_from_oof"]=chosen["policy"]
        m["selection_sha256"]=selection_hash
        dump_json(out/"models"/kind/"benchmark"/"metrics.json",m)
        benchmark_results[kind]=m
    selected_kind=selected["model"]; final_model=models[selected_kind]
    policy=RoutingPolicy(**selected["policy"])
    release=out/"release"; release.mkdir(parents=True,exist_ok=True)
    joblib.dump(final_model,release/"model.joblib",compress=3)
    dump_json(release/"policy.json",selected["policy"])
    bm=benchmark_results[selected_kind]
    quality=all(gates(bm,protocol).values()) and all(selected["gates"].values())
    manifest={"version":"1.1.0","model":selected_kind,"model_sha256":sha256(release/"model.joblib"),
              "policy_sha256":sha256(release/"policy.json"),"selection_sha256":selection_hash,
              "quality_status":"passes_declared_internal_gates" if quality else "provisional_quality_gates_not_all_met",
              "production_authorized":False,"model_input":"raw_query_text_only","response_keys":["route","confidence"],
              "confidence_definition":"Probability of the emitted learned class. Rule confidence, if enabled, is a training-only empirical estimate. Guard fallback confidence is zero (unknown), not certainty.",
              "training_rows":len(training),"training_sha256":sha256(out/"data/training_strict.csv"),
              "benchmark_sha256":sha256(frozen/"benchmark_gold.csv"),"source_commit":os.environ.get("GITHUB_SHA"),
              "trusted_artifact_only":True}
    dump_json(release/"manifest.json",manifest)
    resolver=Resolver(release)
    d,p,lat=timed_decisions(final_model,policy,suite.query_text.tolist())
    app_all=save_evaluation(out/"applicability"/"all",suite,d,p,lat)
    app_sections={}
    for section in sorted(suite["section"].unique()):
        mask=suite.section.eq(section).to_numpy()
        app_sections[section]=save_evaluation(out/"applicability"/section,suite[mask].reset_index(drop=True),d[mask].reset_index(drop=True),p[mask],np.asarray(lat)[mask])
    exact_train=set(training.query_text.map(normalize)); fam_train=set(training.family_id)
    suite_audit=suite[["case_id","section","query_text","route"]].copy()
    suite_audit["exact_training_overlap"]=suite.query_text.map(normalize).isin(exact_train)
    suite_audit["family_training_overlap"]=suite.query_text.map(family_id).isin(fam_train)
    suite_audit.to_csv(out/"applicability"/"overlap_audit.csv",index=False)
    novel=(~suite_audit.exact_training_overlap)&suite.section.eq("core")
    if novel.any():
        app_sections["core_exact_novel"]=save_evaluation(out/"applicability"/"core_exact_novel",suite[novel].reset_index(drop=True),d[novel].reset_index(drop=True),p[novel],np.asarray(lat)[novel])
    robustness=[]
    for q,original in zip(suite.query_text,d.route):
        for name,variant in (("uppercase",q.upper()),("whitespace","  "+q.replace(" ","  ")+"  "),("punctuation",q+"?")):
            result=resolver.resolve(variant)
            robustness.append({"query_text":q,"transformation":name,"variant":variant,"original_route":original,"variant_route":result["route"],"same_route":result["route"]==original})
    robustness=pd.DataFrame(robustness)
    robustness.to_csv(out/"applicability"/"metamorphic_checks.csv",index=False)
    stability=robustness.groupby("transformation").same_route.agg(["sum","count","mean"]).to_dict("index")
    # Re-score frozen historical exports for denominator-consistent reporting.
    references={}; paired={}
    selected_pred=pd.read_csv(out/"models"/selected_kind/"benchmark"/"predictions.csv",keep_default_na=False)
    for name,path in (("v1_0_1",base/"artifacts/models/linearsvc/predictions.csv"),("qwen_legacy_pipeline",base/"artifacts/models/qwen/predictions.csv")):
        ref=pd.read_csv(path,keep_default_na=False)
        col="predicted_route" if "predicted_route" in ref else "predicted_route_raw"
        merged=gold[["benchmark_id","route"]].merge(ref,on="benchmark_id",validate="one_to_one",suffixes=("_gold","_pred"))
        if len(merged)!=len(gold): raise AssertionError("Reference prediction coverage mismatch")
        truecol="route_gold" if "route_gold" in merged else "route"
        references[name]=calculate(merged[truecol],merged[col],None,merged["latency_ms"] if "latency_ms" in merged else None)
        references[name]["source_sha256"]=sha256(path)
        aligned=gold[["benchmark_id","route"]].merge(selected_pred[["benchmark_id","predicted_route"]],on="benchmark_id",validate="one_to_one").merge(ref[["benchmark_id",col]].rename(columns={col:"reference_route"}),on="benchmark_id",validate="one_to_one")
        paired[name]=paired_accuracy_interval(aligned.route,aligned.predicted_route,aligned.reference_route)
    dump_json(out/"legacy_comparison.json",{"references":references,"paired":paired,"caveat":"Models use different training protocols and historical hardware; no cross-hardware speedup or cost claim is made. Qwen figures evaluate the existing model+parser+fallback, not general Qwen capability."})
    runtime=verify_runtime(resolver,suite,out/"verification")
    after=snapshot(base)
    if baseline!=after: raise AssertionError("A legacy V1 file changed during closeout")
    if sha256(out/"selection.json")!=selection_hash: raise AssertionError("Selection changed after evaluation")
    integrity["legacy_bytes_preserved"]=True
    dump_json(out/"data"/"integrity.json",integrity)
    summary={"version":"1.1.0","engineering_status":"complete_local_component_and_reproducible_research_handoff",
             "production_status":"blocked_external_approval_bindings_real_traffic", "selected_model":selected_kind,"selected_policy":selected["policy"],
             "model_quality_passes_declared_gates":quality,"benchmark_gates":gates(bm,protocol),"oof_gates":selected["gates"],
             "review":review,"data":{k:v for k,v in integrity.items() if k!="legacy_files_sha256"},
             "benchmark":bm,"oof":selected["metrics"],"candidate_benchmarks":benchmark_results,
             "applicability":app_sections,"applicability_manifest":app_manifest,
             "applicability_exact_training_overlap":int(suite_audit.exact_training_overlap.sum()),
             "metamorphic_stability":stability,"runtime":runtime,"legacy":references,"paired_accuracy":paired,
             "external_model_api_calls_in_closeout":0,"selection_sha256":selection_hash,"environment":method_info(),
             "interpretation":"Complete engineering deliverable, not proof of production reliability. Labels are mostly synthetic/policy-derived. New tests are assistant-authored and not independent. Original review is retained, with separate policy corrections and context exclusions."}
    dump_json(out/"SUMMARY.json",summary)
    from .reporting import write_reports
    write_reports(repo,summary)
    manifest_files={str(p.relative_to(root)):sha256(p) for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.name!="SHA256SUMS.json" and ".pytest_cache" not in p.parts}
    dump_json(out/"SHA256SUMS.json",manifest_files)
    print(json.dumps({"selected_model":selected_kind,"training_rows":len(training),"benchmark_accuracy":bm["accuracy"],"quality_passed":quality,"runtime_checks":runtime["checks"],"status":"complete"},indent=2),flush=True)

if __name__=="__main__": main()
