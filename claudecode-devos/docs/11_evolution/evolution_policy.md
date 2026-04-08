# Evolution Policy

## Purpose
- Collect execution outcomes.
- Analyze success rate, failure rate, and average duration.
- Tune DevOS operating mode through `state.json`.
- Generate prompt instructions for the next loop.

## Safety Rules
- Do not rewrite project `START_PROMPT.md` automatically.
- Write generated prompt guidance to `runtime/prompts/evolution_instructions.md`.
- Keep execution logs under `runtime/evolution`.
- Keep only bounded decision history in `state.json`.

## Modes
- normal: default controlled operation
- safe: smaller changes and focused verification
- aggressive: faster implementation when recent outcomes are healthy

## Task Strategy
- standard: normal workflow
- split: break slow tasks into smaller checkpoints
