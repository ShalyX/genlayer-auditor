# Advanced GenLayer Attack Vectors

This reference categorizes the "Pillars of Failure" for Intelligent Contracts.

## P1: Ambiguity & Interpretation Fractures
- **V1: Polysemantic Clauses**: Clauses that have multiple, conflicting, yet valid legal or logical meanings.
- **V2: Contextual Drift**: Meaning shifts when evaluated at different block times or external conditions.

## P2: Prompt Steering & Validator Bias
- **V3: Direct Instruction Injection**: Attacker input overrides the contract's "system" prompt.
- **V4: Cognitive Priming**: Input that primes the validator to favor a specific outcome (e.g., emotional pleading).
- **V5: Authority Bias Injection**: Falsified "expert" testimony within prompts.

## P3: Reality & Oracle Integrity
- **V6: Web Result Poisoning**: Redirecting to or poisoning the source of truth used in `gl.nondet.web.render`.
- **V7: Discrepancy Griefing**: Forcing a consensus failure by triggering source-data deltas during validator execution.

## P4: Consensus & Network Economics
- **V8: Appeal Exhaustion**: Designing contracts that inevitably trigger nested appeals to drain network resources.
- **V9: Resource-Heavy Prompts**: Prompts designed to consume maximum token/time budget of validators.
- **V10: Emergent Multi-agent Collusion**: Cross-contract interactions that create unforeseen biases.

## P5: Specification Gaming
- **V11: The "Loophole" Logic**: Finding a literal interpretation that satisfies the prompt but violates the contract's spirit.
- **V12: Reward Manipulation**: Bias toward results that result in higher payouts/fees for specific parties.
