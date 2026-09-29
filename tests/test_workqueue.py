"""
Simple tests for WorkQueue Python implementation.

These tests check the core logic without needing a running Redis instance.
Run with:  pytest tests/test_workqueue.py -v
"""

import json
import sys
import os

import pytest

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from internal.task.task import Task
from internal.worker.worker import process_task


# ---------------------------------------------------------------------------
# Task dataclass
# ---------------------------------------------------------------------------

def test_task_default_values():
    task = Task()
    assert task.type == ""
    assert task.payload == {}
    assert task.retries == 0


def test_task_fields():
    task = Task(type="send_email", payload={"to": "a@b.com", "subject": "Hi"}, retries=3)
    assert task.type == "send_email"
    assert task.payload["to"] == "a@b.com"
    assert task.retries == 3


# ---------------------------------------------------------------------------
# process_task — happy paths
# ---------------------------------------------------------------------------

def test_process_send_email(capsys):
    task = Task(type="send_email", payload={"to": "user@example.com", "subject": "Hello"}, retries=1)
    # send_email sleeps 2 seconds; monkeypatch sleep to skip the wait
    import time
    original_sleep = time.sleep
    time.sleep = lambda s: None

    err = process_task(task)

    time.sleep = original_sleep

    assert err is None
    captured = capsys.readouterr()
    assert "user@example.com" in captured.out
    assert "Hello" in captured.out


def test_process_resize_image(capsys):
    task = Task(type="resize_image", payload={"new_x": 800, "new_y": 600}, retries=1)
    err = process_task(task)
    assert err is None
    captured = capsys.readouterr()
    assert "800" in captured.out
    assert "600" in captured.out


def test_process_generate_pdf(capsys):
    task = Task(type="generate_pdf", payload={"doc": "report"}, retries=1)
    err = process_task(task)
    assert err is None
    captured = capsys.readouterr()
    assert "pdf" in captured.out.lower()


# ---------------------------------------------------------------------------
# process_task — error paths
# ---------------------------------------------------------------------------

def test_process_empty_type():
    task = Task(type="", payload={"key": "val"}, retries=1)
    err = process_task(task)
    assert err == "task type is empty"


def test_process_unsupported_type():
    task = Task(type="unknown_task", payload={"key": "val"}, retries=1)
    err = process_task(task)
    assert err == "unsupported task"


def test_process_empty_payload():
    task = Task(type="send_email", payload={}, retries=1)
    err = process_task(task)
    assert err == "payload is empty"


# ---------------------------------------------------------------------------
# Logger — writes correct text to logs/logs.txt
# ---------------------------------------------------------------------------

def test_log_success_writes_to_file(tmp_path, monkeypatch):
    # Redirect the log file to a temp directory
    log_file = tmp_path / "logs" / "logs.txt"
    log_file.parent.mkdir()

    # Patch open inside the logger module to write to tmp_path
    import internal.logger.logger as logger_module

    original_open = open

    def patched_open(path, mode="r", **kwargs):
        if path == "logs/logs.txt":
            return original_open(str(log_file), mode, **kwargs)
        return original_open(path, mode, **kwargs)

    monkeypatch.setattr("builtins.open", patched_open)

    task = Task(type="send_email", payload={"to": "a@b.com", "subject": "Test"}, retries=2)
    logger_module.log_success(task)

    content = log_file.read_text()
    assert "SUCCESS" in content
    assert "send_email" in content
    assert "a@b.com" in content


def test_log_failure_writes_to_file(tmp_path, monkeypatch):
    log_file = tmp_path / "logs" / "logs.txt"
    log_file.parent.mkdir()

    import internal.logger.logger as logger_module

    original_open = open

    def patched_open(path, mode="r", **kwargs):
        if path == "logs/logs.txt":
            return original_open(str(log_file), mode, **kwargs)
        return original_open(path, mode, **kwargs)

    monkeypatch.setattr("builtins.open", patched_open)

    task = Task(type="send_email", payload={"to": "a@b.com"}, retries=0)
    logger_module.log_failure(task, "something went wrong")

    content = log_file.read_text()
    assert "FAILURE" in content
    assert "send_email" in content
    assert "something went wrong" in content
