import json
import os
import sys
import threading

import redis
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Add project root to path so we can import internal packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from internal.task.task import Task
from internal.worker.worker import process_task
from internal.logger.logger import log_success, log_failure

app = FastAPI()

jobs_done = 0
jobs_failed = 0
total_jobs_in_queue = 0

rdb = None


def connect_redis():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("REDIS_URL is not set")
        sys.exit(1)
    return redis.from_url(redis_url)


@app.get("/metrics")
def metrics_handler():
    """Return worker metrics. Maps to metrics_handler() in cmd/worker/main.go."""
    return JSONResponse({
        "total_jobs_in_queue": total_jobs_in_queue,
        "jobs_done": jobs_done,
        "jobs_failed": jobs_failed,
    })


def run_worker(rdb_conn):
    """Worker loop that pops tasks from Redis and processes them.
    Maps to Run_Worker() in cmd/worker/main.go."""
    global jobs_done, jobs_failed, total_jobs_in_queue

    while True:
        try:
            # BLPOP blocks until a task is available (timeout=0 means block forever)
            res = rdb_conn.blpop("task_queue", timeout=0)
        except Exception as e:
            print("Error connecting to Redis:", e)
            break

        if res is None:
            continue

        total_jobs_in_queue = rdb_conn.llen("task_queue")

        # res is (key, value) tuple; value is the JSON string
        raw_task = res[1]

        try:
            data = json.loads(raw_task)
        except Exception:
            print("Can not parse data from redis")
            continue

        task_to_execute = Task(
            type=data.get("type", ""),
            payload=data.get("payload", {}),
            retries=data.get("retries", 0),
        )

        retries_left = task_to_execute.retries

        err_worker = process_task(task_to_execute)

        if err_worker is not None:
            jobs_failed += 1
            log_failure(task_to_execute, err_worker)
            retries_left -= 1
            print("Error processing task:", err_worker, " Putting it back to the queue")
            if retries_left > 0:
                task_to_execute.retries = retries_left
                task_json = json.dumps(
                    {"type": task_to_execute.type,
                     "payload": task_to_execute.payload,
                     "retries": task_to_execute.retries}
                )
                rdb_conn.rpush("task_queue", task_json)
                continue
            else:
                print("Task failed after all retries")
                continue
        else:
            jobs_done += 1
            log_success(task_to_execute)
            print("Task done successfully")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    rdb = connect_redis()

    port = int(os.getenv("PORT_WORKER", "8081"))

    n = 3  # Number of worker threads to launch

    for i in range(n):
        t = threading.Thread(target=run_worker, args=(rdb,), daemon=True)
        t.start()

    print(f"Started {n} worker threads")
    print(f"Starting metrics server on port  :{port}")

    uvicorn.run(app, host="0.0.0.0", port=port)
