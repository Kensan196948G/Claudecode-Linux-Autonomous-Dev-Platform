# Notification Policy

## Purpose
- Send important DevOS events through the existing mail path.
- Keep Gmail credentials outside the repository.
- Log notification attempts for later inspection.

## Mail Path
- `notifications/notifier.py` dispatches events.
- `ops/notify/send_alert.sh` sends mail only when `ALERT_MAIL_ENABLED=true`.
- `ALERT_MAIL_TO` must be configured in `config/devos.env` or the environment.

## Events
- ERROR
- SUCCESS
- LIMIT
- RESET
