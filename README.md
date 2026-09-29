# WorkQueue

A background task processing system written in Python, using Redis as a job queue.

Tasks are submitted to a **Producer** HTTP API, stored in Redis, and processed by **Worker** threads running concurrently.

---

## Architecture

```
          POST /enqueue
               |
               v
       +---------------+
       |    Producer    |
       |  (FastAPI API) |
       +-------+-------+
               |  RPUSH
               v
       +---------------+
       |     Redis      |
       |   task_queue   |
       +-------+-------+
               |  BLPOP
               v
       +---------------+
       |    Worker      |
       |  (3 threads)   |
       +-------+-------+
               |
       +-------+-------+
       |               |
       v               v
   logs/logs.txt    GET /metrics
```

The Producer and Worker are independent services that communicate only through Redis. The Producer pushes tasks into Redis; the Worker pulls and processes them.

---

## Task Format

Every task is a JSON object with three fields:

```json
{
    "type": "send_email",
    "retries": 3,
    "payload": {
        "to": "user@example.com",
        "subject": "Welcome!"
    }
}
```

| Field | Required | Description |
|---|---|---|
| `type` | Yes | What kind of task to run |
| `retries` | No | How many times to retry on failure (default 0) |
| `payload` | No | Task-specific data as key-value pairs |

---

## Supported Task Types

| Type | Required Payload Fields | What it does |
|---|---|---|
| `send_email` | `to`, `subject` | Simulates sending an email (sleeps 2s) |
| `resize_image` | `new_x`, `new_y` | Prints the target image dimensions |
| `generate_pdf` | _(none)_ | Prints a PDF generation message |

To add a new task type, add an `elif` block in [internal/worker/worker.py](internal/worker/worker.py).

---

## Retries

If a task fails, the worker:
1. Increments `jobs_failed`
2. Logs the failure to `logs/logs.txt`
3. Decrements `retries` by 1
4. If retries remain → pushes the task back to `task_queue`
5. If no retries remain → prints "Task failed after all retries"

---

## Metrics

The worker exposes `GET /metrics` returning:

```json
{
    "total_jobs_in_queue": 2,
    "jobs_done": 10,
    "jobs_failed": 1
}
```

| Field | Description |
|---|---|
| `total_jobs_in_queue` | Current number of tasks in Redis |
| `jobs_done` | Total tasks successfully processed |
| `jobs_failed` | Total tasks that failed at least once |

---

## Logging

Every task execution is appended to `logs/logs.txt`:

```
 SUCCESS: Task type: send_email Task payload: {"to": "..."} Retries left: 3
FAILURE: Task type: send_email Task payload: {"to": "..."} Retries left: 0Error message: payload is empty
```

---

## Project Structure

```
WorkQueue/
├── cmd/
│   ├── producer/
│   │   └── main.py          # Producer HTTP server
│   └── worker/
│       └── main.py          # Worker threads + metrics server
├── internal/
│   ├── task/
│   │   └── task.py          # Task dataclass
│   ├── worker/
│   │   └── worker.py        # process_task() function
│   └── logger/
│       └── logger.py        # log_success() / log_failure()
├── tests/
│   └── test_workqueue.py    # Unit tests
├── logs/
│   └── logs.txt             # Written by the worker (gitignored)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Running Locally

### 1. Prerequisites

- Python 3.12+
- A running Redis instance (e.g. `redis-server` or `docker run -p 6379:6379 redis:7-alpine`)

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
REDIS_URL=redis://localhost:6379
PORT_PRODUCER=8080
PORT_WORKER=8081
```

### 4. Start the Producer

```bash
python cmd/producer/main.py
```

### 5. Start the Worker (in a separate terminal)

```bash
python cmd/worker/main.py
```

### 6. Run the tests

```bash
pytest tests/test_workqueue.py -v
```

---

## Running with Docker Compose

Start the entire system (Redis + Producer + Worker) with one command:

```bash
docker compose up --build
```

| Service | Port | Description |
|---|---|---|
| redis | 6379 | Redis queue |
| producer | 8000 | Enqueue tasks |
| worker | 8001 | Process tasks + metrics |

Stop the system:

```bash
docker compose down
```

To also delete the logs volume:

```bash
docker compose down -v
```

---

## Example API Requests

**Enqueue a task (local):**

```bash
curl -X POST http://localhost:8080/enqueue \
  -H "Content-Type: application/json" \
  -d '{"type": "send_email", "retries": 3, "payload": {"to": "user@example.com", "subject": "Hello"}}'
```

**Enqueue a task (Docker):**

```bash
curl -X POST http://localhost:8000/enqueue \
  -H "Content-Type: application/json" \
  -d '{"type": "send_email", "retries": 3, "payload": {"to": "user@example.com", "subject": "Hello"}}'
```

**Response:**

```
Task of type 'send_email' has been successfully added to the queue
```

**Check metrics (local):**

```bash
curl http://localhost:8081/metrics
```

**Check metrics (Docker):**

```bash
curl http://localhost:8001/metrics
```

**Response:**

```json
{
    "total_jobs_in_queue": 0,
    "jobs_done": 5,
    "jobs_failed": 1
}
```

---

## How Redis connects Producer and Worker

Both services read `REDIS_URL` from the environment.

- **Locally:** `REDIS_URL=redis://localhost:6379`
- **Docker:** `REDIS_URL=redis://redis:6379` — `redis` is the Docker Compose service name, resolved automatically by Docker's internal DNS

```
Producer  --RPUSH-->  Redis  <--BLPOP--  Worker
```

The Producer and Worker never talk to each other directly. Redis is the only shared component.

---

*Originally a Go project by [Abhinav Jha](https://x.com/AbhinavXJ), reimplemented in Python.*