# Judging Criteria: The Consensus FP Gate

A finding is only valid if it presents a concrete "fracture in truth" or a manipulable logic path.

## 1. The Stability Threshold
- **Score >= 90%**: Stable. High confidence that validators will agree. Findings here are likely False Positives unless a Critical exploit (e.g., prompt injection) is proven.
- **Score 75% - 89%**: Vulnerable. Potential for occasional appeals or disagreement.
- **Score < 75%**: Critical Failure. High likelihood of consensus breakage or frequent appeals.

## 2. Liveness vs. Security Trade-offs (NEW)
- **Guideline**: Open access to state-changing functions is NOT a vulnerability if it serves as a decentralized fallback for liveness, provided:
    1. The state transition is restricted by significant time-locks (e.g., 24h+ after deadline).
    2. The transition is non-reversible and leads to a desired game-state resolution.
    3. The function requires valid protocol data (hashes/commits) to execute.
- **Example**: `force_reveal` in `guesschain.py` is a secure fallback, whereas an unprotected `reset_room` would be a Critical vulnerability.

## 3. Evidence Requirements
Every finding must carry at least one evidence tag:
- `[PROMPT-TRACE]`: Concrete path from user input to LLM prompt.
- `[REALITY-DELTA]`: Simulation showing how conflicting data breaks the logical flow.
- `[VARIANCE-PROVED]`: Proof that different LLM minds reach different conclusions on the same clause.
- `[GRIEF-CALC]`: Mathematical proof of economic resource exhaustion.
- `[LIVENESS-CHECK]`: Verification that a fallback mechanism actually resolves the contract state.

## 3. Mandatory FP Gate Questions
1. Does the Equivalence Principle (`strict_eq`) catch this discrepancy before state finality? (If yes, severity is reduced).
2. Is the "ambiguity" merely stylistic, or does it change the financial outcome?
3. In a 5-validator set, how many would need to be "tricked" for the exploit to succeed? (GenLayer consensus logic).
