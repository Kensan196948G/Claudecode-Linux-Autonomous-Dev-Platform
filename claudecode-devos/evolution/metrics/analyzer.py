#!/usr/bin/env python3
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
LOG_FILE = Path(os.environ.get("DEVOS_EVOLUTION_LOG_FILE", DEVOS_HOME / "runtime/evolution/logs/execution_log.json"))
METRICS_FILE = Path(os.environ.get("DEVOS_EVOLUTION_METRICS_FILE", DEVOS_HOME / "runtime/evolution/metrics/latest_metrics.json"))


def load_logs():
    if not LOG_FILE.exists():
        return []
    text = LOG_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return json.loads(text)


def analyze():
    logs = load_logs()
    total = len(logs)
    success = sum(1 for item in logs if item.get("result") == "success")
    fail = sum(1 for item in logs if item.get("result") not in ("success", "skipped"))
    durations = [float(item.get("duration") or 0) for item in logs]
    avg_time = sum(durations) / total if total else 0
    metrics = {
        "total": total,
        "success": success,
        "fail": fail,
        "success_rate": success / total if total else 0,
        "fail_rate": fail / total if total else 0,
        "avg_time": avg_time,
    }
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=METRICS_FILE.parent, delete=False) as tmp:
        json.dump(metrics, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, METRICS_FILE)
    return metrics


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
