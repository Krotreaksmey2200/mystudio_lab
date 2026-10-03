import os
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from job_manager import JobManager, UPLOADS_DIR, RUNS_DIR

app = FastAPI(title="TrainStudio AI - 24/7 Model Training Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_mgr = JobManager()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/system")
async def get_system_stats():
    return job_mgr.get_system_stats()

@app.get("/api/jobs")
async def get_jobs():
    return job_mgr.get_all_jobs()

@app.get("/api/jobs/{job_id}")
async def get_job_detail(job_id: str):
    job = job_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    logs = job_mgr.get_job_logs(job_id)
    return {"job_id": job_id, "logs": logs}

@app.post("/api/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    success = await job_mgr.stop_job(job_id)
    return {"job_id": job_id, "stopped": success}

@app.get("/api/jobs/{job_id}/artifacts")
async def get_artifacts(job_id: str):
    artifacts = job_mgr.get_job_artifacts(job_id)
    return {"job_id": job_id, "artifacts": artifacts}

@app.get("/api/jobs/{job_id}/download/{filename:path}")
async def download_artifact(job_id: str, filename: str):
    job = job_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    file_path = os.path.join(job["run_dir"], filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Artifact file not found")
    return FileResponse(file_path, filename=os.path.basename(filename))

@app.post("/api/jobs/upload")
async def upload_and_run(file: UploadFile = File(...)):
    filename = file.filename or "unknown_script.py"
    is_ipynb = filename.endswith(".ipynb")
    is_py = filename.endswith(".py")

    if not (is_ipynb or is_py):
        raise HTTPException(status_code=400, detail="Only .ipynb (Jupyter Notebook) and .py files are supported")

    dest_path = os.path.join(UPLOADS_DIR, f"{int(asyncio.get_event_loop().time())}_{filename}")
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    job_id = await job_mgr.create_and_start_job(filename, dest_path, is_notebook=is_ipynb)
    return {"success": True, "job_id": job_id, "message": f"Job {job_id} launched successfully in 24/7 background mode!"}

@app.post("/api/jobs/sample")
async def run_sample_ai_training():
    sample_file = os.path.join(BASE_DIR, "sample_training.py")
    if not os.path.exists(sample_file):
        raise HTTPException(status_code=404, detail="Sample script not found")

    job_id = await job_mgr.create_and_start_job("sample_deep_learning_model.py", sample_file, is_notebook=False)
    return {"success": True, "job_id": job_id, "message": "Demo neural network training started!"}

@app.websocket("/ws/logs/{job_id}")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await websocket.accept()
    queue = job_mgr.subscribe(job_id)

    # First send initial existing log history
    initial_logs = job_mgr.get_job_logs(job_id, max_lines=200)
    job = job_mgr.get_job(job_id)
    await websocket.send_json({
        "type": "init",
        "job_id": job_id,
        "logs": initial_logs,
        "job": job
    })

    try:
        while True:
            # Wait for new log lines from background process
            msg = await queue.get()
            await websocket.send_json(msg)
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        job_mgr.unsubscribe(job_id, queue)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
