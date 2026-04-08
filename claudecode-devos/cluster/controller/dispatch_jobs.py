#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
STATE = Path(os.environ.get("CLUSTER_STATE_FILE", DEVOS_HOME / "cluster/controller/cluster_state.json"))
JOBS_DIR = DEVOS_HOME / "cluster/jobs"


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def choose_worker(workers, required_tags):
    candidates = []
    required = set(required_tags or [])
    for worker in workers:
        if not worker.get("enabled", False):
            continue
        if worker.get("drain", False):
            continue
        if worker.get("current_jobs", 0) >= worker.get("max_jobs", 1):
            continue
        if not required.issubset(set(worker.get("tags", []))):
            continue
        candidates.append(worker)

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.get("current_jobs", 0), item.get("cpu_percent") or 0, -(item.get("memory_free_mb") or 0)))
    return candidates[0]


def main():
    state = load_state()
    state.setdefault("jobs", {}).setdefault("queued", [])
    state["jobs"].setdefault("running", [])
    state["jobs"].setdefault("completed", [])
    state["jobs"].setdefault("failed", [])
    for worker in state.get("workers", []):
        worker["current_jobs"] = 0
        if worker.get("status") == "busy":
            worker["status"] = "idle"

    queued_jobs = []
    running = []
    completed = []
    failed = []
    for job_file in JOBS_DIR.glob("job-*.json"):
        job = json.loads(job_file.read_text(encoding="utf-8"))
        status = job.get("status")
        if status == "queued":
            queued_jobs.append((job_file, job))
        elif status in ("assigned", "running"):
            running.append(job["job_id"])
            assigned = job.get("assigned_worker")
            for worker in state.get("workers", []):
                if worker.get("id") == assigned:
                    worker["current_jobs"] = worker.get("current_jobs", 0) + 1
                    worker["status"] = "busy"
                    break
        elif status == "completed":
            completed.append(job["job_id"])
        elif status == "failed":
            failed.append(job["job_id"])

    queued_jobs.sort(key=lambda item: item[1].get("priority", 0), reverse=True)
    state["jobs"]["queued"] = [job["job_id"] for _, job in queued_jobs]
    state["jobs"]["running"] = running
    state["jobs"]["completed"] = completed[-100:]
    state["jobs"]["failed"] = failed[-100:]

    for job_file, job in queued_jobs:
        worker = choose_worker(state.get("workers", []), job.get("required_tags", []))
        if not worker:
            continue

        job["status"] = "assigned"
        job["assigned_worker"] = worker["id"]
        job["assigned_at"] = timestamp()
        write_json(job_file, job)

        worker["current_jobs"] = worker.get("current_jobs", 0) + 1
        worker["status"] = "busy"
        state["jobs"]["running"].append(job["job_id"])
        state["jobs"]["queued"] = [item for item in state["jobs"]["queued"] if item != job["job_id"]]

    state["jobs"]["running"] = list(dict.fromkeys(state["jobs"]["running"]))
    state["cluster"]["last_dispatch_at"] = timestamp()
    write_json(STATE, state)


if __name__ == "__main__":
    main()
