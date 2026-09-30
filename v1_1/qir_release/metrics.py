from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
from .common import ROUTES, SEED, dump_json

def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if not n:
        return None
    p = k / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n))/d
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [max(0.0, center-half), min(1.0, center+half)]

def calculate(y_true, y_pred, confidence=None, latency_ms=None) -> dict:
    y = np.asarray(y_true, dtype=str); pred = np.asarray(y_pred, dtype=str)
    if len(y) != len(pred) or not len(y):
        raise ValueError("Non-empty, equal-size predictions required")
    if (set(y) | set(pred)) - set(ROUTES):
        raise ValueError("Unrecognized route")
    sc = pred == "short_circuit"; actual = y == "short_circuit"
    fp = int((sc & ~actual).sum()); tp = int((sc & actual).sum())
    denom = int(sc.sum()); nonshort = int((~actual).sum())
    result = {
        "rows": len(y), "accuracy": float((pred == y).mean()),
        "correct": int((pred == y).sum()),
        "macro_f1": float(f1_score(y,pred,labels=ROUTES,average="macro",zero_division=0)),
        "false_short_circuit_count": fp, "predicted_short_circuit_count": denom,
        "true_short_circuit_count": int(actual.sum()),
        "false_short_circuit_rate": float(fp/denom) if denom else None,
        "false_short_circuit_discovery_rate": float(fp/denom) if denom else None,
        "false_short_circuit_nonshort_rate": float(fp/nonshort) if nonshort else None,
        "false_short_circuit_overall_rate": fp/len(y),
        "short_circuit_precision": float(tp/denom) if denom else None,
        "short_circuit_recall": float(tp/actual.sum()) if actual.sum() else None,
        "short_circuit_coverage": denom/len(y),
        "llm_route_fraction": float((pred=="llm_needed").mean()),
        "missed_complex_fraction": float(((y=="complex") & (pred!="complex")).sum()/(y=="complex").sum()) if (y=="complex").any() else None,
        "accuracy_95ci": wilson(int((y==pred).sum()),len(y)),
        "false_short_circuit_discovery_95ci": wilson(fp,denom),
        "short_circuit_recall_95ci": wilson(tp,int(actual.sum())),
        "confusion_matrix_order": list(ROUTES),
        "confusion_matrix": confusion_matrix(y,pred,labels=ROUTES).tolist(),
        "per_route": classification_report(y,pred,labels=ROUTES,output_dict=True,zero_division=0),
    }
    if confidence is not None:
        c=np.asarray(confidence,dtype=float)
        if len(c)!=len(y) or not np.isfinite(c).all() or ((c<0)|(c>1)).any():
            raise ValueError("Invalid confidence values")
        reliability=[]; ece=0.0
        for lo in np.arange(0,1,0.1):
            mask=(c>=lo)&(c<(lo+0.1) if lo<0.89 else c<=1)
            if not mask.any(): continue
            mean=float(c[mask].mean()); acc=float((y[mask]==pred[mask]).mean())
            reliability.append({"lower":round(float(lo),1),"upper":round(float(lo+0.1),1),"rows":int(mask.sum()),"mean_confidence":mean,"accuracy":acc})
            ece+=float(mask.mean())*abs(mean-acc)
        result["confidence_reliability"]=reliability
        result["confidence_ece_descriptive"]=ece
        result["confidence_caveat"]="Diagnostic reliability, not a guarantee. Guarded/fallback decisions and rule estimates are not interchangeable with calibrated multiclass probabilities."
    if latency_ms is not None:
        a=np.asarray(latency_ms,dtype=float)
        if len(a) and np.isfinite(a).all() and (a>=0).all():
            result["latency_ms"]={"mean":float(a.mean()),"p50":float(np.median(a)),"p95":float(np.percentile(a,95)),"p99":float(np.percentile(a,99)),"n":len(a)}
    return result

def gates(m: dict, protocol: dict) -> dict[str,bool]:
    fdr=m.get("false_short_circuit_rate")
    recall=m.get("short_circuit_recall")
    return {"accuracy":m["accuracy"]>=protocol["min_accuracy"],
            "macro_f1":m["macro_f1"]>=protocol["min_macro_f1"],
            "short_circuit_precision":fdr is not None and fdr<=protocol["max_false_short_circuit_discovery_rate"],
            "short_circuit_recall":recall is not None and recall>=protocol["min_short_circuit_recall"]}

def selection_key(m:dict, protocol:dict) -> tuple:
    g=gates(m,protocol)
    safety=g["accuracy"] and g["macro_f1"] and g["short_circuit_precision"] and m["predicted_short_circuit_count"]>=protocol["minimum_validation_short_predictions"]
    fdr=m["false_short_circuit_rate"] if m["false_short_circuit_rate"] is not None else 1.0
    score=.45*m["macro_f1"]+.25*m["accuracy"]+.2*(1-fdr)+.1*(m["short_circuit_recall"] or 0)
    return (all(g.values()) and safety,safety,score,-fdr)

def paired_accuracy_interval(y, a, b, repeats=2000) -> dict:
    y=np.asarray(y); a=np.asarray(a); b=np.asarray(b)
    d=(a==y).astype(float)-(b==y).astype(float)
    rng=np.random.default_rng(SEED)
    samples=np.array([rng.choice(d,size=len(d),replace=True).mean() for _ in range(repeats)])
    return {"candidate_minus_reference":float(d.mean()),"bootstrap_95ci":np.percentile(samples,[2.5,97.5]).tolist(),
            "candidate_only_correct":int(((a==y)&(b!=y)).sum()),"reference_only_correct":int(((b==y)&(a!=y)).sum()),
            "caveat":"Paired row bootstrap on a previously observed, synthetic benchmark. Not a production population confidence interval or proof of improvement."}

def save_evaluation(out:Path, queries:pd.DataFrame, decisions:pd.DataFrame, probabilities=None, latency=None) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    data=queries.reset_index(drop=True).copy()
    for c in decisions.columns:
        data["predicted_route" if c=="route" else c]=decisions[c].to_numpy()
    data["correct"]=data.route.eq(data.predicted_route)
    data["false_short_circuit"]=data.predicted_route.eq("short_circuit") & data.route.ne("short_circuit")
    if latency is not None: data["latency_ms"]=latency
    if probabilities is not None:
        for i,r in enumerate(ROUTES): data["probability_"+r]=probabilities[:,i]
    data.to_csv(out/"predictions.csv",index=False)
    data[~data.correct].to_csv(out/"errors.csv",index=False)
    m=calculate(data.route,data.predicted_route,data.confidence,latency)
    dump_json(out/"metrics.json",m)
    return m
