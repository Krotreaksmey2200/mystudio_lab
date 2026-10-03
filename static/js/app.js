// TrainStudio AI - Frontend Application Logic

let activeJobId = null;
let activeWebSocket = null;
let selectedFile = null;
let lossChart = null;
let accChart = null;

// Initialize charts using Chart.js or canvas fallback
function initCharts() {
  const lossCtx = document.getElementById('lossChart')?.getContext('2d');
  const accCtx = document.getElementById('accChart')?.getContext('2d');

  if (typeof Chart !== 'undefined' && lossCtx && accCtx) {
    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        }
      },
      plugins: {
        legend: { display: false }
      }
    };

    lossChart = new Chart(lossCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Loss',
          data: [],
          borderColor: '#fb923c',
          backgroundColor: 'rgba(251, 146, 60, 0.12)',
          borderWidth: 2,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#fb923c'
        }]
      },
      options: commonOptions
    });

    accChart = new Chart(accCtx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Accuracy %',
          data: [],
          borderColor: '#4ade80',
          backgroundColor: 'rgba(74, 222, 128, 0.12)',
          borderWidth: 2,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#4ade80'
        }]
      },
      options: commonOptions
    });
  }
}

function resetCharts() {
  if (lossChart) {
    lossChart.data.labels = [];
    lossChart.data.datasets[0].data = [];
    lossChart.update();
  }
  if (accChart) {
    accChart.data.labels = [];
    accChart.data.datasets[0].data = [];
    accChart.update();
  }
  document.getElementById('val-current-loss').textContent = '--';
  document.getElementById('val-current-acc').textContent = '--';
  document.getElementById('chart-metrics-info').textContent = 'Waiting for epoch data...';
}

function addMetricToChart(metric) {
  if (!metric) return;
  const label = metric.epoch ? `Ep ${metric.epoch}` : `Step ${metric.step || ''}`;

  if (metric.loss !== undefined && lossChart) {
    lossChart.data.labels.push(label);
    lossChart.data.datasets[0].data.push(metric.loss);
    lossChart.update();
    document.getElementById('val-current-loss').textContent = metric.loss.toFixed(4);
  }

  if (metric.accuracy !== undefined && accChart) {
    accChart.data.labels.push(label);
    accChart.data.datasets[0].data.push(metric.accuracy);
    accChart.update();
    document.getElementById('val-current-acc').textContent = `${metric.accuracy.toFixed(2)}%`;
  }

  if (metric.epoch) {
    const total = metric.total_epochs ? `/${metric.total_epochs}` : '';
    document.getElementById('chart-metrics-info').textContent = `Tracking Epoch ${metric.epoch}${total}`;
  }
}

// System Stats Poller
async function fetchSystemStats() {
  try {
    const res = await fetch('/api/system');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('hdr-cpu').textContent = `${data.cpu_percent}%`;
    document.getElementById('hdr-ram').textContent = `${data.ram_used_gb} / ${data.ram_total_gb} GB`;
    document.getElementById('hdr-gpu').textContent = data.gpu_info.split('(')[0].trim();

    document.getElementById('card-active-jobs').textContent = data.active_jobs;
    document.getElementById('card-cpu-val').textContent = data.cpu_percent;
    document.getElementById('card-ram-val').textContent = data.ram_percent;
    document.getElementById('card-ram-sub').textContent = `${data.ram_used_gb} GB of ${data.ram_total_gb} GB used`;
    document.getElementById('card-disk-val').textContent = data.disk_free_gb;

    document.getElementById('prog-jobs').style.width = `${Math.min(100, data.active_jobs * 50)}%`;
    document.getElementById('prog-cpu').style.width = `${data.cpu_percent}%`;
    document.getElementById('prog-ram').style.width = `${data.ram_percent}%`;
  } catch (err) {
    console.error('Failed to fetch system stats:', err);
  }
}

// Jobs & History
async function fetchJobs() {
  try {
    const res = await fetch('/api/jobs');
    if (!res.ok) return;
    const jobs = await res.json();

    renderJobHistory(jobs);

    // If no active job selected, or currently selected job finished and another is running, pick the first
    if (!activeJobId && jobs.length > 0) {
      selectJob(jobs[0].id);
    }
  } catch (err) {
    console.error('Failed to fetch jobs:', err);
  }
}

