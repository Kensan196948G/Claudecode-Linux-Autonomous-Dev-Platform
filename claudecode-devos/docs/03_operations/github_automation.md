# GitHub Automation

## Requirements
- `gh auth login` must be completed for the service user.
- The target repository must have an `origin` remote and the configured base branch.
- `GITHUB_AUTO_MERGE` defaults to `false`.

## Flow
1. `issue_manager.sh` reads open issues and writes the selected issue into `state.json`.
2. `sync.sh` creates `feature/auto-issue-<number>-<timestamp>` from `origin/$GITHUB_BASE_BRANCH`.
3. `claude-safe.sh` runs with an issue-scoped prompt.
4. If files changed, `sync.sh` commits to the feature branch.
5. `pr_manager.sh` pushes the branch and creates or reuses a PR.
6. If `GITHUB_AUTO_MERGE=true`, `pr_manager.sh` requests GitHub auto-merge.

## Local Check
```bash
DEVOS_HOME="$PWD/claudecode-devos" GITHUB_LOOP_ONCE=true claudecode-devos/github/full_loop.sh /path/to/repo
```
