# ⚡ TrainStudio AI - 24/7 Model Training Hub

TrainStudio AI គឺជា Full-Stack Web Platform សម្រាប់ Upload ហ្វាល់ **Jupyter Notebook (`.ipynb`)** ឬ **Python Script (`.py`)** ដើម្បី Train AI/Deep Learning Models ក្នុងកម្រិត **24 ម៉ោងជាប់រហូត (Background Daemon)** ដោយមិនខ្លាចដាច់ Connection ឬ Timeout ឡើយ។

---

## 🌟 លក្ខណៈពិសេសចម្បង (Key Features)

1. **ដំណើរការ 24 ម៉ោងជាប់រហូត (24/7 Daemon Runner):**
   - រាល់ Task ដែលអ្នក Upload នឹងដំណើរការក្នុង Background Daemon ដាច់ដោយឡែក។
   - អ្នកអាច**បិទ Browser ឬបិទ Tab ចោល**បានដោយសុវត្ថិភាព ការ Train នឹងនៅតែបន្តដំណើរការរហូតដល់ចប់។
2. **គាំទ្រទាំង `.ipynb` និង `.py`:**
   - ប្រព័ន្ធនឹងបំប្លែងកូដពី Jupyter Notebook Code Cells ទៅជា Executable Process ដោយស្វ័យប្រវត្តិ។
3. **Live Terminal & WebSocket Streaming:**
   - បង្ហាញ Output, Epochs, Loss, និង Accuracy ក្នុង Real-time តាមរយៈ WebSocket។
4. **Live Training Charts:**
   - គូរក្រាហ្វិក Loss និង Accuracy ដោយស្វ័យប្រវត្តិនៅពេល Notebook បញ្ចេញ Log។
5. **Saved Checkpoints & Artifacts Downloader:**
   - Checkpoints ឬ Model Weights (`.pt`, `.pth`, `.bin`) នឹងបង្ហាញលើផ្ទាំង Dashboard សម្រាប់ Download បានភ្លាមៗដោយចុច 1-Click។
6. **Real-time Hardware & Resource Monitoring:**
   - បង្ហាញ CPU %, RAM %, Disk Space, និង Apple Silicon MPS (GPU Acceleration)។

---

## 🚀 របៀបបើកដំណើរការ (How to Run)

### វិធីទី ១៖ ចុចបើកតាម Script
បើក Terminal ក្នុង Folder នេះ រួចវាយ៖
```bash
./run_studio.sh
```

### វិធីទី ២៖ ប្រើ Python ដោយផ្ទាល់
```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

បន្ទាប់មកបើក Browser (Chrome, Safari, Edge) របស់អ្នកចូលទៅកាន់៖
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 រចនាសម្ព័ន្ធគម្រោង (Project Structure)

- `server.py`: FastAPI Web Server, REST API, WebSocket Endpoints
- `job_manager.py`: Background Process Daemon, Subprocess Runner, Log Parser, 24/7 Task Persistence
- `static/index.html`: Dashboard UI (Dark Mode Glassmorphism)
- `static/css/style.css`: Modern UI Styling
- `static/js/app.js`: Real-time WebSocket Log Streaming & Dynamic Charts
- `sample_notebook.ipynb`: ហ្វាល់ Notebook គំរូសម្រាប់សាកល្បង Upload
- `sample_training.py`: Script គំរូសម្រាប់សាកល្បង Train Neural Network
- `data/runs/`: កន្លែងរក្សាទុក Model Output, Checkpoints និង Weights
- `data/logs/`: កន្លែងរក្សាទុក Log រាល់ការ Train ទាំងអស់
