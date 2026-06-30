import ast
import os
import re
from datetime import datetime, timezone

try:
    from .preflight import check_source
except ImportError:
    from preflight import check_source


SEVERITY_SCORES = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

SEVERITY_MODEL = {
    "low": "Informational or weak signal. Review during normal cleanup.",
    "medium": "Can cause inconsistent outcomes or operational friction. Fix before high-value use.",
    "high": "Can affect contract state, validator agreement, or validator cost. Fix before production.",
    "critical": "Can directly enable unsafe execution, invalid scoring, or severe compromise. Fix immediately.",
}


def add_finding(findings, pillar, severity, message, source="heuristic", line=None):
    findings.append({
        "pillar": pillar,
        "severity": severity,
        "message": message,
        "source": source,
        "line": line,
    })


def severity_score(severity):
    return SEVERITY_SCORES.get(severity, 0)


def classify_risk(score):
    if score >= 7:
        return "HIGH"
    if score >= 3:
        return "MEDIUM"
    return "LOW"


def score_by_pillar(findings, pillar):
    return sum(
        severity_score(finding["severity"])
        for finding in findings
        if finding["pillar"] == pillar
    )


def metric_class(label):
    if label == "LOW":
        return "val-low"
    if label == "MEDIUM":
        return "val-medium"
    return "val-high"


def invalid_metrics():
    metric = {
        "value": "N/A",
        "className": "val-medium",
    }
    return {
        "consensus": dict(metric),
        "appeal": dict(metric),
        "drift": dict(metric),
        "reality": dict(metric),
        "compute": dict(metric),
        "deterministic": {
            "value": "INVALID",
            "className": "val-high",
        },
    }


def validate_contract_source(contract_name, source):
    stripped = source.strip()
    issues = []

    if not stripped:
        issues.append("Contract source is empty.")
        return issues

    try:
        tree = ast.parse(source, filename=contract_name or "submitted_contract.py")
    except SyntaxError as exc:
        issues.append(f"Submitted source is not valid Python: line {exc.lineno}: {exc.msg}.")
        return issues

    has_class = any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    has_function = any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree))
    has_genlayer_signal = bool(re.search(
        r"(@gl\.|@genlayer|import\s+genlayer|from\s+genlayer|gl\.public|gl\.nondet|allow_storage|TreeMap)",
        source,
        re.I,
    ))

    if not has_class and not has_function:
        issues.append("Submitted source has no Python class or function definitions.")

    if not has_genlayer_signal:
        issues.append("Submitted source does not look like a GenLayer Intelligent Contract.")

    return issues


def invalid_contract_response(contract_name, source, issues):
    findings = [
        {
            "pillar": "input",
            "severity": "critical",
            "message": f"[INPUT] {issue}",
            "source": "validator",
            "line": None,
        }
        for issue in issues
    ]

    logs = [
        {"message": f"[PREFLIGHT] Validating {contract_name}...", "type": "info"},
        {"message": "[INPUT] Audit aborted before scoring.", "type": "warning"},
    ]
    logs.extend({"message": finding["message"], "type": "error"} for finding in findings)
    logs.append({
        "message": "[REPORT] Submit a valid GenLayer Python contract before interpreting stability metrics.",
        "type": "warning",
    })

    return {
        "contractName": contract_name,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "engine": "genlayer-auditor-live",
        "version": read_version(),
        "metrics": invalid_metrics(),
        "findings": findings,
        "summary": {
            "headline": "This submission was not audited.",
            "plainEnglish": "The input does not look like a GenLayer Python contract, so the auditor stopped before producing risk scores.",
            "nextSteps": [
                "Paste the full contract source, not a fragment or random text.",
                "Make sure the source contains Python class/function definitions.",
                "Include the GenLayer decorators/imports used by the contract.",
            ],
            "metricExplanations": metric_explanations(),
            "findingExplanations": explain_findings(findings),
            "narrativeFindings": merge_finding_explanations(findings),
            "severityModel": SEVERITY_MODEL,
        },
        "severityModel": SEVERITY_MODEL,
        "logs": logs,
        "verdict": {
            "status": "invalid",
            "message": "INVALID CONTRACT INPUT",
        },
    }


