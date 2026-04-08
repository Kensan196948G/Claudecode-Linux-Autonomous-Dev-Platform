#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
LOG_FILE = Path(os.environ.get("DEVOS_EVOLUTION_LOG_FILE", DEVOS_HOME / "runtime/evolution/logs/execution_log.json"))


def load_log():
    if not LOG_FILE.exists():
        return []
    text = LOG_FILE.read_text(encoding="utf-8").strip()
    if not text:
        return []
    return json.loads(text)


def save_log(entries):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=LOG_FILE.parent, delete=False) as tmp:
        json.dump(entries[-1000:], tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, LOG_FILE)


def collect_log(event, result, duration, detail=None):
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "result": result,
        "duration": float(duration),
        "detail": detail or {},
    }
    entries = load_log()
    entries.append(entry)
    save_log(entries)
    return entry


def main():
    parser = argparse.ArgumentParser(description="Collect DevOS evolution execution logs.")
    parser.add_argument("event")
    parser.add_argument("result")
    parser.add_argument("duration", type=float)
    parser.add_argument("--detail", default="{}")
    args = parser.parse_args()
    detail = json.loads(args.detail)
    print(json.dumps(collect_log(args.event, args.result, args.duration, detail), ensure_ascii=False))


if __name__ == "__main__":
    main()
