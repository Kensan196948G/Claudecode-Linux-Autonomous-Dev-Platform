#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${TARGET_DIR:-/opt/claudecode-devos}"
SERVICE_USER="${SERVICE_USER:-kensan}"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo: sudo SERVICE_USER=$SERVICE_USER $0" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
rsync -a --delete \
  --exclude 'runtime/logs/*' \
  --exclude 'runtime/pids/*' \
  --exclude 'runtime/tmp/*' \
  --exclude 'runtime/metrics/*' \
  --exclude 'runtime/usage/*' \
  --exclude 'runtime/ci/*' \
  --exclude 'runtime/decisions/*' \
  --exclude 'runtime/prompts/*' \
  --exclude 'runtime/agent_logs/*' \
  --exclude 'runtime/issues/*' \
  --exclude 'runtime/dashboard/*' \
  --exclude 'runtime/projects/*' \
  --exclude 'runtime/history/*' \
  --exclude 'runtime/worktrees/*' \
  --exclude 'runtime/ui_actions/*' \
  --exclude 'runtime/evolution/logs/*' \
  --exclude 'runtime/evolution/metrics/*' \
  --exclude 'runtime/evolution/history/*' \
  --exclude 'runtime/cluster/*' \
  --exclude 'runtime/archive/*' \
  --exclude 'cluster/events/*' \
  --exclude 'cluster/locks/*' \
  --exclude 'cluster/failures/*' \
  --exclude 'cluster/archive/*' \
  --exclude 'cluster/leader/leader.json' \
  --exclude 'cluster/jobs/job-*.json' \
  --exclude 'strategy/scores/*' \
  --exclude 'strategy/history/*' \
  "$SOURCE_DIR/" "$TARGET_DIR/"

chown -R "$SERVICE_USER:$SERVICE_USER" "$TARGET_DIR"
chmod -R u=rwX,go=rX "$TARGET_DIR"
chmod +x "$TARGET_DIR"/ai/*.sh "$TARGET_DIR"/ai/*.py "$TARGET_DIR"/bin/*.sh "$TARGET_DIR"/ci/*.sh "$TARGET_DIR"/ci/*.py "$TARGET_DIR"/cluster/controller/*.py "$TARGET_DIR"/cluster/controller/*.sh "$TARGET_DIR"/cluster/leader/*.py "$TARGET_DIR"/cluster/workers/*.py "$TARGET_DIR"/cluster/workers/*.sh "$TARGET_DIR"/core/*.py "$TARGET_DIR"/evolution/*.py "$TARGET_DIR"/evolution/metrics/*.py "$TARGET_DIR"/evolution/optimizer/*.py "$TARGET_DIR"/github/*.sh "$TARGET_DIR"/notifications/*.py "$TARGET_DIR"/ops/*.py "$TARGET_DIR"/ops/*.sh "$TARGET_DIR"/ops/notify/*.sh "$TARGET_DIR"/reports/*.py "$TARGET_DIR"/strategy/*.py "$TARGET_DIR"/strategy/*.sh "$TARGET_DIR"/web/*.py

sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/claudecode-session.service" > /etc/systemd/system/claudecode-session.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/memory-guard.service" > /etc/systemd/system/memory-guard.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/usage-manager.service" > /etc/systemd/system/usage-manager.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/github-loop.service" > /etc/systemd/system/github-loop.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/autonomous-orchestrator.service" > /etc/systemd/system/autonomous-orchestrator.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/devos-dashboard.service" > /etc/systemd/system/devos-dashboard.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/devos-report.service" > /etc/systemd/system/devos-report.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/devos-evolution.service" > /etc/systemd/system/devos-evolution.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/cluster-orchestrator.service" > /etc/systemd/system/cluster-orchestrator.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/cluster-requeue.service" > /etc/systemd/system/cluster-requeue.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/worker-heartbeat.service" > /etc/systemd/system/worker-heartbeat.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/worker-poll-jobs.service" > /etc/systemd/system/worker-poll-jobs.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/strategy-cycle.service" > /etc/systemd/system/strategy-cycle.service
sed "s/^User=.*/User=$SERVICE_USER/" "$TARGET_DIR/systemd/log-retention.service" > /etc/systemd/system/log-retention.service
cp "$TARGET_DIR/systemd/claudecode-session.timer" /etc/systemd/system/claudecode-session.timer
cp "$TARGET_DIR/systemd/memory-guard.timer" /etc/systemd/system/memory-guard.timer
cp "$TARGET_DIR/systemd/usage-manager.timer" /etc/systemd/system/usage-manager.timer
cp "$TARGET_DIR/systemd/autonomous-orchestrator.timer" /etc/systemd/system/autonomous-orchestrator.timer
cp "$TARGET_DIR/systemd/devos-report.timer" /etc/systemd/system/devos-report.timer
cp "$TARGET_DIR/systemd/devos-evolution.timer" /etc/systemd/system/devos-evolution.timer
cp "$TARGET_DIR/systemd/cluster-orchestrator.timer" /etc/systemd/system/cluster-orchestrator.timer
cp "$TARGET_DIR/systemd/cluster-requeue.timer" /etc/systemd/system/cluster-requeue.timer
cp "$TARGET_DIR/systemd/worker-heartbeat.timer" /etc/systemd/system/worker-heartbeat.timer
cp "$TARGET_DIR/systemd/worker-poll-jobs.timer" /etc/systemd/system/worker-poll-jobs.timer
cp "$TARGET_DIR/systemd/strategy-cycle.timer" /etc/systemd/system/strategy-cycle.timer
cp "$TARGET_DIR/systemd/log-retention.timer" /etc/systemd/system/log-retention.timer

systemctl daemon-reload

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "  python3 -m pip install --user -r $TARGET_DIR/requirements.txt"
echo "  sudo apt install msmtp msmtp-mta mailutils"
echo "  gh auth login"
echo "  sudo systemctl enable --now memory-guard.timer"
echo "  sudo systemctl enable --now usage-manager.timer"
echo "  sudo systemctl enable --now claudecode-session.timer"
echo "  sudo systemctl enable --now github-loop.service  # optional"
echo "  sudo systemctl enable --now autonomous-orchestrator.timer  # optional"
echo "  sudo systemctl enable --now devos-dashboard.service  # optional"
echo "  sudo systemctl enable --now devos-report.timer  # optional"
echo "  sudo systemctl enable --now devos-evolution.timer  # optional"
echo "  sudo systemctl enable --now cluster-orchestrator.timer  # controller optional"
echo "  sudo systemctl enable --now cluster-requeue.timer  # controller optional"
echo "  sudo systemctl enable --now worker-heartbeat.timer worker-poll-jobs.timer  # worker optional"
echo "  sudo systemctl enable --now strategy-cycle.timer  # optional"
echo "  sudo systemctl enable --now log-retention.timer  # recommended"
