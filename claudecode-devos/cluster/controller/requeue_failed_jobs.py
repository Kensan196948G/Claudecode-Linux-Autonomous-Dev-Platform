#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

DEVOS_HOME = Path(os.environ.get("DEVOS_HOME", "/opt/claudecode-devos"))
JOBS_DIR = DEVOS_HOME / "cluster/jobs"
FAILED_DIR = DEVOS_HOME / "cluster/failures"
ARCHIVE_DIR = DEVOS_HOME / "cluster/archive"
RETRY_LIMIT = int(os.environ.get("CLUSTER_JOB_RETRY_LIMIT", "3"))


def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def requeue():
    FAILED_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for failed_file in sorted(FAILED_DIR.glob("job-*.json")):
        job = json.loads(failed_file.read_text(encoding="utf-8"))
        retry = int(job.get("retry") or 0)
        if retry >= RETRY_LIMIT:
            job["status"] = "permanent_fail"
            job["permanent_failed_at"] = timestamp()
            archive_path = ARCHIVE_DIR / failed_file.name
            write_json(archive_path, job)
            failed_file.unlink()
            results.append({"job_id": job.get("job_id"), "action": "permanent_fail"})
            continue

        job["status"] = "queued"
        job["assigned_worker"] = None
        job["retry"] = retry + 1
        job["requeued_at"] = timestamp()
        job.pop("started_at", None)
        job.pop("completed_at", None)
        write_json(JOBS_DIR / failed_file.name, job)
        failed_file.unlink()
        results.append({"job_id": job.get("job_id"), "action": "requeued", "retry": job["retry"]})
    return results


if __name__ == "__main__":
    print(json.dumps(requeue(), ensure_ascii=False, indent=2))