def map_preflight_finding(raw_finding):
    severity = "medium"
    pillar = "deterministic"

    if "[ACCESS]" in raw_finding:
        severity = "high"
    elif "[PYTHON]" in raw_finding:
        severity = "critical"
    elif "[ORACLE]" in raw_finding:
        severity = "high"
        pillar = "reality"
    elif "[STORAGE]" in raw_finding:
        pillar = "economic"

    line = parse_line_number(raw_finding)

    return {
        "pillar": pillar,
        "severity": severity,
        "message": raw_finding,
        "source": "preflight",
        "line": line,
    }


def parse_line_number(message):
    match = re.search(r"\bL(\d+):", message)
    return int(match.group(1)) if match else None


def snippet_for_line(source, line):
    if not line:
        return ""
    lines = source.splitlines()
    if line < 1 or line > len(lines):
        return ""
    return lines[line - 1].strip()


def first_matching_line(source, pattern):
    for index, line in enumerate(source.splitlines(), start=1):
        if re.search(pattern, line, re.I):
            return index
    return None


def metric_explanations():
    return {
        "consensus": "How likely independent validators are to reach the same answer. Higher is better.",
        "appeal": "How likely users are to dispute the result because the answer can be interpreted differently.",
        "drift": "How much the final outcome may change when prompts, wording, or validator framing changes.",
        "reality": "Risk that external data sources disagree or change during resolution.",
        "compute": "Estimated validator workload compared with a simple contract. Higher means more cost/grief risk.",
        "deterministic": "Traditional code-level risk from access control, unsafe Python, storage, or URL construction.",
    }


def explain_findings(findings):
    explanations = []
    for finding in findings:
        message = finding["message"]
        pillar = finding["pillar"]
        line = finding.get("line")
        snippet = finding.get("snippet", "")

        if "[ACCESS]" in message:
            title = "Public write may be callable by the wrong user"
            impact = "A state-changing method can probably be called without an obvious owner/user check."
            recommendation = "Add an explicit sender/role check near the top of the method."
            suggested_fix = "Add an assert/if guard using gl.message.sender_address before mutating state."
            why_severity = "High because an unguarded public write can let unauthorized users change contract state."
        elif "[PYTHON]" in message:
            title = "Unsafe Python execution"
            impact = "eval/exec can run attacker-controlled code if user input reaches it."
            recommendation = "Remove eval/exec and replace it with explicit parsing or a whitelist."
            suggested_fix = "Replace eval/exec with strict parsing, enum lookup, or schema validation."
            why_severity = "Critical because arbitrary code execution is usually directly exploitable."
        elif "[ORACLE]" in message:
            title = "Dynamic external URL"
            impact = "Validators may fetch attacker-controlled or inconsistent URLs."
            recommendation = "Use allowlisted domains and construct URLs from validated parameters only."
            suggested_fix = "Keep a fixed allowlist of hostnames and reject user-controlled URL fragments."
            why_severity = "High because external fetches can steer validator evidence or trigger SSRF-like behavior."
        elif "[STORAGE]" in message:
            title = "Storage persistence needs review"
            impact = "The contract opts into storage, but the scanner did not see the expected persistent map pattern."
            recommendation = "Confirm the state model uses GenLayer-supported persistent structures."
            suggested_fix = "Use the expected persistent collection pattern, or remove @allow_storage if it is unnecessary."
            why_severity = "Medium because storage model mistakes often create state inconsistency rather than immediate compromise."
        elif pillar == "interpretive":
            title = "Outcome wording is ambiguous"
            impact = "Different validators may reasonably interpret the same resolution criteria differently."
            recommendation = "Convert subjective rules into precise schemas, thresholds, examples, or tie-breakers."
            suggested_fix = "Define exact thresholds, source priority, time windows, and tie-breaker behavior."
            why_severity = "Medium because ambiguity raises appeals and disagreement, but may not directly break state."
        elif pillar == "reality":
            title = "External data can diverge"
            impact = "The contract depends on multiple sources that may not agree at the same moment."
            recommendation = "Define source priority, timestamp rules, quorum logic, or averaging behavior."
            suggested_fix = "Record source timestamps and define quorum/median/priority rules for conflicting data."
            why_severity = "Medium or high depending on whether source disagreement can change payouts."
        elif pillar == "economic":
            title = "Validator cost can be amplified"
            impact = "Loops, many URLs, or repeated rendering can make validation expensive or slow."
            recommendation = "Cap source counts, loop bounds, payload sizes, and render calls."
            suggested_fix = "Set maximum list sizes and maximum web render calls per resolution."
            why_severity = "High when repeated work can make validators spend much more compute than expected."
        elif pillar == "adversarial":
            title = "Prompt steering risk"
            impact = "User-controlled text may influence validators beyond the intended question."
            recommendation = "Separate untrusted evidence from instructions and summarize or sanitize it before resolution."
            suggested_fix = "Quote untrusted text as evidence, never as instructions, and use a neutral summarization step."
            why_severity = "High because prompt steering can change validator interpretation of the same facts."
        elif pillar == "input":
            title = "Input cannot be scored"
            impact = message.replace("[INPUT] ", "")
            recommendation = "Submit complete GenLayer Python contract source."
            suggested_fix = "Paste the full contract file with imports, decorators, classes, and methods."
            why_severity = "Critical because the audit cannot produce meaningful scores for invalid input."
        else:
            title = "Finding needs review"
            impact = message
            recommendation = "Inspect this finding before high-value deployment."
            suggested_fix = recommendation
            why_severity = SEVERITY_MODEL.get(finding["severity"], "Severity is based on expected impact.")

        explanations.append({
            "title": title,
            "severity": finding["severity"].upper(),
            "line": line,
            "snippet": snippet,
            "impact": impact,
            "recommendation": recommendation,
            "suggestedFix": suggested_fix,
            "whySeverity": why_severity,
            "raw": message,
        })

    return explanations


