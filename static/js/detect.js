/* ═══════════════════════════════════════════════════════
   DETECT.JS — Plant disease detection (backend-driven)
   ─────────────────────────────────────────────────────
   POSTs image to POST /api/detect.
   All results come from the backend.
   No random local fallback — if backend fails an explicit
   error toast is shown.
═══════════════════════════════════════════════════════ */
let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  const uploadZone = document.getElementById('uploadZone');
  if (!uploadZone) return;

  uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });
});

function handleFile(e) { if (e.target.files[0]) setFile(e.target.files[0]); }

function setFile(file) {
  if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
    showToast('⚠️ Please upload a JPG or PNG image.');
    return;
  }
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('previewImg').src          = e.target.result;
    document.getElementById('uploadZone').style.display  = 'none';
    document.getElementById('previewWrap').style.display = 'block';
    document.getElementById('detectBtn').style.display   = 'flex';
  };
  reader.readAsDataURL(file);
}

function clearFile() {
  selectedFile = null;

  const uploadZone  = document.getElementById('uploadZone');
  const previewWrap = document.getElementById('previewWrap');
  const detectBtn   = document.getElementById('detectBtn');
  const fileInput   = document.getElementById('fileInput');

  // Reset file input
  fileInput.value = '';

  // Reset preview image
  document.getElementById('previewImg').src = '';

  // Restore UI cleanly — remove inline style so CSS default (block) takes over
  uploadZone.style.display  = '';
  previewWrap.style.display = 'none';
  detectBtn.style.display   = 'none';

  // Force layout reset (THIS FIXES BROKEN UI)
  uploadZone.classList.remove('drag-over');

  resetDetectPanel();
}

function resetDetectPanel() {
  document.getElementById('detectEmpty').style.display   = 'flex';
  document.getElementById('detectLoading').style.display = 'none';
  document.getElementById('detectOutput').style.display  = 'none';
}

/* ── Render detection result ── */
function renderDetectResult(data) {
  document.getElementById('detectLoading').style.display = 'none';
  document.getElementById('detectOutput').style.display  = 'block';

  const disease = data.disease || data.label || 'Unknown';
  const plant   = data.plant   || 'Unknown';
  const conf    = data.confidence;

  document.getElementById('det-disease').textContent = disease;
  document.getElementById('det-plant').textContent   = 'Plant: ' + plant;

  const badge = document.getElementById('det-conf');
  badge.textContent = conf + '% confidence';
  badge.className   = 'confidence-badge ' + (conf > 85 ? 'conf-high' : 'conf-med');

  /* Use local DISEASE_DB for rich descriptions if available */
  const db = (typeof DISEASE_DB !== 'undefined')
    ? (DISEASE_DB[data.label] || DISEASE_DB['default'])
    : null;

  if (db) {
    document.getElementById('det-diagnosis').textContent  = db.diagnosis  || '';
    document.getElementById('det-symptoms').textContent   = db.symptoms   || '';
    document.getElementById('det-treatment').textContent  = db.treatment  || '';
    document.getElementById('det-prevention').textContent = db.prevention || '';
  } else {
    document.getElementById('det-diagnosis').textContent  = disease !== 'Healthy'
      ? 'Disease detected: ' + disease
      : 'No disease detected — plant appears healthy.';
    document.getElementById('det-symptoms').textContent   = '';
    document.getElementById('det-treatment').textContent  = '';
    document.getElementById('det-prevention').textContent = '';
  }

  /* Stub-mode notice */
  const stubNotice = document.getElementById('det-stub-notice');
  if (stubNotice) {
    stubNotice.style.display = data.stub_mode ? 'block' : 'none';
    if (data.stub_mode) stubNotice.classList.add('stub-notice');
  }

  /* ── Top-5 predictions ── */
  const top5Data    = data.top5 || [];
  const top5Section = document.getElementById('det-top5-section');
  const top5List    = document.getElementById('det-top5-list');
  if (top5Section && top5List) {
    if (top5Data.length > 1) {
      top5List.innerHTML = '';
      top5Data.forEach((item, i) => {
        const lbl     = item.label || 'Unknown';
        const parts   = lbl.includes('___') ? lbl.split('___') :
                        lbl.includes('__')  ? lbl.split('__')  : [lbl, lbl];
        const plant   = parts[0].replace(/_/g, ' ').trim();
        const disease = (parts[1] || parts[0]).replace(/_/g, ' ').trim();
        const confVal = item.confidence || 0;
        const barW    = Math.min(100, confVal);
        const cls     = confVal >= 70 ? 'conf-high' : confVal >= 40 ? 'conf-med' : 'conf-low';

        const row = document.createElement('div');
        row.className = 'top5-item';
        row.innerHTML =
          `<span class="top5-rank">#${i + 1}</span>` +
          `<div class="top5-info">` +
            `<div class="top5-disease">${disease}</div>` +
            `<div class="top5-plant">${plant}</div>` +
          `</div>` +
          `<div class="top5-right">` +
            `<span class="confidence-badge ${cls} top5-badge">${confVal}%</span>` +
            `<div class="top5-bar"><div class="top5-bar-fill" style="width:${barW}%"></div></div>` +
          `</div>`;
        top5List.appendChild(row);
      });
      top5Section.style.display = 'block';
    } else {
      top5Section.style.display = 'none';
    }
  }
}

/* ── Main detection function ── */
async function runDetection() {
  if (!selectedFile) {
    showToast('⚠️ Please upload a leaf image first.');
    return;
  }

  if (!API.isLoggedIn()) {
    showToast('🔒 Please log in to use Disease Detection.');
    setTimeout(() => { window.location.href = '/login'; }, 1200);
    return;
  }

  document.getElementById('detectEmpty').style.display   = 'none';
  document.getElementById('detectLoading').style.display = 'flex';
  document.getElementById('detectOutput').style.display  = 'none';

  try {
    const data = await API.detect(selectedFile);
    renderDetectResult(data);
    const label = data.disease || data.label || 'Unknown';
    showToast('🔬 Detection complete: ' + label + ' (' + data.confidence + '%)');
  } catch (err) {
    document.getElementById('detectLoading').style.display = 'none';
    document.getElementById('detectEmpty').style.display   = 'flex';
    showToast('❌ Detection failed: ' + (err.message || 'Server error. Please try again.'));
  }
}
