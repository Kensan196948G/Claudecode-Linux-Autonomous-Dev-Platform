# Multi Project Policy

## Selection Rule
- Only `active` projects are eligible.
- Selection uses priority, weight, and release due date.
- Expired projects are ignored.

## Safe Defaults
- `max_parallel_projects = 1`
- `scheduler.mode = single`
- Resource pressure moves the orchestrator into `cooldown`.
- CI failure moves the orchestrator into `repair_ci`.

## Project Fields
- `id`
- `name_ja`
- `name_en`
- `repository`
- `docs_dir`
- `session_prompt_file`
- `priority`
- `weight`
- `status`
- `release_due`
