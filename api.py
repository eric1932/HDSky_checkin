import os

from fastapi import FastAPI
from fastapi import BackgroundTasks
from main import sign_in
from datetime import datetime

LOG_FILE_NAME = "last_result.log"

app = FastAPI()

log_file_path = os.path.join(".", LOG_FILE_NAME)
if not os.path.exists(log_file_path):
    open(log_file_path, 'w').close()


def background_sign_in():
    result = sign_in()
    with open(log_file_path, 'w') as f:
        f.write(result)


@app.get("/")
def root():
    return "Hello World!"


@app.get("/hdsky/status")
def hdsky_status():
    with open(log_file_path) as f:
        result = f.readline()
    j = {
        "none": 0 if result else 1,
        "signed": 1 if result == "今日已签到" else 0,
        "raw_text": result
    }
    return j


@app.get("/hdsky/sign_in", status_code=200)
def hdsky_sign_in(background_tasks: BackgroundTasks):
    background_tasks.add_task(background_sign_in)
    return f"Task initiated at {datetime.now().strftime('%H:%M:%S')}"