def finding_root_cause(finding, explanation):
    message = finding["message"]
    if "[ACCESS]" in message:
        return "access-control"
    if "[PYTHON]" in message:
        return "unsafe-python"
    if "[ORACLE]" in message:
        return "dynamic-oracle-url"
    if "[STORAGE]" in message:
        return "storage-persistence"
    if "[INTERPRETIVE]" in message or finding["pillar"] == "interpretive":
        return "ambiguous-resolution"
    if "[REALITY]" in message or finding["pillar"] == "reality":
        return "external-data-divergence"
    if "[ECONOMIC]" in message or finding["pillar"] == "economic":
        return "validator-cost-amplification"
    if "[ADVERSARIAL]" in message or finding["pillar"] == "adversarial":
        return "prompt-steering"
    if finding["pillar"] == "input":
        return "invalid-input"
    return explanation["title"].lower()


def finding_location_family(finding):
    message = finding["message"]
    if "[ACCESS]" in message:
        return "public-write-methods"

    method_match = re.search(r"\bmethod:\s*(\w+)", message)
    if method_match:
        return f"method:{method_match.group(1)}"

    line = finding.get("line")
    if line:
        return f"line:{line}"

    return finding.get("source", "general")


def merge_finding_explanations(findings):
    explanations = explain_findings(findings)
    grouped = {}

    for finding, explanation in zip(findings, explanations):
        key = (
            finding_root_cause(finding, explanation),
            finding_location_family(finding),
        )
        group = grouped.setdefault(key, {
            **explanation,
            "count": 0,
            "lines": [],
            "rawFindings": [],
        })
        group["count"] += 1
        if explanation.get("line") and explanation["line"] not in group["lines"]:
            group["lines"].append(explanation["line"])
        group["rawFindings"].append(explanation["raw"])

        if severity_score(finding["severity"]) > severity_score(group["severity"].lower()):
            group["severity"] = explanation["severity"]
            group["whySeverity"] = explanation["whySeverity"]

    merged = list(grouped.values())
    for group in merged:
        group["lines"].sort()
        if group["count"] > 1:
            location_text = ", ".join(f"line {line}" for line in group["lines"][:4])
            if len(group["lines"]) > 4:
                location_text += f", and {len(group['lines']) - 4} more"
            if location_text:
                group["impact"] = f"{group['impact']} This pattern appears {group['count']} times ({location_text})."
            else:
                group["impact"] = f"{group['impact']} This pattern appears {group['count']} times."

    return merged


