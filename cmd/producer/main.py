import json
import os
import sys

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

# Add project root to path so we can import internal packages
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from internal.task.task import Task

app = FastAPI()

rdb = None


def connect_redis():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("REDIS_URL is not set")
        sys.exit(1)
    return redis.from_url(redis_url)


@app.post("/enqueue")
async def post_handler(request: Request):
    # Read the request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Bad Request")

    task = Task(
        type=body.get("type", ""),
        payload=body.get("payload", {}),
        retries=body.get("retries", 0),
    )

    if task.type == "":
        raise HTTPException(status_code=400, detail="Bad Request")

    if task.type == "send_email":
        if task.payload.get("to") is None or task.payload.get("subject") is None:
            raise HTTPException(
                status_code=400,
                detail="Bad request,pass to and subject fields inside the payload",
            )

    # Serialize the task to JSON
    task_json = json.dumps(
        {"type": task.type, "payload": task.payload, "retries": task.retries}
    )

    # Push to Redis list "task_queue"
    res = rdb.rpush("task_queue", task_json)

    print("Length of queue", res)

    return PlainTextResponse(
        f"Task of type '{task.type}' has been successfully added to the queue"
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    # rdb is a module-level global so the route handler above can reach it
    global rdb
    rdb = connect_redis()

    port = int(os.getenv("PORT_PRODUCER", "8080"))
    print(f"Starting the server on port  :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
