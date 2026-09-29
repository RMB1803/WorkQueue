import time


def process_task(task_to_execute):
    """Process a task based on its type. Maps to Process_Task() in worker.go."""

    if not task_to_execute.payload:
        return "payload is empty"

    # Add your task type here, and perform the task under your if/elif
    if task_to_execute.type == "send_email":
        time.sleep(2)
        print("Sending email to", task_to_execute.payload["to"],
              "with subject", task_to_execute.payload["subject"])
        return None

    elif task_to_execute.type == "resize_image":
        print("Resizing image to x cordinate:",
              task_to_execute.payload["new_x"],
              "y cordinate:", task_to_execute.payload["new_y"])
        return None

    elif task_to_execute.type == "generate_pdf":
        print("Generating pdf...")
        return None

    elif task_to_execute.type == "":
        return "task type is empty"

    else:
        return "unsupported task"
