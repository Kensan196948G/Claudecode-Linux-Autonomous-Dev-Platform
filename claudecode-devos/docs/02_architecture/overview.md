# Architecture Overview

```text
systemd timer
  -> run-session.sh
    -> project-dispatcher.sh
    -> prompt composition from Docs + state.json + START_PROMPT.md
    -> claude-safe.sh

systemd timer
  -> memory_guard.py
    -> state_manager.py
    -> notifications/notifier.py when recovery is triggered
    -> recovery.sh when memory or swap threshold is breached

systemd timer
  -> usage_manager.py
    -> reset daily usage after date changes
    -> reset weekly usage once during Friday 13:00

run-session.sh
  -> usage_manager.py check before Claude start
  -> usage_manager.py record after Claude exit

github/full_loop.sh
  -> issue_manager.sh selects the next open issue
  -> sync.sh creates a feature branch and runs claude-safe
  -> pr_manager.sh opens a PR
  -> pr_manager.sh requests auto merge only when GITHUB_AUTO_MERGE=true

bin/autonomous_orchestrator.sh
  -> usage_manager.py reset/check
  -> memory_guard.py
  -> ci/check_ci_status.sh
  -> decision_engine.py chooses next_action
  -> ai/issue_prioritizer.py and ai/prompt_builder.py when active work is needed
  -> run-scheduled-project.sh, ci/repair_ci.sh, cooldown, or suspend
  -> ci/merge_green_prs.sh when auto merge is explicitly enabled
  -> ai/agent_logger.sh appends an agent timeline

ops/project_scheduler.py
  -> ranks active projects by priority, weight, and release_due
  -> writes runtime/projects/selected_project.json
  -> updates scheduler and projects_runtime state

web/app.py
  -> reads state.json, projects.json, selected_project.json, and log tails
  -> serves /, /api/state, and /api/projects
  -> writes manual control requests through web/manual_control.py
  -> edits project priority, status, and weight through web/manual_control.py

ops/worktree_manager.sh
  -> creates isolated feature or repair worktrees
  -> updates worktree.current_* in state.json
  -> removes and prunes completed worktrees

reports/report_generator.py
  -> generates markdown reports from state.json and projects.json
  -> updates reports.last_generated_at and reports.last_report_file

notifications/notifier.py
  -> logs events
  -> delegates mail delivery to ops/notify/send_alert.sh

core/evolution_loop.py
  -> analyzes runtime/evolution execution logs
  -> updates evolution mode and task strategy
  -> writes runtime/prompts/evolution_instructions.md

cluster/controller/cluster_orchestrator.sh
  -> exits on non-leader controllers
  -> syncs cluster job/event files when enabled
  -> ingests worker heartbeats
  -> requeues failed jobs
  -> dispatches queued jobs to eligible workers

cluster/workers/poll_jobs.sh
  -> runs assigned JSON jobs through existing WorkTree-safe runners

strategy/run_strategy_cycle.sh
  -> scores active projects by ROI and strategic value
  -> updates project selection_status
  -> project_scheduler.py prioritizes selected/candidate projects

ops/log_retention.sh
  -> compresses older logs into runtime/archive/logs
  -> deletes old archives after the retention window
```

## State Flow
`state.json` is updated by `state_manager.py` and `usage_manager.py` with a file lock and atomic replacement. Session start, session end, resource metrics, Claude PID, recovery count, and usage counters all flow through this file.