function renderJobHistory(jobs) {
  const container = document.getElementById('job-history-list');
  if (!jobs || jobs.length === 0) {
    container.innerHTML = '<div class="empty-placeholder">No jobs recorded yet</div>';
    return;
  }

  container.innerHTML = jobs.map(j => {
    let badgeClass = 'badge-stopped';
    if (j.status === 'RUNNING') badgeClass = 'badge-running';
    else if (j.status === 'COMPLETED') badgeClass = 'badge-completed';
    else if (j.status === 'FAILED') badgeClass = 'badge-failed';

    const isSelected = j.id === activeJobId;
    const borderStyle = isSelected ? 'border-color: var(--accent-cyan); background: rgba(0,242,254,0.06);' : '';

    return `
      <div class="job-item" style="${borderStyle}" onclick="selectJob('${j.id}')">
        <div>
          <div class="job-info-name">
            <span>${j.type.includes('Notebook') ? '📓' : '🐍'}</span>
            <span>${j.filename}</span>
            <span class="job-badge ${badgeClass}">${j.status}</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 4px;">
            ID: #${j.id} • Started: ${new Date(j.created_at).toLocaleTimeString()} • Duration: ${j.duration_sec ? j.duration_sec + 's' : 'In progress'}
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); selectJob('${j.id}')">
          View Live
        </button>
      </div>
    `;
  }).join('');
}

// Select and Connect to a Job
function selectJob(jobId) {
  if (activeJobId === jobId && activeWebSocket) return;
  activeJobId = jobId;

  // Update history items highlight
  fetchJobs();

  // Close previous WebSocket
  if (activeWebSocket) {
    activeWebSocket.close();
    activeWebSocket = null;
  }

  resetCharts();
  connectWebSocket(jobId);
  fetchArtifacts(jobId);
}

// WebSocket Connection
function connectWebSocket(jobId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/logs/${jobId}`;
  
  const terminal = document.getElementById('terminal-body');
  const titleEl = document.getElementById('terminal-job-title');
  const statusEl = document.getElementById('terminal-job-status');
  const stopBtn = document.getElementById('btn-stop-job');

  terminal.innerHTML = `[TrainStudio AI] Connecting live WebSocket stream for Job #${jobId}...\n`;

  activeWebSocket = new WebSocket(wsUrl);

  activeWebSocket.onopen = () => {
    console.log(`WebSocket connected for job ${jobId}`);
  };

  activeWebSocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'init') {
        terminal.textContent = data.logs || '';
        if (data.job) {
          titleEl.textContent = `Console: ${data.job.filename} (#${data.job.id})`;
          updateStatusBadge(data.job.status);
          if (data.job.metrics && data.job.metrics.length > 0) {
            data.job.metrics.forEach(m => addMetricToChart(m));
          }
        }
      } else if (data.type === 'log') {
        appendLogLine(data.line);
        if (data.metric) {
          addMetricToChart(data.metric);
        }
      }

      // Check if job completed
      if (data.line && data.line.includes('=== Job completed with status:')) {
        fetchJobs();
        fetchArtifacts(jobId);
      }

      // Auto-scroll
      if (document.getElementById('chk-autoscroll').checked) {
        terminal.scrollTop = terminal.scrollHeight;
      }
    } catch (e) {
      console.error('Error handling WebSocket message:', e);
    }
  };

  activeWebSocket.onclose = () => {
    console.log('WebSocket stream closed.');
  };
}

function appendLogLine(line) {
  const terminal = document.getElementById('terminal-body');
  terminal.textContent += line + '\n';
}

function updateStatusBadge(status) {
  const statusEl = document.getElementById('terminal-job-status');
  const stopBtn = document.getElementById('btn-stop-job');

  statusEl.className = 'job-badge';
  if (status === 'RUNNING') {
    statusEl.classList.add('badge-running');
    statusEl.textContent = 'RUNNING (24/7)';
    stopBtn.style.display = 'inline-flex';
  } else if (status === 'COMPLETED') {
    statusEl.classList.add('badge-completed');
    statusEl.textContent = 'COMPLETED';
    stopBtn.style.display = 'none';
  } else if (status === 'FAILED') {
    statusEl.classList.add('badge-failed');
    statusEl.textContent = 'FAILED';
    stopBtn.style.display = 'none';
  } else {
    statusEl.classList.add('badge-stopped');
    statusEl.textContent = 'STOPPED';
    stopBtn.style.display = 'none';
  }
}

