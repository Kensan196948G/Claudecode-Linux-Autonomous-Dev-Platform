#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
OUT = DEVOS_HOME / "runtime/agent_logs/agent_events.jsonl"


def log_event(agent, action, result, duration_sec, issue=None, project_id=None, detail=None):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "issue": issue,
        "project_id": project_id,
        "result": result,
        "duration_sec": float(duration_sec),
        "detail": detail or {},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print(json.dumps(event, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Append a structured DevOS agent event.")
    parser.add_argument("--agent", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--result", default="unknown", choices=["success", "failure", "skipped", "running", "unknown"])
    parser.add_argument("--duration-sec", type=float, default=0)
    parser.add_argument("--issue")
    parser.add_argument("--project-id")
    parser.add_argument("--detail", default="{}")
    args = parser.parse_args()
    log_event(
        args.agent,
        args.action,
        args.result,
        args.duration_sec,
        issue=args.issue,
        project_id=args.project_id,
        detail=json.loads(args.detail),
    )


if __name__ == "__main__":
    main()
