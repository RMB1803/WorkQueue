import json


def log_success(cur_task):
    """Log a successful task to logs.txt. Maps to LogSuccess() in logger.go."""
    try:
        payload_str = json.dumps(cur_task.payload)
    except Exception:
        payload_str = ""

    text = ("\n SUCCESS: Task type: " + cur_task.type
            + " Task payload: " + payload_str
            + " Retries left: " + str(cur_task.retries))

    try:
        with open("logs/logs.txt", "a") as f:
            f.write(text)
    except Exception as e:
        print("Error writing to the log file:", e)
        return

    print("logged successfully to the file")


def log_failure(cur_task, cur_err):
    """Log a failed task to logs.txt. Maps to LogFailure() in logger.go."""
    try:
        payload_str = json.dumps(cur_task.payload)
    except Exception:
        payload_str = ""

    text = ("FAILURE: Task type: " + cur_task.type
            + " Task payload: " + payload_str
            + " Retries left: " + str(cur_task.retries)
            + "Error message: " + str(cur_err))

    try:
        with open("logs/logs.txt", "a") as f:
            f.write(text)
    except Exception as e:
        print("Error writing to the log file:", e)
        return

    print("logged successfully to the file")
