import os
import sys
import json
import time
import uuid
import asyncio
import signal
import re
import psutil
import nbformat
from typing import Dict, Any, Optional, List
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
RUNS_DIR = os.path.join(DATA_DIR, "runs")
JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RUNS_DIR, exist_ok=True)

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        self.load_jobs()

    def load_jobs(self):
        if os.path.exists(JOBS_FILE):
            try:
                with open(JOBS_FILE, "r", encoding="utf-8") as f:
                    self.jobs = json.load(f)
                    # Mark any previously running jobs as interrupted if server stopped
                    for jid, job in self.jobs.items():
                        if job.get("status") == "RUNNING":
                            job["status"] = "STOPPED"
                            job["ended_at"] = datetime.now().isoformat()
            except Exception as e:
                print(f"Error loading jobs: {e}")
                self.jobs = {}
        else:
            self.jobs = {}

    def save_jobs(self):
        try:
            with open(JOBS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.jobs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving jobs: {e}")

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        return sorted(list(self.jobs.values()), key=lambda x: x.get("created_at", ""), reverse=True)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def convert_ipynb_to_py(self, ipynb_path: str, output_py_path: str):
        with open(ipynb_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)

        py_lines = [
            "# Auto-generated execution script from Notebook\n",
            "import sys, os, subprocess\n",
            "os.environ['PYTHONUNBUFFERED'] = '1'\n\n"
        ]

        for cell_idx, cell in enumerate(nb.cells):
            if cell.cell_type == "code":
                py_lines.append(f"\n# --- Notebook Cell {cell_idx + 1} ---\n")
                lines = cell.source.splitlines()
                for line in lines:
                    trimmed = line.strip()
                    # Handle shell commands like !pip install
                    if trimmed.startswith("!"):
                        cmd = trimmed[1:].strip()
                        py_lines.append(f"subprocess.run({repr(cmd)}, shell=True, check=False)\n")
                    # Handle magic commands like %matplotlib, %load_ext, etc.
                    elif trimmed.startswith("%"):
                        py_lines.append(f"# Magic skipped: {trimmed}\n")
                    else:
                        py_lines.append(line + "\n")

        with open(output_py_path, "w", encoding="utf-8") as f:
            f.writelines(py_lines)

    async def broadcast_log(self, job_id: str, line: str, parsed_metric: Optional[Dict[str, Any]] = None):
        msg = {
            "type": "log",
            "job_id": job_id,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "line": line,
            "metric": parsed_metric
        }
        if job_id in self.subscribers:
            for q in list(self.subscribers[job_id]):
                try:
                    await q.put(msg)
                except Exception:
                    pass

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q = asyncio.Queue()
        if job_id not in self.subscribers:
            self.subscribers[job_id] = []
        self.subscribers[job_id].append(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue):
        if job_id in self.subscribers and q in self.subscribers[job_id]:
            self.subscribers[job_id].remove(q)
            if not self.subscribers[job_id]:
                del self.subscribers[job_id]

    def parse_metrics_from_line(self, line: str) -> Optional[Dict[str, Any]]:
        # Detect patterns like: Epoch 1/20 | Loss: 0.3541 | Acc: 89.2%
        metric = {}
        epoch_match = re.search(r'(?:epoch|ep)[:\s]+(\d+)(?:/(\d+))?', line, re.IGNORECASE)
        loss_match = re.search(r'(?:loss|val_loss|cost)[:\s]+([0-9]+\.?[0-9]*(?:e-?[0-9]+)?)', line, re.IGNORECASE)
        acc_match = re.search(r'(?:acc|accuracy|val_acc)[:\s]+([0-9]+\.?[0-9]*%?)', line, re.IGNORECASE)

        if epoch_match:
            metric["epoch"] = int(epoch_match.group(1))
            if epoch_match.group(2):
                metric["total_epochs"] = int(epoch_match.group(2))
        if loss_match:
            try:
                metric["loss"] = float(loss_match.group(1))
            except ValueError:
                pass
        if acc_match:
            val = acc_match.group(1).replace("%", "")
            try:
                metric["accuracy"] = float(val)
            except ValueError:
                pass

        return metric if metric else None

    async def create_and_start_job(self, filename: str, original_path: str, is_notebook: bool, params: Dict[str, Any] = None) -> str:
        job_id = str(uuid.uuid4())[:8]
        run_dir = os.path.join(RUNS_DIR, job_id)
        os.makedirs(run_dir, exist_ok=True)

        exec_script = os.path.join(run_dir, "train.py")
        if is_notebook:
            self.convert_ipynb_to_py(original_path, exec_script)
        else:
            with open(original_path, "r", encoding="utf-8") as src, open(exec_script, "w", encoding="utf-8") as dst:
                dst.write(src.read())

        log_path = os.path.join(LOGS_DIR, f"{job_id}.log")

        job_info = {
            "id": job_id,
            "filename": filename,
            "type": "Notebook (.ipynb)" if is_notebook else "Python Script (.py)",
            "status": "RUNNING",
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "run_dir": run_dir,
            "log_path": log_path,
            "metrics": [],
            "exit_code": None,
            "duration_sec": 0,
            "params": params or {}
        }

        self.jobs[job_id] = job_info
        self.save_jobs()

        # Launch background runner task
        asyncio.create_task(self._run_job_process(job_id, exec_script, run_dir, log_path))
        return job_id

    async def _run_job_process(self, job_id: str, script_path: str, cwd: str, log_path: str):
        start_time = time.time()
        job = self.jobs[job_id]

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["WORKSPACE_DIR"] = cwd

        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(f"=== [TrainStudio AI] Job {job_id} Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            log_file.write(f"Target: {job['filename']} (24/7 Background Runner)\n")
            log_file.write(f"Environment: Python {sys.version.split()[0]}\n")
            log_file.write("=" * 60 + "\n\n")
            log_file.flush()

            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-u", script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=cwd,
                    env=env
                )
                self.active_processes[job_id] = proc

                # Read output stream line by line in real-time
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    log_file.write(decoded)
                    log_file.flush()

                    # Check for metrics
                    parsed_metric = self.parse_metrics_from_line(decoded)
                    if parsed_metric:
                        parsed_metric["step"] = len(job["metrics"]) + 1
                        job["metrics"].append(parsed_metric)

                    await self.broadcast_log(job_id, decoded.rstrip("\r\n"), parsed_metric)

                await proc.wait()
                exit_code = proc.returncode
                job["exit_code"] = exit_code
                job["status"] = "COMPLETED" if exit_code == 0 else "FAILED"

            except asyncio.CancelledError:
                job["status"] = "STOPPED"
                log_file.write("\n\n[TrainStudio AI] Job cancelled by user.\n")
            except Exception as e:
                job["status"] = "FAILED"
                log_file.write(f"\n\n[TrainStudio AI] Error executing job: {e}\n")
            finally:
                duration = round(time.time() - start_time, 2)
                job["duration_sec"] = duration
                job["ended_at"] = datetime.now().isoformat()
                log_file.write(f"\n=== Job {job_id} finished with status {job['status']} in {duration}s ===\n")
                log_file.flush()

                if job_id in self.active_processes:
                    del self.active_processes[job_id]

                self.save_jobs()
                await self.broadcast_log(job_id, f"=== Job completed with status: {job['status']} (Duration: {duration}s) ===")

    async def stop_job(self, job_id: str) -> bool:
        if job_id in self.active_processes:
            proc = self.active_processes[job_id]
            try:
                proc.send_signal(signal.SIGTERM)
                await asyncio.sleep(1)
                if proc.returncode is None:
                    proc.kill()
            except Exception as e:
                print(f"Error stopping process: {e}")
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "STOPPED"
                self.jobs[job_id]["ended_at"] = datetime.now().isoformat()
                self.save_jobs()
            return True
        return False

    def get_job_logs(self, job_id: str, max_lines: int = 1000) -> str:
        log_path = os.path.join(LOGS_DIR, f"{job_id}.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    return "".join(lines[-max_lines:])
            except Exception as e:
                return f"Error reading log: {e}"
        return "No logs found for this job."

    def get_job_artifacts(self, job_id: str) -> List[Dict[str, Any]]:
        run_dir = os.path.join(RUNS_DIR, job_id)
        artifacts = []
        if os.path.exists(run_dir):
            for root, _, files in os.walk(run_dir):
                for file in files:
                    if file == "train.py":
                        continue
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, run_dir)
                    size = os.path.getsize(full_p)
                    artifacts.append({
                        "name": rel_p,
                        "size_bytes": size,
                        "size_formatted": self.format_size(size),
                        "modified": datetime.fromtimestamp(os.path.getmtime(full_p)).strftime("%Y-%m-%d %H:%M:%S")
                    })
        return artifacts

    @staticmethod
    def format_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_system_stats(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(BASE_DIR)

        active_jobs_count = len([j for j in self.jobs.values() if j.get("status") == "RUNNING"])

        # Check for Apple Silicon GPU (MPS) or NVIDIA
        gpu_info = "Apple Silicon MPS / CPU"
        try:
            import torch
            if torch.backends.mps.is_available():
                gpu_info = "Apple Silicon (MPS Hardware Acceleration Active)"
            elif torch.cuda.is_available():
                gpu_info = f"NVIDIA {torch.cuda.get_device_name(0)}"
        except ImportError:
            pass

        return {
            "cpu_percent": cpu_percent,
            "ram_used_gb": round((mem.total - mem.available) / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "ram_percent": mem.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "disk_percent": disk.percent,
            "active_jobs": active_jobs_count,
            "total_jobs": len(self.jobs),
            "gpu_info": gpu_info
        }