def build_next_steps(narrative_findings):
    if not narrative_findings:
        return [
            "Run the full specialist review before deploying value-bearing contracts.",
            "Add test cases for disputed outcomes and edge-case evidence.",
            "Review all external data assumptions manually.",
        ]

    steps = []
    for finding in narrative_findings:
        if finding["recommendation"] not in steps:
            steps.append(finding["recommendation"])
        if len(steps) == 3:
            break

    fallback_steps = [
        "Add regression tests for each fixed issue family.",
        "Re-run the audit and confirm the detailed findings list no longer contains unresolved high-risk items.",
        "Review all external data assumptions manually.",
    ]
    for fallback in fallback_steps:
        if len(steps) == 3:
            break
        if fallback not in steps:
            steps.append(fallback)

    return steps


def build_summary(findings, metrics, verdict):
    if not findings:
        return {
            "headline": "No high-signal issues were found.",
            "plainEnglish": "This does not prove the contract is safe; it only means the local checks did not find obvious risk patterns.",
            "nextSteps": [
                "Run the full specialist review before deploying value-bearing contracts.",
                "Add test cases for disputed outcomes and edge-case evidence.",
                "Review all external data assumptions manually.",
            ],
            "metricExplanations": metric_explanations(),
            "findingExplanations": [],
            "narrativeFindings": [],
            "severityModel": SEVERITY_MODEL,
        }

    finding_explanations = explain_findings(findings)
    narrative_findings = merge_finding_explanations(findings)
    top_titles = [item["title"] for item in narrative_findings[:3]]
    family_label = "issue family" if len(narrative_findings) == 1 else "issue families"
    return {
        "headline": verdict["message"].title(),
        "plainEnglish": (
            f"The contract has {len(findings)} audit signal(s) across {len(narrative_findings)} {family_label}. "
            "The biggest concerns are: "
            + "; ".join(top_titles)
            + "."
        ),
        "nextSteps": build_next_steps(narrative_findings),
        "metricExplanations": metric_explanations(),
        "findingExplanations": finding_explanations,
        "narrativeFindings": narrative_findings,
        "severityModel": SEVERITY_MODEL,
    }


