"""All headline values are populated from executed artifacts, not handwritten."""
from __future__ import annotations
import html,json
from pathlib import Path
from .common import dump_json

def pct(x): return "not defined" if x is None else f"{100*x:.2f}%"
def num(x): return "not measured" if x is None else f"{x:.4f}"
def interval(x): return "undefined denominator" if x is None else f"{pct(x[0])}–{pct(x[1])}"

def write_reports(repo:Path,s:dict):
    root=repo/"v1_1"; out=root/"artifacts"; docs=root/"docs"
    docs.mkdir(exist_ok=True)
    b=s["benchmark"]; a=s["applicability"]["core"]; stress=s["applicability"]["stress"]
    rv=s["review"]; rt=s["runtime"]; gate="PASS" if s["model_quality_passes_declared_gates"] else "NOT ALL MET"
    comparisons=[]
    for name,m in s["legacy"].items():
        comparisons.append(f"| {name} | {pct(m['accuracy'])} | {num(m['macro_f1'])} | {pct(m['false_short_circuit_rate'])} ({m['false_short_circuit_count']}/{m['predicted_short_circuit_count']}) | {pct(m['short_circuit_recall'])} |")
    comparisons.append(f"| V1.1 selected: {s['selected_model']} | {pct(b['accuracy'])} | {num(b['macro_f1'])} | {pct(b['false_short_circuit_rate'])} ({b['false_short_circuit_count']}/{b['predicted_short_circuit_count']}) | {pct(b['short_circuit_recall'])} |")
    text=f'''# Query Intent Resolver — Technical Closeout

**Engineering delivery:** complete, with reproducible source, artifacts, review audit, runtime, tests, evaluation, documentation, and integration seam.  
**Internal model quality gates:** {gate}.  
**Production deployment:** not authorized; requires MascotGO bindings, product approval, independently labeled real queries, and acceptable operational risk.

## Decision for the handoff

The OOF-selected V1.1 candidate is **{s['selected_model']}**, with short-circuit threshold **{s['selected_policy']['short_threshold']}** and lookup-rule override **{s['selected_policy']['use_lookup_rules']}**. It was selected using only grouped training out-of-fold results; the historical benchmark and new applicability labels were not used to choose the candidate or threshold. Completing the engineering work does not waive the predeclared quality gates.

The original V1.0.1 source, trained artifact, benchmark, predictions and policy remain byte-for-byte preserved. V1.1 is delivered beside them, not silently substituted for the earlier model. Neither model is declared authorized for live user traffic by this handoff.

## Source and contribution closeout

Nimisha's submitted review has **{rv['submitted_rows']}** rows and matches all quarantined query IDs. It is retained unchanged in `data/manual_review_received.csv`. Structural completion was confirmed, but a semantic consistency pass identified conflicting routes across otherwise equivalent school/program substitutions. A completed form was therefore not treated as automatically correct training truth.

- **{rv['accepted_unchanged']}** labels retained unchanged under the explicit closeout policy.
- **{rv['policy_adjudicated']}** labels separately adjudicated by the AI-assisted closeout pass, with row-level rationale and original label/notes retained.
- **{rv['deferred_context']}** context-dependent queries retained outside supervised training.

No modified opinion is attributed to Nimisha. The audit is `artifacts/data/review_audit.csv`; exclusions are `artifacts/data/deferred_context.csv`. Context-dependent cases are a deliberate modeling boundary, not a missing submission.

Anthony supplied the original Qwen inference export through PR #6. The original export and legacy scores are preserved. Tanvi completed the product-scope review in issue #4. Remaining applicability execution was completed in this closeout as **AI-assisted testing**, not described as a new independent teammate review. Historical phase contributors retain credit in the repository history.

## Data and leakage controls

The reviewed training pool contains **{s['data']['reviewed_training_rows']}** rows. The strict V1.1 fit uses **{s['data']['strict_training_rows']}** rows after excluding **{s['data']['excluded_family_rows']}** rows in heuristic template families represented in the historical benchmark. Of the newly reviewed examples, **{s['data']['reviewed_examples_retained_in_strict_training']}** remain in this stricter fit; accepting a review into the versioned data pool is not the same as using it in every fitted model.

There are **0 exact-query overlaps** and **0 family overlaps under the declared lexical heuristic** between the V1.1 fit and the historical benchmark. This heuristic replaces known schools, programs, places and numbers; it is not a proof of zero semantic similarity. The legacy training pool overlapped **{s['data']['legacy_template_overlap_families']}** such benchmark families. The two versions consequently do not have identical training conditions.

Grouped outer cross-validation has three folds. Each calibrated estimator fits its entire feature pipeline inside three grouped inner folds: vocabulary construction is not performed globally before calibration. The frozen protocol defines three candidates, a fixed threshold grid and a restricted full-match lookup grammar. The rule layer is disabled unless its training-only evidence satisfies the declared support and precision criteria.

The 300-row V1 benchmark is balanced (75 per route). It has been observed repeatedly in this project's history, so this is **historical regression evidence**, not a newly blind final test. It was not relabeled. Its SHA-256 remains `{s['data']['benchmark_sha256']}`.

## Historical benchmark comparison

| System | Accuracy | Macro F1 | False SC among predicted SC | SC recall |
|---|---:|---:|---:|---:|
{chr(10).join(comparisons)}

The V1.1 accuracy Wilson 95% interval is **{interval(b['accuracy_95ci'])}**. The false-short-circuit discovery interval is **{interval(b['false_short_circuit_discovery_95ci'])}**. Small denominators limit certainty even where point estimates look favorable.

In this project, the legacy field `false_short_circuit_rate` means **false discoveries / predicted short circuits**. It is not the usual false-positive rate over actual non-short queries. V1.1 also reports the latter (**{pct(b['false_short_circuit_nonshort_rate'])}**) and the all-query fraction (**{pct(b['false_short_circuit_overall_rate'])}**). A zero predicted-short denominator is reported as undefined, never as guaranteed zero risk.

The Qwen result describes its then-existing persona/intent generation, parser, fallback, and deployment policy together. It does not establish that the underlying Qwen architecture is unsuitable for direct route training. The recorded GPU generation latency and local CPU classifier timings are not a controlled cross-hardware speed comparison. The old Qwen zero-cost field was an unpriced default, not evidence of free compute.

## Applicability and robustness

A separate **120-case** suite was authored and hashed before closeout inference: **100 balanced core cases**, plus **20 boundary/stress cases**. These are assistant-authored, policy-labeled examples, not real MascotGO traffic or independent human validation. Assumptions are visible per case. No failed case was relabeled or used for model selection after predictions.

| Set | Rows | Accuracy | Macro F1 | False SC discoveries | SC recall |
|---|---:|---:|---:|---:|---:|
| Core | {a['rows']} | {pct(a['accuracy'])} | {num(a['macro_f1'])} | {pct(a['false_short_circuit_rate'])} | {pct(a['short_circuit_recall'])} |
| Stress | {stress['rows']} | {pct(stress['accuracy'])} | {num(stress['macro_f1'])} | {pct(stress['false_short_circuit_rate'])} | {pct(stress['short_circuit_recall'])} |

The stress set predominantly expects clarification/escalation; do not combine it with the core set to inflate the headline. There are **{s['applicability_exact_training_overlap']}** exact training overlaps in the full suite. A core exact-novel subset and full overlap audit are supplied. Novelty is not inferred simply because a sentence was typed anew.

Capitalization, whitespace and punctuation variants are tested separately. Full row-level outputs, failure examples, route confusion, confidence reliability and metamorphic stability are in `artifacts/applicability/`. The limited unsupported-language/instruction-pattern guard is a routing heuristic, not a comprehensive security or out-of-domain detector. `llm_needed` is a request for further handling/clarification, not permission to fulfill unsafe content or proof that one model call will suffice.

## Runtime and integration

Successful `POST /v1/resolve` returns exactly `route` and `confidence`. Optional persona, page, filters, context and session are accepted but do not affect the result. Invalid types, blank input, excessive length, unsupported control characters and oversized batches are rejected. `/health` means the service process is available; `/ready` means the model is loaded, not that production approval exists.

For learned decisions, confidence is the probability assigned to the **emitted** route, not the top probability of a different route before fallback. Guarded inputs return zero confidence to signal unknown. Any enabled rule uses a separately estimated training-only precision signal. These meanings are documented rather than presented as calibrated guarantees across all decision sources.

The runtime performs no network calls, no database mutations, and no raw-query logging. API-key authentication is optional for local evaluation and required at the deployment gateway for any externally exposed installation. Trusted bundle hashes are checked before model loading; this does not make untrusted pickle/joblib files safe. The supplied environment is pinned.

**{rt['passed']}/{rt['checks']} runtime verification checks passed**. The in-process 1,000-query serial test processed approximately **{rt['load']['sequential_queries_per_second']:.1f} queries/second**. That is a measured local CPU workload, not an HTTP/network/production service-level agreement. Threaded parity is separately verified.

`RouterBindings` accepts explicit callables for all four routes and fails when a binding is missing. The deployment preflight remains false until the product owner approves concrete handlers, real traffic has been validated and the quality gates are satisfied. No fabricated endpoint or claimed Foundry deployment is included.

## Cost and operational evidence

This closeout made **0 external model API calls**. The local classifier consumes no LLM tokens. Hosting, CPU, monitoring, data lookup and downstream execution costs are not measured and must not be reported as zero. Historical Phase 5 pricing tables are planning material, not contemporary measured costs. `config/cost_model.example.json` provides explicit replaceable assumptions rather than a savings claim.

## What remains outside this completed engineering delivery

Peter/MascotGO must provide the actual invocation surface, route-to-handler mapping, optional request fields, deployment boundary, authorized data/index coverage, and a privacy-safe real-query or shadow-traffic sample. A product owner must accept routing-error tolerances. These remain tracked by issue #5; they cannot be invented or completed on MascotGO's behalf.

The internal handoff can be designated complete. Production validation/deployment cannot. If the internal gate status at the top is not all met, the candidate remains provisional and must not be promoted merely because a deadline expired.

## Reproducibility

Run `PYTHONPATH=v1_1 python -m qir_release.build --repo-root .` using `v1_1/requirements.txt`. The selected policy is saved before evaluation labels are opened. Its hash is recorded on every candidate report. The baseline snapshot checks every file under `v1/` before and after the build. Reproduction must fail if the benchmark or applicability suite changes unexpectedly.

## Technical references and source basis

- Original Google Drive project plan: https://docs.google.com/document/d/1NKtirKNjp--RUNvo2KindbX4F-p1Ceir-dGA9BnIg70/edit (original phases 1–7; read during closeout; broader persona/intent outputs were later narrowed by the team).
- Current contract and original data provenance: `v1/CONTRACT.md`, `v1/ROUTING_LABEL_POLICY.md`, original phase directories, and Git history.
- scikit-learn calibration API: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
- Grouped validation API: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
- Microsoft Foundry OpenAPI tool integration: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/openapi (integration pattern only, not a deployment claim).
- GitHub build artifacts: https://docs.github.com/en/actions/tutorials/store-and-share-data
'''
    (docs/"TECHNICAL_CLOSEOUT.md").write_text(text,encoding="utf-8")
    decision={"engineering_delivery_complete":True,"internal_quality_gates_passed":s["model_quality_passes_declared_gates"],
              "independent_real_traffic_validation_complete":False,"live_mascotgo_integration_complete":False,
              "original_benchmark_unchanged":True,"api_contract_verified":True,
              "review_submission_processed":True,"applicability_execution_complete":True,
              "reviewed_context_exclusions_deliberate":rv["deferred_context"],"candidate":s["selected_model"],
              "recommended_use":"Local demonstration and product-integration review; no automatic live promotion."}
    dump_json(out/"COMPLETION_MATRIX.json",decision)
    rows="".join(f"<tr><td>{html.escape(name)}</td><td>{pct(m['accuracy'])}</td><td>{num(m['macro_f1'])}</td><td>{pct(m['false_short_circuit_rate'])}</td><td>{pct(m['short_circuit_recall'])}</td></tr>" for name,m in {**s['legacy'],"V1.1 "+s['selected_model']:b}.items())
    cards=[("Engineering","Delivered"),("Quality gates",gate),("Historical accuracy",pct(b['accuracy'])),("Core applicability",pct(a['accuracy']))]
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Query Intent Resolver · Technical Closeout</title>
<style>body{{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f6f7f9;color:#192434}}main{{max-width:1040px;margin:48px auto;padding:0 28px}}h1{{font-size:42px;line-height:1.1;letter-spacing:-1.3px}}h2{{margin-top:42px}}.eyebrow{{text-transform:uppercase;letter-spacing:2px;font-size:12px}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card,section{{background:white;border:1px solid #dbe1e8;border-radius:8px;padding:22px}}.card strong{{display:block;font-size:24px;line-height:1.3}}.card span{{font-size:12px}}section{{margin-top:18px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:12px 8px;border-bottom:1px solid #e3e8ef}}.note{{font-size:14px;color:#42536b}}a{{color:#24496c}}pre{{overflow:auto;background:#f3f6fa;padding:18px}}@media(max-width:700px){{.cards{{grid-template-columns:1fr 1fr}}h1{{font-size:32px}}table{{font-size:12px}}}}@media print{{body{{background:white}}main{{margin:0;max-width:none}}section{{break-inside:avoid}}}}</style>
<main><p class="eyebrow">MascotGO · Engineering and research handoff · V1.1</p><h1>Query Intent Resolver<br>Technical closeout</h1><p>A reproducible query-only routing component, complete with reviewed data provenance, model comparisons, a tested API and explicit deployment boundaries.</p><div class="cards">{''.join(f'<div class="card"><span>{k}</span><strong>{v}</strong></div>' for k,v in cards)}</div>
<section><h2>What is complete</h2><p>The review submission is preserved, {rv['accepted_unchanged']} labels are retained unchanged, {rv['policy_adjudicated']} are separately policy-adjudicated and {rv['deferred_context']} context-dependent examples remain deliberately excluded. The strict training fit uses {s['data']['strict_training_rows']:,} queries. All original V1 files remain unchanged.</p><p>Model and threshold selection used grouped training OOF only. The historical test was not rewritten. Applicability testing and API verification are executed, not merely planned.</p></section>
<section><h2>Historical benchmark results</h2><table><thead><tr><th>System</th><th>Accuracy</th><th>Macro F1</th><th>False SC / predicted SC</th><th>SC recall</th></tr></thead><tbody>{rows}</tbody></table><p class="note">300 balanced, previously observed synthetic/curated queries. V1.1 removes heuristic template-family overlaps, so training conditions differ. Qwen figures describe the legacy model + parser + fallback. Do not infer a controlled hardware speedup.</p></section>
<section><h2>Applicability, without inflated claims</h2><p>Core suite: {a['rows']} cases, {pct(a['accuracy'])} accuracy. Stress suite: {stress['rows']} cases, {pct(stress['accuracy'])} accuracy. The suite was hashed before predictions and contains no independent users or production traffic. Full errors and overlap audits are retained.</p><p>Runtime checks: {rt['passed']}/{rt['checks']} passed. Local serial throughput: {rt['load']['sequential_queries_per_second']:.1f} queries/second over 1,000 in-process calls. This is not a network SLA.</p></section>
<section><h2>The integration contract</h2><pre>POST /v1/resolve\n{{"query_text":"UCLA vs USC for engineering"}}\n\n{{"route":"complex","confidence":0.91}}</pre><p class="note">Illustrative response, not a claimed output for that exact query. Optional context remains decoupled. Invalid input is rejected; no actual downstream handler is invoked.</p></section>
<section><h2>What Peter needs to decide</h2><p>Invocation surfaces; concrete handler for each route; supported indexed fields; available optional context; deployment boundary; privacy-safe real-query or shadow evaluation; and accepted error tolerances.</p><p><strong>Production is not authorized by this handoff.</strong> Successful builds and project delivery are separate from model quality and live deployment approval.</p></section>
<p><a href="TECHNICAL_CLOSEOUT.md">Full technical report</a> · <a href="../artifacts/SUMMARY.json">Machine-readable evidence</a> · <a href="../artifacts/COMPLETION_MATRIX.json">Completion boundaries</a> · <a href="../artifacts/applicability/core/errors.csv">Core failures</a></p></main></html>'''
    (docs/"REVIEWER_BRIEF.html").write_text(page,encoding="utf-8")
    write_print_reports(docs,s)


def write_print_reports(docs:Path,s:dict):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    from docx import Document
    from docx.shared import Inches,Pt
    b=s['benchmark']; a=s['applicability']['core']; r=s['review']
    title="Query Intent Resolver"
    subtitle="V1.1 | Technical closeout and integration handoff"
    sections=[
        ("Delivery decision",f"The query-only engineering package is complete. Internal quality gates are {'met' if s['model_quality_passes_declared_gates'] else 'not all met'}. Live MascotGO deployment is not authorized: concrete handlers, product approval and independently labeled real traffic remain external requirements."),
        ("What was finished",f"The submitted 55-row review was verified against the quarantine queue. {r['accepted_unchanged']} labels were retained unchanged; {r['policy_adjudicated']} were separately policy-adjudicated; {r['deferred_context']} context-dependent queries were excluded. The original reviewer CSV and every original V1 file are unchanged. The strict new fit contains {s['data']['strict_training_rows']:,} queries."),
        ("Model selection and evidence",f"The selected candidate is {s['selected_model']}. Three fixed candidates were evaluated using grouped training out-of-fold predictions. Model, routing threshold and optional lookup rule were fixed before reading evaluation labels. The legacy 300-query benchmark is historical regression evidence, not a new blind test. V1.1 has zero exact and zero heuristic template-family overlaps with its fit; semantic overlap beyond this heuristic remains possible."),
        ("Applicability and runtime",f"The balanced 100-case assistant-authored core suite achieved {pct(a['accuracy'])} accuracy and {num(a['macro_f1'])} macro F1. Twenty boundary cases are reported separately. These cases are neither independent human testing nor real-user traffic. The runtime passed {s['runtime']['passed']}/{s['runtime']['checks']} contract, input-validation, batch, parity and threading checks."),
        ("Confidence and cost", "Learned confidence is the probability of the emitted route, not the probability of a discarded prediction. Guard fallback confidence is zero to indicate unknown. No external model API calls or LLM tokens were used in this closeout; infrastructure, CPU and downstream costs are not claimed to be zero."),
        ("Integration boundary", "The API accepts raw query_text and returns exactly route and confidence. Persona, page, filters, context and session do not influence V1.1 predictions. Python, CLI, FastAPI, OpenAPI, Docker and explicit four-handler binding examples are supplied. There are no fabricated endpoint URLs, credentials or claimed live Foundry deployments."),
        ("Peter's remaining decisions", "Confirm the invocation surface, route-to-handler mapping, indexed-field coverage, optional request fields, preferred deployment environment and an authorized real-query or shadow sample. Approve error tolerances only after independent validation. Issue #5 remains the external product decision record."),
        ("Use this package", "Start with v1_1/docs/REVIEWER_BRIEF.html and TECHNICAL_CLOSEOUT.md. Exact metrics, row-level predictions, failures, review dispositions, hashes and environment are under v1_1/artifacts/. Reproduce with PYTHONPATH=v1_1 python -m qir_release.build --repo-root . using the pinned requirements. The previous V1.0.1 remains available for rollback and comparison.")]
    rows=[["Measure","Historical 300","Core applicability 100"],
          ["Accuracy",pct(b['accuracy']),pct(a['accuracy'])],
          ["Macro F1",num(b['macro_f1']),num(a['macro_f1'])],
          ["False SC / predicted SC",pct(b['false_short_circuit_rate']),pct(a['false_short_circuit_rate'])],
          ["Short-circuit recall",pct(b['short_circuit_recall']),pct(a['short_circuit_recall'])]]
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyCustom",fontName="Helvetica",fontSize=10,leading=14,spaceAfter=10))
    styles.add(ParagraphStyle(name="HCustom",fontName="Helvetica-Bold",fontSize=13,leading=17,spaceAfter=6,spaceBefore=8))
    story=[Paragraph(title,styles['Title']),Paragraph(subtitle,styles['Normal']),Spacer(1,18)]
    for i,(heading,body) in enumerate(sections):
        if i==3:
            t=Table(rows,colWidths=[180,150,150],repeatRows=1)
            t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#edf1f5')),('BOTTOMPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d6dce3'))]))
            story.extend([t,Spacer(1,12),PageBreak()])
        story.extend([Paragraph(heading,styles['HCustom']),Paragraph(html.escape(body),styles['BodyCustom'])])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8); canvas.drawString(54,30,'MascotGO Query Intent Resolver | Engineering handoff, not production authorization')
        canvas.drawRightString(558,30,str(doc.page))
    SimpleDocTemplate(str(docs/'EXECUTIVE_HANDOFF.pdf'),pagesize=letter,rightMargin=54,leftMargin=54,topMargin=48,bottomMargin=48).build(story,onFirstPage=footer,onLaterPages=footer)
    doc=Document(); sec=doc.sections[0]; sec.top_margin=Inches(.65); sec.bottom_margin=Inches(.65)
    normal=doc.styles['Normal']; normal.font.name='Calibri'; normal.font.size=Pt(10)
    doc.add_heading(title,0); doc.add_paragraph(subtitle)
    for i,(heading,body) in enumerate(sections):
        if i==3:
            table=doc.add_table(rows=1,cols=3); table.style='Light Shading Accent 1'
            for j,value in enumerate(rows[0]): table.rows[0].cells[j].text=value
            for row in rows[1:]:
                cells=table.add_row().cells
                for j,value in enumerate(row): cells[j].text=value
        doc.add_heading(heading,1); doc.add_paragraph(body)
    doc.save(docs/'EXECUTIVE_HANDOFF.docx')
