# Reporting Policy

## Purpose
- Generate a lightweight Markdown report from state.json and projects.json.
- Preserve usage, resource, CI, project, and repair history in a human-readable form.
- Keep generated reports local to the DevOS host.

## Schedule
- The default systemd timer runs hourly.
- Daily report generation can be added separately if needed.

## Output
- Reports are written to `reports/report_YYYY-MM-DD_HH-MM.md`.
- Generated report files are runtime artifacts and are not committed by default.
