# WorkTree Policy

## Purpose
- Avoid direct work on the base branch.
- Isolate `feature` and `repair` attempts.
- Reduce the blast radius of autonomous changes.

## Rules
1. `develop` uses a `feature` worktree when WorkTree mode is enabled.
2. `repair_ci` uses a `repair` worktree when WorkTree mode is enabled.
3. WorkTrees are removed after processing.
4. Local WorkTrees are cleaned after PR creation.
5. Direct commits to the base branch are not allowed.

## Benefits
- Better isolation for autonomous repair.
- Easier cleanup when an attempt goes wrong.
- Safer future parallelism.
