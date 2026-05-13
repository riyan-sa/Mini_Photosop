/* ─── State ──────────────────────────────────────────────── */
const state = { hasImage: false };

/* ─── Elements ───────────────────────────────────────────── */
const fileInput  = document.getElementById('file-input');
const imgBefore  = document.getElementById('img-before');
const imgAfter   = document.getElementById('img-after');
const emptyState = document.getElementById('empty-state');
const loading    = document.getElementById('loading');
const statusBar  = document.getElementById('status-bar');
const imgInfo    = document.getElementById('img-info');
const beforeWrap = document.getElementById('before-wrap');

const sliders = {
  brightness: { el: document.getElementById('s-brightness'), val: document.getElementById('v-brightness') },
  contrast:   { el: document.getElementById('s-contrast'),   val: document.getElementById('v-contrast')   },
  sharpen:    { el: document.getElementById('s-sharpen'),    val: document.getElementById('v-sharpen')    },
  blur:       { el: document.getElementById('s-blur'),       val: document.getElementById('v-blur')       },
};

/* ─── Helpers ────────────────────────────────────────────── */
function setStatus(msg, type = '') {
  statusBar.textContent = msg;
  statusBar.className = 'status-bar ' + type;
}

function showLoading(show) {
  loading.style.display = show ? 'flex' : 'none';
}

function showImage(base64, target) {
  target.style.display = 'block';
  target.src = 'data:image/jpeg;base64,' + base64;
  
}

function updateInfo(info) {
  if (!info || !info.width) return;
  imgInfo.textContent = `${info.width} × ${info.height}px · ${info.mode}`;
}

function getSliderValues() {
  return {
    brightness: sliders.brightness.el.value / 100,
    contrast:   sliders.contrast.el.value   / 100,
    sharpen:    sliders.sharpen.el.value     / 100,
    blur:       sliders.blur.el.value        / 2,
  };
}

function resetSliders() {
  sliders.brightness.el.value = 100; sliders.brightness.val.textContent = '100';
  sliders.contrast.el.value   = 100; sliders.contrast.val.textContent   = '100';
  sliders.sharpen.el.value    = 100; sliders.sharpen.val.textContent    = '100';
  sliders.blur.el.value       = 0;   sliders.blur.val.textContent       = '0';
}

function clearCanvas() {
  
  imgBefore.src = ''; imgBefore.style.display = 'none';
  
  imgAfter.src = ''; imgAfter.style.display = 'none';
  emptyState.style.display = '';
  beforeWrap.classList.add('clickable');
  state.hasImage = false;
  imgInfo.textContent = '—';
  resetSliders();
}

/* ─── Slider live update ─────────────────────────────────── */
let debounceTimer;
Object.entries(sliders).forEach(([key, s]) => {
  s.el.addEventListener('input', () => {
    s.val.textContent = s.el.value;
    if (!state.hasImage) return;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(applyEnhance, 300);
  });
});

/* ─── API Calls ──────────────────────────────────────────── */
async function uploadImage(file) {
  const form = new FormData();
  form.append('file', file);
  showLoading(true);
  setStatus('Mengupload gambar...');
  try {
    const res  = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload gagal.');
    emptyState.style.display = 'none';
    showImage(data.image, imgBefore);
    showImage(data.image, imgAfter);
    state.hasImage = true;
    updateInfo(data.info);
    resetSliders();
    setStatus(`✓ ${file.name} berhasil diupload.`, 'ok');
  } catch (e) {
    setStatus(`✕ ${e.message}`, 'error');
  } finally {
    showLoading(false);
  }
}

async function applyEnhance() {
  if (!state.hasImage) return;
  showLoading(true);
  try {
    const res  = await fetch('/api/enhance', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(getSliderValues()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    showImage(data.image, imgAfter);
    setStatus('✓ Enhancement diterapkan.', 'ok');
  } catch (e) {
    setStatus(`✕ ${e.message}`, 'error');
  } finally {
    showLoading(false);
  }
}

async function applyHisteq() {
  if (!state.hasImage) return;
  showLoading(true);
  setStatus('Menerapkan histogram equalization...');
  try {
    const res  = await fetch('/api/histeq', { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    showImage(data.image, imgAfter);
    setStatus('✓ Histogram equalization diterapkan.', 'ok');
  } catch (e) {
    setStatus(`✕ ${e.message}`, 'error');
  } finally {
    showLoading(false);
  }
}

async function resetImage() {
  if (!state.hasImage) return;
  showLoading(true);
  try {
    const res  = await fetch('/api/reset');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    showImage(data.image, imgBefore);
    showImage(data.image, imgAfter);
    resetSliders();
    setStatus('✓ Direset ke gambar awal.', 'ok');
  } catch (e) {
    setStatus(`✕ ${e.message}`, 'error');
  } finally {
    showLoading(false);
  }
}

/* ─── Event Listeners ────────────────────────────────────── */
fileInput.addEventListener('change', (e) => {
  if (e.target.files[0]) uploadImage(e.target.files[0]);
  e.target.value = '';
});

// Klik area BEFORE saat belum ada gambar → buka file dialog
beforeWrap.addEventListener('click', () => {
  if (!state.hasImage) fileInput.click();
});

// Hapus gambar
document.getElementById('btn-clear').addEventListener('click', () => {
  if (!state.hasImage) return;
  clearCanvas();
  setStatus('Gambar dihapus.');
});

document.getElementById('btn-apply').addEventListener('click', applyEnhance);
document.getElementById('btn-histeq').addEventListener('click', applyHisteq);
document.getElementById('btn-reset').addEventListener('click', resetImage);
document.getElementById('btn-reset-sliders').addEventListener('click', () => {
  resetSliders();
  if (state.hasImage) applyEnhance();
});