def analyze_contract(contract_name, source):
    validation_issues = validate_contract_source(contract_name, source)
    if validation_issues:
        return invalid_contract_response(contract_name, source, validation_issues)

    findings = [map_preflight_finding(finding) for finding in check_source(source)]
    lines = source.splitlines()

    for index, line in enumerate(lines):
        line_number = index + 1
        if re.search(r"ignore previous|system prompt|developer message|jailbreak|override", line, re.I):
            add_finding(
                findings,
                "adversarial",
                "high",
                f"L{line_number}: [ADVERSARIAL] Steering language can influence validator framing.",
                line=line_number,
            )

    if re.search(r"resolution_criteria|criteria|subjective|successful|reasonable|fair", source, re.I):
        line_number = first_matching_line(source, r"resolution_criteria|criteria|subjective|successful|reasonable|fair")
        add_finding(
            findings,
            "interpretive",
            "medium",
            "[INTERPRETIVE] Outcome language may support multiple valid interpretations.",
            line=line_number,
        )

    url_count = len(re.findall(r"https?://", source))
    if url_count >= 3:
        add_finding(
            findings,
            "reality",
            "medium",
            f"[REALITY] {url_count} external URLs found. Check snapshot consistency across sources.",
            line=first_matching_line(source, r"https?://"),
        )

    loop_count = len(re.findall(r"\b(for|while)\b", source))
    render_count = source.count("gl.nondet.web.render")
    if loop_count > 2 or render_count > 3:
        add_finding(
            findings,
            "economic",
            "high",
            "[ECONOMIC] Repeated loops or web renders may increase validator cost.",
            line=first_matching_line(source, r"\b(for|while)\b|gl\.nondet\.web\.render"),
        )

    for finding in findings:
        finding["snippet"] = snippet_for_line(source, finding.get("line"))

    int_score = score_by_pillar(findings, "interpretive")
    adv_score = score_by_pillar(findings, "adversarial")
    eco_score = score_by_pillar(findings, "economic")
    real_score = score_by_pillar(findings, "reality")
    det_score = score_by_pillar(findings, "deterministic")

    agreement = max(50, 98 - (int_score * 7) - (adv_score * 5) - (real_score * 3))
    drift = min(95, 2 + (adv_score * 12) + (int_score * 5) + (real_score * 3))
    compute = 1.0 + (eco_score * 0.8) + (render_count * 0.25)
    appeal_risk = classify_risk(int_score + adv_score + (eco_score * 0.5))
    reality_risk = classify_risk(real_score)
    deterministic_risk = classify_risk(det_score)

    metrics = {
        "consensus": {
            "value": f"{round(agreement)}%",
            "className": "val-high" if agreement < 75 else "val-medium" if agreement < 90 else "val-low",
        },
        "appeal": {
            "value": appeal_risk,
            "className": metric_class(appeal_risk),
        },
        "drift": {
            "value": f"{round(drift)}%",
            "className": "val-high" if drift > 20 else "val-medium" if drift > 5 else "val-low",
        },
        "reality": {
            "value": reality_risk,
            "className": metric_class(reality_risk),
        },
        "compute": {
            "value": f"{compute:.1f}x",
            "className": "val-high" if compute > 3 else "val-medium" if compute > 1.5 else "val-low",
        },
        "deterministic": {
            "value": deterministic_risk,
            "className": metric_class(deterministic_risk),
        },
    }

    logs = [
        {"message": f"[PREFLIGHT] Analyzing {contract_name}...", "type": "info"},
        {
            "message": (
                "[PREFLIGHT] No deterministic issues detected."
                if not findings
                else f"[PREFLIGHT] {len(findings)} signal(s) detected."
            ),
            "type": "success" if not findings else "warning",
        },
        {"message": "[ORACLE] Running live 5-pillar audit engine.", "type": "system"},
    ]

    for finding in findings:
        log_type = "warning" if finding["severity"] in ("critical", "high") else "info"
        logs.append({"message": finding["message"], "type": log_type})

    logs.extend([
        {"message": f"[CONSENSUS] Estimated validator agreement: {round(agreement)}%", "type": "info"},
        {"message": f"[CONSENSUS] Appeal probability: {appeal_risk}", "type": "warning" if appeal_risk == "HIGH" else "info"},
        {"message": f"[ECONOMICS] Expected validator compute multiplier: {compute:.1f}x", "type": "warning" if compute > 1.5 else "info"},
        {
            "message": (
                "[REPORT] Audit complete. Review highlighted findings before deploying high-value markets."
                if findings
                else "[REPORT] Audit complete. No high-signal findings in submitted source."
            ),
            "type": "warning" if findings else "success",
        },
    ])

    verdict = {
        "status": "review" if findings else "acceptable",
        "message": (
            "REVIEW REQUIRED BEFORE HIGH-VALUE DEPLOYMENT"
            if findings
            else "CONSENSUS STABILITY ACCEPTABLE"
        ),
    }

    return {
        "contractName": contract_name,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "engine": "genlayer-auditor-live",
        "version": read_version(),
        "metrics": metrics,
        "findings": findings,
        "summary": build_summary(findings, metrics, verdict),
        "severityModel": SEVERITY_MODEL,
        "logs": logs,
        "verdict": verdict,
    }


def read_version():
    version_path = os.path.join(os.path.dirname(__file__), "..", "VERSION")
    try:
        with open(version_path, "r", encoding="utf-8") as version_file:
            return version_file.read().strip()
    except OSError:
        return "unknown"
