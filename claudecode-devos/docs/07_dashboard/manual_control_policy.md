# Manual Control Policy

## Available Actions
- `develop`
- `repair_ci`
- `cooldown`
- `suspend`
- `resume`
- `select project`

## Notes
- While `manual_override=true`, the orchestrator prioritizes the dashboard action.
- `resume` clears the manual override and returns to automatic decision mode.
- `suspend` is treated as a stop for autonomous execution.
- Manual project selection sets `control.manual_project_id` and runs the selected project through the scheduler path.
