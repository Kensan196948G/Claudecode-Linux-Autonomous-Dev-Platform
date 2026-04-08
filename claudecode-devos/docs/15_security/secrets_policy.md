# Secrets Policy

## Rules
- Secrets are never committed to Git.
- Local secrets live in environment files outside Git or in systemd environment overrides.
- GitHub tokens use `gh auth login` or GitHub Secrets.
- Gmail uses msmtp app password outside the repository.

## Examples
- `ALERT_MAIL_TO`
- msmtp password
- GitHub token
- API keys

## Verification
- Review `.gitignore` before adding new runtime files.
- Never place credentials in `state.json`, project docs, generated reports, or Dashboard output.
