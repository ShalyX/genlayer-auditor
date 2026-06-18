# GenLayer Auditor: The Oracle of Interpretation (README)

**Version**: 1.0.0  
**Status**: Ship-Ready  
**Philosophy**: Predictive "Pre-Crime" Auditing for AI-Native Contracts.

## Overview
The **GenLayer Auditor** is a high-intelligence security framework designed to identify "fractures in truth" before they occur. Unlike traditional auditors that focus on static code bugs, the Oracle models the **probabilistic convergence** of multiple validator minds.

## The 5 Pillars of Intelligence
1. **Ambiguity Surface Mapping**: Measures the variance of natural language interpretations.
2. **Adversarial Prompt Simulation**: Tests resilience to prompt injection and validator steering.
3. **Data Dependency Stress Testing**: Simulates consensus instability across conflicting external sources.
4. **Consensus Variance Simulation**: Models agreement rates across different LLM "personalities".
5. **Economic Attack Modeling**: Calculates the cost-to-disruption ratio for appeals and resources.

## Quick Start
Start the live local auditor:
```bash
python scripts/server.py
```

Then open:
```text
http://127.0.0.1:8765
```

To invoke the full specialist workflow in your terminal/LLM interface:
> "Run genlayer-auditor deep on ./contracts"

For deterministic local checks, run:
```bash
python scripts/preflight.py ./contracts
```

The browser UI is served by `scripts/server.py` and calls the live `/api/audit` endpoint. It runs deterministic preflight checks plus the local 5-pillar heuristic engine over pasted contract source.

The live UI includes:
- Risky and clean sample contracts for quick testing.
- Plain-English explanations for every metric and finding.
- Line-linked findings with snippets and suggested fixes.
- Markdown report export for sharing audit results.

## Directory Structure
- `SKILL.md`: The Orchestration Router.
- `agents/`: Specialist reasoning prompts (Pillar 1-5).
- `references/`: Knowledge base for advanced GenLayer attack vectors.
- `scripts/`: Deterministic preflight scanner (`preflight.py`).
- `scripts/server.py`: Local live audit server and API.
- `scripts/audit_engine.py`: Metrics and finding engine used by the API.
- `ui/`: Static browser interface for quick local heuristic checks.
- `reports/`: Default location for generated findings.

## Stability Metrics
- **95%+ (Finance Tier)**: Stable for high-value institutional assets.
- **85%+ (Logic Tier)**: Stable for core protocol execution.
- **70%+ (Gaming Tier)**: Acceptable for social/probabilistic games.