// Artifacts & Checkpoints
async function fetchArtifacts(jobId) {
  if (!jobId) return;
  const container = document.getElementById('artifacts-list');
  try {
    const res = await fetch(`/api/jobs/${jobId}/artifacts`);
    if (!res.ok) return;
    const data = await res.json();
    const artifacts = data.artifacts || [];

    if (artifacts.length === 0) {
      container.innerHTML = '<div class="empty-placeholder">No checkpoints generated yet</div>';
      return;
    }

    container.innerHTML = artifacts.map(art => `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; margin-bottom: 6px;">
        <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px;">
          <div style="font-size: 0.82rem; font-weight: 600; color: #fff;">💾 ${art.name}</div>
          <div style="font-size: 0.72rem; color: var(--text-dim);">${art.size_formatted} • ${art.modified}</div>
        </div>
        <a href="/api/jobs/${jobId}/download/${encodeURIComponent(art.name)}" download class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 0.75rem;">
          ⬇️ Download
        </a>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to fetch artifacts:', err);
  }
}

// Setup Event Listeners
function setupEvents() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const startUploadBtn = document.getElementById('btn-start-upload');
  const runSampleBtn = document.getElementById('btn-run-sample');
  const stopJobBtn = document.getElementById('btn-stop-job');
  const clearTerminalBtn = document.getElementById('btn-clear-terminal');
  const downloadLogBtn = document.getElementById('btn-download-log');
  const refreshStatsBtn = document.getElementById('btn-refresh-stats');
  const refreshHistoryBtn = document.getElementById('btn-refresh-history');
  const refreshArtifactsBtn = document.getElementById('btn-refresh-artifacts');

  // Drag and Drop
  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.name.endsWith('.ipynb') && !file.name.endsWith('.py')) {
      alert('Please upload a Jupyter Notebook (.ipynb) or Python script (.py)');
      return;
    }
    selectedFile = file;
    document.getElementById('selected-filename').textContent = file.name;
    document.getElementById('selected-filesize').textContent = `${(file.size / 1024).toFixed(1)} KB`;
    document.getElementById('selected-file-panel').style.display = 'block';
  }

  // Upload and Start
  startUploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);

    startUploadBtn.disabled = true;
    startUploadBtn.textContent = 'Launching Background Daemon...';

    try {
      const res = await fetch('/api/jobs/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        selectedFile = null;
        document.getElementById('selected-file-panel').style.display = 'none';
        fileInput.value = '';
        await fetchJobs();
        selectJob(data.job_id);
      } else {
        alert(data.detail || 'Failed to start job');
      }
    } catch (err) {
      alert('Error uploading file: ' + err.message);
    } finally {
      startUploadBtn.disabled = false;
      startUploadBtn.textContent = '▶️ Start 24/7 Execution';
    }
  });

  // Run Sample AI Demo
  runSampleBtn.addEventListener('click', async () => {
    runSampleBtn.disabled = true;
    runSampleBtn.textContent = 'Starting Demo Model...';
    try {
      const res = await fetch('/api/jobs/sample', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        await fetchJobs();
        selectJob(data.job_id);
      }
    } catch (err) {
      alert('Error launching sample: ' + err.message);
    } finally {
      runSampleBtn.disabled = false;
      runSampleBtn.textContent = '🧪 Run Sample Neural Network (Demo)';
    }
  });

  // Stop Active Job
  stopJobBtn.addEventListener('click', async () => {
    if (!activeJobId) return;
    if (!confirm('Are you sure you want to stop this 24/7 training job?')) return;
    try {
      await fetch(`/api/jobs/${activeJobId}/stop`, { method: 'POST' });
      updateStatusBadge('STOPPED');
      fetchJobs();
    } catch (err) {
      console.error('Failed to stop job:', err);
    }
  });

  // Clear Terminal
  clearTerminalBtn.addEventListener('click', () => {
    document.getElementById('terminal-body').textContent = '';
  });

  // Download Log
  downloadLogBtn.addEventListener('click', () => {
    if (!activeJobId) return;
    window.open(`/api/jobs/${activeJobId}/logs`, '_blank');
  });

  refreshStatsBtn.addEventListener('click', fetchSystemStats);
  refreshHistoryBtn.addEventListener('click', fetchJobs);
  refreshArtifactsBtn.addEventListener('click', () => fetchArtifacts(activeJobId));
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
  initCharts();
  setupEvents();
  fetchSystemStats();
  fetchJobs();

  // Poll system stats every 3 seconds
  setInterval(fetchSystemStats, 3000);
  // Periodic artifact sync
  setInterval(() => {
    if (activeJobId) fetchArtifacts(activeJobId);
  }, 4000);
});
