/* ══════════════════════════════════════════════════════════
   Mini Photoshop — app.js (v11 - Ultimate Realtime Sync)
   ══════════════════════════════════════════════════════════ */

const S = {
  hasImage: false, imgW: 0, imgH: 0,
  geo: { flip_h: false, flip_v: false, crop: null, scale: 1.0, rotate: 0.0, tx: 0, ty: 0 },
  enh: { brightness: 1.0, contrast: 1.0, sharpen: 1.0, blur: 0.0 },
  cropMode: false, resizeMode: false, dragMode: false,
  activeSegFilter: 'threshold'
};

const $ = id => document.getElementById(id);
const fileInput    = $('file-input');
const imgBefore    = $('img-before');
const imgAfter     = $('img-after');
const emptyState   = $('empty-state');
const loading      = $('loading');
const statusBar    = $('status-bar');
const imgInfo      = $('img-info');
const beforeWrap   = $('before-wrap');
const afterWrap    = $('after-wrap');
const cropOverlay  = $('crop-overlay');
const cropBox      = $('crop-box');
const cropActions  = $('crop-actions');
const resizeOverlay= $('resize-overlay');

const ENH_SLIDERS = {
  brightness: { el: $('s-brightness'), val: $('v-brightness'), default: 100 },
  contrast:   { el: $('s-contrast'),   val: $('v-contrast'),   default: 100 },
  sharpen:    { el: $('s-sharpen'),    val: $('v-sharpen'),    default: 100 },
  blur:       { el: $('s-blur'),       val: $('v-blur'),       default: 0   },
};

const setStatus = (msg, type='') => { if(statusBar) { statusBar.textContent = msg; statusBar.className = 'status-bar ' + type; } };
const showLoading = show => { if(loading) loading.style.display = show ? 'flex' : 'none'; };

function resetEnhSliders() {
  Object.entries(ENH_SLIDERS).forEach(([k, s]) => {
    if (s.el) {
      s.el.value = s.default;
      if (s.val) s.val.textContent = s.default;
    }
  });
  S.enh = { brightness: 1.0, contrast: 1.0, sharpen: 1.0, blur: 0.0 };
}

function resetGeoUI() {
  S.geo = { flip_h: false, flip_v: false, crop: null, scale: 1.0, rotate: 0.0, tx: 0, ty: 0 };
  if ($('s-rotate')) { $('s-rotate').value = 0; $('v-rotate').textContent = '0°'; }
  if ($('s-scale')) { 
    $('s-scale').value = 100; 
    $('v-scale').textContent = '100%'; 
    if ($('n-scale')) $('n-scale').value = 100;
  }
  if ($('n-tx')) $('n-tx').value = 0;
  if ($('n-ty')) $('n-ty').value = 0;
  if (cropOverlay) cropOverlay.hidden = true;
  if (cropActions) cropActions.hidden = true;
  if (resizeOverlay) resizeOverlay.hidden = true;
  S.cropMode = false;
  S.resizeMode = false;
  S.dragMode = false;
}

function showImage(b64, target) {
  if(!target) return;
  target.src = 'data:image/jpeg;base64,' + b64;
  target.style.display = 'block'; // 👈 Mengunci agar gambar AFTER pasti tampil ke layar monitor
  target.style.transform = '';   
  
  // Amankan pemanggilan histogram realtime agar tidak membuat hang rendering utama
  if ($('hist-modal') && !$('hist-modal').hidden) {
      triggerRealtimeHistogram();
  }
}

function updateInfo(info) {
  if (!info?.width || !imgInfo) return;
  S.imgW = info.width; S.imgH = info.height;
  imgInfo.textContent = `${info.width} × ${info.height}px · ${info.mode}`;
  if($('n-width')) $('n-width').value = info.width;
  if($('n-height')) $('n-height').value = info.height;
}

function getEnhValues() {
  return {
    brightness: +ENH_SLIDERS.brightness.el.value / 100,
    contrast:   +ENH_SLIDERS.contrast.el.value   / 100,
    sharpen:    +ENH_SLIDERS.sharpen.el.value     / 100,
    blur:       +ENH_SLIDERS.blur.el.value        / 2,
  };
}

function syncStateAfterUndoRedo(data) {
  if (data.enh_state) {
    const e = data.enh_state;
    if(ENH_SLIDERS.brightness.el) {
      ENH_SLIDERS.brightness.el.value = Math.round(e.brightness * 100); ENH_SLIDERS.brightness.val.textContent = Math.round(e.brightness * 100);
      ENH_SLIDERS.contrast.el.value   = Math.round(e.contrast * 100);   ENH_SLIDERS.contrast.val.textContent   = Math.round(e.contrast * 100);
      ENH_SLIDERS.sharpen.el.value    = Math.round(e.sharpen * 100);    ENH_SLIDERS.sharpen.val.textContent    = Math.round(e.sharpen * 100);
      ENH_SLIDERS.blur.el.value       = Math.round(e.blur * 2);         ENH_SLIDERS.blur.val.textContent       = Math.round(e.blur * 2);
    }
    S.enh = {...e};
  }
  if (data.geo_state) {
    const g = data.geo_state; S.geo = {...S.geo, ...g};
    if($('s-rotate')) { 
      $('s-rotate').value = g.rotate; 
      if($('n-rotate')) $('n-rotate').value = g.rotate;
    }
    if($('s-scale')) { 
      $('s-scale').value  = Math.round(g.scale * 100); 
      $('v-scale').textContent = Math.round(g.scale * 100) + '%'; 
      if($('n-scale')) $('n-scale').value = Math.round(g.scale * 100); 
    }
    if($('n-tx')) { $('n-tx').value = g.tx; $('n-ty').value = g.ty; }
  }
}

/* ─── API BASE ───────────────────────────────────────────── */
async function api(endpoint, body=null, method='POST') {
  showLoading(true);
  try {
    const opts = { method };
    if (body) { opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(body); }
    const res  = await fetch('/api/' + endpoint, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error');
    if(data.image) showImage(data.image, imgAfter);
    if(data.info) updateInfo(data.info);
    if(data.geo_state || data.enh_state) syncStateAfterUndoRedo(data);
    setStatus('✓ ' + data.message, 'ok');
    return data;
  } catch(e) { setStatus('✕ ' + e.message, 'error'); return null; } finally { showLoading(false); }
}

function commitGeo() { return api('geo_commit', { ...S.geo, crop: S.geo.crop ? [...S.geo.crop] : null }); }
async function pushHistory() { try { await fetch('/api/push_history', {method:'POST'}); } catch(e) {} }

/* ─── DROPDOWN MODAL TRIGGERS ────────────────────────────── */
$('btn-open-transform')?.addEventListener('click', () => { if (!S.hasImage) return; $('transform-modal').hidden = false; });
$('btn-open-seg')?.addEventListener('click', () => { if (!S.hasImage) return; $('segmentation-modal').hidden = false; });
$('btn-open-restoration')?.addEventListener('click', () => { if (!S.hasImage) return; $('restoration-modal').hidden = false; });

$('transform-close').onclick = () => { $('transform-modal').hidden = true; };
$('segmentation-close').onclick = async () => { $('segmentation-modal').hidden = true; await api('restore/revert', null, 'POST'); };
$('restoration-close').onclick = async () => { $('restoration-modal').hidden = true; await api('restore/revert', null, 'POST'); };

/* ─── SHORTCUTS & UNDO / REDO ────────────────────────────── */
async function performUndo() { if (!S.hasImage) return; const data = await api('undo'); if (data) syncStateAfterUndoRedo(data); }
async function performRedo() { if (!S.hasImage) return; const data = await api('redo'); if (data) syncStateAfterUndoRedo(data); }

document.addEventListener('keydown', (e) => {
  const key = e.key.toLowerCase();
  if (e.ctrlKey && e.shiftKey && key === 'z') { e.preventDefault(); performRedo(); } 
  else if (e.ctrlKey && key === 'z') { e.preventDefault(); performUndo(); }
  else if (e.ctrlKey && key === 'y') { e.preventDefault(); performRedo(); }
});
if($('btn-undo')) $('btn-undo').onclick = (e) => { e.preventDefault(); performUndo(); };
if($('btn-redo')) $('btn-redo').onclick = (e) => { e.preventDefault(); performRedo(); };

/* ─── UPLOAD / DYNAMICS ──────────────────────────────────── */
if(fileInput) fileInput.onchange = e => { if(e.target.files[0]) uploadImage(e.target.files[0]); e.target.value=''; };
if(beforeWrap) beforeWrap.onclick = ()=>{ if(!S.hasImage && fileInput) fileInput.click(); };
if($('btn-clear')) $('btn-clear').onclick = ()=>{ if(S.hasImage){ clearCanvas(); setStatus('Workspace dibersihkan.', 'ok'); } };

async function uploadImage(file) {
  const form = new FormData(); 
  form.append('file', file); 
  showLoading(true);
  try {
    const res  = await fetch('/api/upload', { method:'POST', body:form }); 
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    
    if(emptyState) emptyState.style.display = 'none';
    
    // Tampilkan paksa elemen gambarnya di layar monitor
    if(imgBefore) { imgBefore.src = 'data:image/jpeg;base64,' + data.image; imgBefore.style.display = 'block'; }
    if(imgAfter)  { imgAfter.src  = 'data:image/jpeg;base64,' + data.image; imgAfter.style.display  = 'block'; }
    
    S.hasImage = true; 
    updateInfo(data.info); 
    resetEnhSliders(); 
    resetGeoUI(); 
    setStatus(`✓ ${file.name} diupload.`, 'ok');
    
    // Update histogram HANYA jika panel melayangnya sedang aktif terbuka
    if ($('hist-modal') && !$('hist-modal').hidden) {
        triggerRealtimeHistogram();
    }
  } catch(e) { 
    setStatus('✕ ' + e.message, 'error'); 
  } finally { 
    showLoading(false); 
  }
}

async function triggerRealtimeHistogram() {
  // Cek ketat, jika gambar belum di-load atau panel modal sedang ditutup, langsung batalkan request
  if (!S.hasImage || !$('hist-modal') || $('hist-modal').hidden) return;
  try {
    const res = await fetch('/api/histogram'); 
    const data = await res.json();
    if (res.ok) { 
        histData = data; 
        drawHistogram(histChannel); 
    }
  } catch(e) {
    console.warn("Histogram belum siap menerima state gambar baru.");
  }
}

if($('btn-reset')) $('btn-reset').onclick = async ()=>{
  if(!S.hasImage) return; await pushHistory();
  const data = await api('reset', null, 'GET'); if(data){ showImage(data.image, imgBefore); resetGeoUI(); }
};

// Pasang event klik rotasi, scale, flip, crop, & resize
if($('btn-flip-h')) $('btn-flip-h').onclick = ()=>{ S.geo.flip_h=!S.geo.flip_h; if(S.hasImage) pushHistory().then(()=>commitGeo()); };
if($('btn-flip-v')) $('btn-flip-v').onclick = ()=>{ S.geo.flip_v=!S.geo.flip_v; if(S.hasImage) pushHistory().then(()=>commitGeo()); };
if($('btn-resize')) $('btn-resize').onclick = async ()=>{
  const w=parseInt($('n-width').value), h=parseInt($('n-height').value);
  if(!w||!h){ setStatus('Isi width dan height.','error'); return; }
  await pushHistory(); api('resize',{width:w,height:h});
};

/* ─── ROTATE LOGIC ─── */
let rotateTimer;
$('s-rotate')?.addEventListener('input', (e) => {
  const val = parseInt(e.target.value);
  if ($('n-rotate')) $('n-rotate').value = val;
  S.geo.rotate = val;
  clearTimeout(rotateTimer);
  rotateTimer = setTimeout(() => {
    commitGeo();
  }, 100);
});
$('n-rotate')?.addEventListener('input', (e) => {
  let val = parseInt(e.target.value);
  if (isNaN(val)) return;
  val = Math.max(0, Math.min(val, 360));
  if ($('s-rotate')) $('s-rotate').value = val;
  S.geo.rotate = val;
  clearTimeout(rotateTimer);
  rotateTimer = setTimeout(() => {
    commitGeo();
  }, 100);
});

const applyQuickRotation = async (degChange) => {
  if (!S.hasImage) return;
  S.geo.rotate = (S.geo.rotate + degChange + 360) % 360;
  if ($('s-rotate')) $('s-rotate').value = S.geo.rotate;
  if ($('n-rotate')) $('n-rotate').value = S.geo.rotate;
  await pushHistory();
  commitGeo();
};

if ($('btn-rot-90-ccw')) $('btn-rot-90-ccw').onclick = () => applyQuickRotation(-90);
if ($('btn-rot-90-cw')) $('btn-rot-90-cw').onclick = () => applyQuickRotation(90);
if ($('btn-rot-180')) $('btn-rot-180').onclick = () => applyQuickRotation(180);

if ($('btn-rotate-reset')) $('btn-rotate-reset').onclick = async () => {
  if (!S.hasImage) return;
  S.geo.rotate = 0;
  if ($('s-rotate')) $('s-rotate').value = 0;
  if ($('n-rotate')) $('n-rotate').value = 0;
  await pushHistory();
  commitGeo();
};

/* ─── SCALE LOGIC ─── */
let scaleTimer;
$('s-scale')?.addEventListener('input', (e) => {
  const val = parseInt(e.target.value);
  $('v-scale').textContent = val + '%';
  if ($('n-scale')) $('n-scale').value = val;
  S.geo.scale = Math.max(1, val) / 100;
  clearTimeout(scaleTimer);
  scaleTimer = setTimeout(() => {
    commitGeo();
  }, 100);
});
$('n-scale')?.addEventListener('input', (e) => {
  let val = parseInt(e.target.value);
  if (isNaN(val)) return;
  val = Math.max(0, Math.min(val, 100));
  if ($('s-scale')) $('s-scale').value = val;
  $('v-scale').textContent = val + '%';
  S.geo.scale = Math.max(1, val) / 100;
  clearTimeout(scaleTimer);
  scaleTimer = setTimeout(() => {
    commitGeo();
  }, 100);
});
if ($('btn-scale-reset')) $('btn-scale-reset').onclick = async () => {
  if (!S.hasImage) return;
  S.geo.scale = 1.0;
  $('s-scale').value = 100;
  $('v-scale').textContent = '100%';
  if ($('n-scale')) $('n-scale').value = 100;
  await pushHistory();
  commitGeo();
};

/* ─── CROP MOUSE DRAG & RESIZE LOGIC ─── */
function getRenderedImageRect(img) {
  if (!img || !img.complete || img.naturalWidth === 0) return null;
  const rect = img.getBoundingClientRect();
  const wrapRect = img.parentElement.getBoundingClientRect();
  
  const imgRatio = img.naturalWidth / img.naturalHeight;
  const containerRatio = rect.width / rect.height;
  
  let renderW, renderH, renderX, renderY;
  if (imgRatio > containerRatio) {
    renderW = rect.width;
    renderH = rect.width / imgRatio;
    renderX = rect.left - wrapRect.left;
    renderY = (rect.height - renderH) / 2 + (rect.top - wrapRect.top);
  } else {
    renderH = rect.height;
    renderW = rect.height * imgRatio;
    renderY = rect.top - wrapRect.top;
    renderX = (rect.width - renderW) / 2 + (rect.left - wrapRect.left);
  }
  
  return {
    left: renderX,
    top: renderY,
    width: renderW,
    height: renderH,
    naturalWidth: img.naturalWidth,
    naturalHeight: img.naturalHeight
  };
}

function updateCropOverlayPosition() {
  const rect = getRenderedImageRect(imgAfter);
  if (!rect) return;
  cropOverlay.style.left = rect.left + 'px';
  cropOverlay.style.top = rect.top + 'px';
  cropOverlay.style.width = rect.width + 'px';
  cropOverlay.style.height = rect.height + 'px';
  
  if (parseFloat(cropBox.style.width) === 0 || !cropBox.style.width) {
    cropBox.style.left = (rect.width * 0.1) + 'px';
    cropBox.style.top = (rect.height * 0.1) + 'px';
    cropBox.style.width = (rect.width * 0.8) + 'px';
    cropBox.style.height = (rect.height * 0.8) + 'px';
  }
  updateCropMasks();
}

function updateCropMasks() {
  const boxL = parseFloat(cropBox.style.left) || 0;
  const boxT = parseFloat(cropBox.style.top) || 0;
  const boxW = parseFloat(cropBox.style.width) || 0;
  const boxH = parseFloat(cropBox.style.height) || 0;
  
  const overlayW = parseFloat(cropOverlay.style.width) || 0;
  const overlayH = parseFloat(cropOverlay.style.height) || 0;
  
  if ($('crop-mask-top')) {
    $('crop-mask-top').style.left = '0px';
    $('crop-mask-top').style.top = '0px';
    $('crop-mask-top').style.width = overlayW + 'px';
    $('crop-mask-top').style.height = boxT + 'px';
  }
  if ($('crop-mask-bottom')) {
    $('crop-mask-bottom').style.left = '0px';
    $('crop-mask-bottom').style.top = (boxT + boxH) + 'px';
    $('crop-mask-bottom').style.width = overlayW + 'px';
    $('crop-mask-bottom').style.height = (overlayH - boxT - boxH) + 'px';
  }
  if ($('crop-mask-left')) {
    $('crop-mask-left').style.left = '0px';
    $('crop-mask-left').style.top = boxT + 'px';
    $('crop-mask-left').style.width = boxL + 'px';
    $('crop-mask-left').style.height = boxH + 'px';
  }
  if ($('crop-mask-right')) {
    $('crop-mask-right').style.left = (boxL + boxW) + 'px';
    $('crop-mask-right').style.top = boxT + 'px';
    $('crop-mask-right').style.width = (overlayW - boxL - boxW) + 'px';
    $('crop-mask-right').style.height = boxH + 'px';
  }
}

let isCropDragging = false;
let cropDragStartX, cropDragStartY, cropDragStartLeft, cropDragStartTop;

cropBox.addEventListener('mousedown', (e) => {
  if (e.target.classList.contains('crop-handle')) return;
  isCropDragging = true;
  cropDragStartX = e.clientX;
  cropDragStartY = e.clientY;
  cropDragStartLeft = parseFloat(cropBox.style.left) || 0;
  cropDragStartTop = parseFloat(cropBox.style.top) || 0;
  document.addEventListener('mousemove', onCropDrag);
  document.addEventListener('mouseup', onStopCropDrag);
});

function onCropDrag(e) {
  if (!isCropDragging) return;
  const dx = e.clientX - cropDragStartX;
  const dy = e.clientY - cropDragStartY;
  
  const overlayW = parseFloat(cropOverlay.style.width) || 0;
  const overlayH = parseFloat(cropOverlay.style.height) || 0;
  const boxW = parseFloat(cropBox.style.width) || 0;
  const boxH = parseFloat(cropBox.style.height) || 0;
  
  let newL = cropDragStartLeft + dx;
  let newT = cropDragStartTop + dy;
  
  newL = Math.max(0, Math.min(newL, overlayW - boxW));
  newT = Math.max(0, Math.min(newT, overlayH - boxH));
  
  cropBox.style.left = newL + 'px';
  cropBox.style.top = newT + 'px';
  updateCropMasks();
}

function onStopCropDrag() {
  isCropDragging = false;
  document.removeEventListener('mousemove', onCropDrag);
  document.removeEventListener('mouseup', onStopCropDrag);
}

let isCropResizing = false;
let activeHandle = null;
let cropResizeStartLeft, cropResizeStartTop, cropResizeStartWidth, cropResizeStartHeight;

cropBox.addEventListener('mousedown', (e) => {
  if (!e.target.classList.contains('crop-handle')) return;
  isCropResizing = true;
  activeHandle = e.target.dataset.pos;
  cropDragStartX = e.clientX;
  cropDragStartY = e.clientY;
  cropResizeStartLeft = parseFloat(cropBox.style.left) || 0;
  cropResizeStartTop = parseFloat(cropBox.style.top) || 0;
  cropResizeStartWidth = parseFloat(cropBox.style.width) || 0;
  cropResizeStartHeight = parseFloat(cropBox.style.height) || 0;
  e.stopPropagation();
  document.addEventListener('mousemove', onCropResize);
  document.addEventListener('mouseup', onStopCropResize);
});

function onCropResize(e) {
  if (!isCropResizing) return;
  const dx = e.clientX - cropDragStartX;
  const dy = e.clientY - cropDragStartY;
  
  const overlayW = parseFloat(cropOverlay.style.width) || 0;
  const overlayH = parseFloat(cropOverlay.style.height) || 0;
  
  let newL = cropResizeStartLeft;
  let newT = cropResizeStartTop;
  let newW = cropResizeStartWidth;
  let newH = cropResizeStartHeight;
  
  const minSize = 20;
  
  if (activeHandle.includes('r')) {
    newW = Math.max(minSize, Math.min(cropResizeStartWidth + dx, overlayW - newL));
  }
  if (activeHandle.includes('b')) {
    newH = Math.max(minSize, Math.min(cropResizeStartHeight + dy, overlayH - newT));
  }
  if (activeHandle.includes('l')) {
    const maxDx = cropResizeStartWidth - minSize;
    const finalDx = Math.max(-cropResizeStartLeft, Math.min(dx, maxDx));
    newL = cropResizeStartLeft + finalDx;
    newW = cropResizeStartWidth - finalDx;
  }
  if (activeHandle.includes('t')) {
    const maxDx = cropResizeStartHeight - minSize;
    const finalDy = Math.max(-cropResizeStartTop, Math.min(dy, maxDx));
    newT = cropResizeStartTop + finalDy;
    newH = cropResizeStartHeight - finalDy;
  }
  
  cropBox.style.left = newL + 'px';
  cropBox.style.top = newT + 'px';
  cropBox.style.width = newW + 'px';
  cropBox.style.height = newH + 'px';
  updateCropMasks();
}

function onStopCropResize() {
  isCropResizing = false;
  document.removeEventListener('mousemove', onCropResize);
  document.removeEventListener('mouseup', onStopCropResize);
}

if ($('btn-crop-mode')) $('btn-crop-mode').onclick = () => {
  if (!S.hasImage) return;
  S.cropMode = !S.cropMode;
  if (S.cropMode) {
    S.geo.rotate = 0;
    S.geo.scale = 1.0;
    if ($('s-rotate')) { $('s-rotate').value = 0; $('v-rotate').textContent = '0°'; }
    if ($('s-scale')) { $('s-scale').value = 100; $('v-scale').textContent = '100%'; if ($('n-scale')) $('n-scale').value = 100; }
    
    pushHistory().then(() => commitGeo()).then(() => {
      cropOverlay.hidden = false;
      cropActions.hidden = false;
      updateCropOverlayPosition();
    });
  } else {
    cropOverlay.hidden = true;
    cropActions.hidden = true;
  }
};

if ($('btn-crop-cancel')) $('btn-crop-cancel').onclick = () => {
  S.cropMode = false;
  cropOverlay.hidden = true;
  cropActions.hidden = true;
};

if ($('btn-crop-apply')) $('btn-crop-apply').onclick = async () => {
  if (!S.hasImage) return;
  const rect = getRenderedImageRect(imgAfter);
  if (!rect) return;
  
  const overlayW = parseFloat(cropOverlay.style.width) || rect.width;
  const overlayH = parseFloat(cropOverlay.style.height) || rect.height;
  
  const boxL = parseFloat(cropBox.style.left) || 0;
  const boxT = parseFloat(cropBox.style.top) || 0;
  const boxW = parseFloat(cropBox.style.width) || 0;
  const boxH = parseFloat(cropBox.style.height) || 0;
  
  const scaleX = rect.naturalWidth / overlayW;
  const scaleY = rect.naturalHeight / overlayH;
  
  const left = Math.round(boxL * scaleX);
  const top = Math.round(boxT * scaleY);
  const right = Math.round((boxL + boxW) * scaleX);
  const bottom = Math.round((boxT + boxH) * scaleY);
  
  S.cropMode = false;
  cropOverlay.hidden = true;
  cropActions.hidden = true;
  
  await pushHistory();
  const data = await api('crop', { left, top, right, bottom });
  if (data) {
    S.geo.crop = [left, top, right, bottom];
  }
};

window.addEventListener('resize', () => {
  if (S.cropMode) {
    updateCropOverlayPosition();
  }
});

/* ─── TRANSLATION (GESER/DRAG) LOGIC ─── */
let isTranslating = false;
let transStartX, transStartY, transStartTx, transStartTy;

if ($('btn-drag-mode')) $('btn-drag-mode').onclick = () => {
  if (!S.hasImage) return;
  S.dragMode = !S.dragMode;
  if (S.dragMode) {
    $('btn-drag-mode').classList.add('active');
    imgAfter.style.cursor = 'move';
    setStatus('Mode Geser aktif: Seret (drag) gambar untuk menggeser.', 'ok');
  } else {
    $('btn-drag-mode').classList.remove('active');
    imgAfter.style.cursor = '';
    imgAfter.style.transform = '';
  }
};

imgAfter.addEventListener('mousedown', (e) => {
  if (!S.dragMode || !S.hasImage) return;
  isTranslating = true;
  transStartX = e.clientX;
  transStartY = e.clientY;
  transStartTx = S.geo.tx;
  transStartTy = S.geo.ty;
  e.preventDefault();
  document.addEventListener('mousemove', onTranslateMove);
  document.addEventListener('mouseup', onTranslateStop);
});

function onTranslateMove(e) {
  if (!isTranslating) return;
  const dx = e.clientX - transStartX;
  const dy = e.clientY - transStartY;
  
  const rect = getRenderedImageRect(imgAfter);
  const scaleX = rect ? (rect.naturalWidth / rect.width) : 1.0;
  const scaleY = rect ? (rect.naturalHeight / rect.height) : 1.0;
  
  const serverTx = Math.round(transStartTx + dx * scaleX);
  const serverTy = Math.round(transStartTy + dy * scaleY);
  
  $('n-tx').value = serverTx;
  $('n-ty').value = serverTy;
  
  imgAfter.style.transform = `translate(${transStartTx / scaleX + dx}px, ${transStartTy / scaleY + dy}px)`;
}

async function onTranslateStop() {
  if (!isTranslating) return;
  isTranslating = false;
  document.removeEventListener('mousemove', onTranslateMove);
  document.removeEventListener('mouseup', onTranslateStop);
  
  S.geo.tx = parseInt($('n-tx').value) || 0;
  S.geo.ty = parseInt($('n-ty').value) || 0;
  
  await pushHistory();
  commitGeo();
}

if ($('btn-translate')) $('btn-translate').onclick = async () => {
  if (!S.hasImage) return;
  const tx = parseInt($('n-tx').value) || 0;
  const ty = parseInt($('n-ty').value) || 0;
  S.geo.tx = tx;
  S.geo.ty = ty;
  await pushHistory();
  commitGeo();
};
/* ═══════════════════════════════════════════════
   FLOATING POPUP MODALS MANAGEMENT (REUSABLE DRAG)
═══════════════════════════════════════════════ */
function makeDraggable(headerId, boxId) {
    const header = $(headerId), box = $(boxId);
    if (!header || !box) return;
    let isDragging = false, startX, startY, startLeft, startTop;
    header.style.cursor = 'grab';
    header.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('hist-close')) return;
        isDragging = true; header.style.cursor = 'grabbing';
        startX = e.clientX; startY = e.clientY;
        const rect = box.getBoundingClientRect();
        if (box.style.transform) { box.style.left = rect.left + 'px'; box.style.top = rect.top + 'px'; box.style.transform = 'none'; }
        startLeft = parseInt(window.getComputedStyle(box).left, 10) || rect.left;
        startTop = parseInt(window.getComputedStyle(box).top, 10) || rect.top;
        document.addEventListener('mousemove', onDrag); document.addEventListener('mouseup', onStopDrag);
    });
    function onDrag(e) { if (!isDragging) return; box.style.left = (startLeft + (e.clientX - startX)) + 'px'; box.style.top = (startTop + (e.clientY - startY)) + 'px'; }
    function onStopDrag() { isDragging = false; header.style.cursor = 'grab'; document.removeEventListener('mousemove', onDrag); document.removeEventListener('mouseup', onStopDrag); }
}

makeDraggable('hsv-header', 'hsv-box');
makeDraggable('enhance-header', 'enhance-box');
makeDraggable('hist-header', 'hist-box');
makeDraggable('transform-header', 'transform-box');
makeDraggable('segmentation-header', 'segmentation-box');
makeDraggable('restoration-header', 'restoration-box');

// Trigger Pembukaan Modals Panel Dari Dropdown Menu
$('btn-open-hsv')?.addEventListener('click', async () => { if (!S.hasImage) return; $('hsv-modal').hidden = false; await snapshotRestoreBase(); previewHSV(); });
$('btn-open-enhance')?.addEventListener('click', () => { if (!S.hasImage) return; $('enhance-modal').hidden = false; });
$('btn-toggle-hist')?.addEventListener('click', () => { if (!S.hasImage) return; $('hist-modal').hidden = !$('hist-modal').hidden; triggerRealtimeHistogram(); });

$('hsv-close').onclick = $('btn-hsv-cancel').onclick = async () => { $('hsv-modal').hidden = true; await api('restore/revert', null, 'POST'); };
$('enhance-close').onclick = $('btn-enhance-cancel').onclick = () => { $('enhance-modal').hidden = true; };
$('hist-close').onclick = () => { $('hist-modal').hidden = true; };

// Pemroses Slider Enhancement di dalam Popup Modal
let enhTimer;
Object.entries(ENH_SLIDERS).forEach(([k, s]) => {
  if(!s.el) return;
  s.el.addEventListener('input', () => {
    s.val.textContent = s.el.value; if (!S.hasImage) return;
    clearTimeout(enhTimer); enhTimer = setTimeout(() => api('enhance', getEnhValues()), 60);
  });
});
$('btn-enhance-ok').onclick = async () => { if(!S.hasImage) return; $('enhance-modal').hidden = true; await pushHistory(); api('enhance', getEnhValues()); };

/* ═══════════════════════════════════════════════
   FITUR 5 & 7: SEGMENTATION, EDGE, & MORPHOLOGY LOGIC
═══════════════════════════════════════════════ */
let segTimer;

document.querySelectorAll('[data-seg]').forEach(btn => {
  btn.onclick = async () => {
    if (S.hasImage) await api('restore/revert', null, 'POST');
    document.querySelectorAll('[data-seg]').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('#segmentation-modal .restore-params').forEach(p => p.classList.remove('active'));
    
    btn.classList.add('active');
    S.activeSegFilter = btn.dataset.seg;
    
    // Penentuan target id tab slider parameter di UI
    let targetParamId = 'sp-' + S.activeSegFilter;
    if (S.activeSegFilter.startsWith('edge_') && S.activeSegFilter !== 'edge_canny') {
        targetParamId = 'sp-edge_fixed'; // Gunakan info badge untuk filter otomatis
    }
    if (S.activeSegFilter.startsWith('morph_')) {
        targetParamId = 'sp-morph';
    }
    
    const rp = $(targetParamId);
    if(rp) rp.classList.add('active');
    
    await snapshotRestoreBase();
    previewSegmentation();
  };
});

function previewSegmentation() {
  if (!S.hasImage) return;
  clearTimeout(segTimer);
  segTimer = setTimeout(async () => {
     const f = S.activeSegFilter;
     let url = '', payload = {};
     
     if (f === 'threshold') {
         url = '/api/binary/threshold'; // Direct preview ke fitur biner baru
         payload = { threshold: +$('s-seg-thresh').value };
     } else if (f === 'kmeans') {
         url = '/api/segment/preview/kmeans';
         payload = { clusters: +$('s-seg-k').value };
     } else if (f.startsWith('edge_')) {
         url = '/api/binary/preview/edge';
         const methodType = f.replace('edge_', '');
         payload = { 
             method: methodType, 
             p1: +$('s-canny-low').value, 
             p2: +$('s-canny-high').value 
         };
     } else if (f.startsWith('morph_')) {
         url = '/api/binary/preview/morph';
         const opType = f.replace('morph_', '');
         payload = { 
             operation: opType, 
             size: +$('s-morph-size').value * 2 + 1 // Ubah 1,2,3 jadi ganjil (3x3, 5x5, 7x7) 
         };
     }
     
     // Trigger hit preview ke server
     if(f === 'threshold') {
         // Khusus threshold panggil endpoint preview
         showLoading(true);
         const res = await fetch('/api/binary/preview/threshold', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
         const data = await res.json(); showLoading(false);
         if (res.ok && data.image) showImage(data.image, imgAfter);
     } else {
         showLoading(true);
         const res = await fetch(url, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
         const data = await res.json(); showLoading(false);
         if (res.ok && data.image) showImage(data.image, imgAfter);
     }
  }, 150);
}

// Hubungkan semua listener slider di dalam tab segmentation
['s-seg-thresh', 's-seg-k', 's-canny-low', 's-canny-high'].forEach(id => {
  $(id)?.addEventListener('input', (e) => { $(id.replace('s-', 'v-')).textContent = e.target.value; previewSegmentation(); });
});

$('s-morph-size')?.addEventListener('input', (e) => {
    const actSize = +e.target.value * 2 + 1;
    $('v-morph-size').textContent = `${actSize}×${actSize}`;
    previewSegmentation();
});

// Listener Tombol eksekusi komit riwayat final (Biar Masuk Antrean Undo/Redo!)
$('btn-segment-apply').onclick = async () => {
  if (!S.hasImage) return;
  const f = S.activeSegFilter;
  let url = '', payload = {};
  
  if (f === 'threshold') { url = 'binary/threshold'; payload = { threshold: +$('s-seg-thresh').value }; }
  else if (f === 'kmeans') { url = 'segment/kmeans'; payload = { clusters: +$('s-seg-k').value }; }
  else if (f.startsWith('edge_')) {
      url = 'binary/edge';
      payload = { method: f.replace('edge_', ''), p1: +$('s-canny-low').value, p2: +$('s-canny-high').value };
  }
  else if (f.startsWith('morph_')) {
      url = 'binary/morph';
      payload = { operation: f.replace('morph_', ''), size: +$('s-morph-size').value * 2 + 1 };
  }
  
  await pushHistory();
  await api(url, payload);
  await snapshotRestoreBase();
};

$('btn-segment-preview').onclick = async () => { if (S.hasImage) { await api('restore/revert', null, 'POST'); await snapshotRestoreBase(); previewSegmentation(); } };

/* ═══════════════════════════════════════════════
   FITUR 8: IMAGE COMPRESSION INTERACTION LOGIC
═══════════════════════════════════════════════ */
const compressModal = $('compress-modal');
const compressBox   = $('compress-box');
let compressTimer;

// 1. Daftarkan agar pop-up kompresi bisa digeser melayang di layar
makeDraggable('compress-header', 'compress-box');

// 2. Event buka jendela modal kompresi dari Dropdown File Navbar
$('btn-open-compress')?.addEventListener('click', async () => {
    if (!S.hasImage) return;
    $('s-compress-quality').value = 80;
    $('v-compress-quality').textContent = '80%';
    
    // Ambil basis gambar saat ini untuk di-preview secara temporer
    await snapshotRestoreBase();
    if(compressModal) compressModal.hidden = false;
    previewCompression();
});

// 3. Fungsi penutup jendela modal
function closeCompressModal() { if(compressModal) compressModal.hidden = true; }
$('compress-close').onclick = $('btn-compress-cancel').onclick = async () => {
    closeCompressModal();
    await api('restore/revert', null, 'POST'); // Kembalikan canvas ke visual awal tanpa kompresi
};

// 4. Logika Live Preview Perubahan Ukuran File Saat Slider Digeser
function previewCompression() {
    if (!S.hasImage) return;
    clearTimeout(compressTimer);
    compressTimer = setTimeout(async () => {
        const qVal = parseInt($('s-compress-quality').value);
        showLoading(true);
        
        const res = await fetch('/api/compress/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ quality: qVal })
        });
        const data = await res.json();
        showLoading(false);
        
        if (res.ok && data.image) {
            // Render gambar hasil kompresi ke panel AFTER secara realtime
            imgAfter.src = `data:image/jpeg;base64,${data.image}`;
            // Update teks info rasio penghematan memori di dalam popup
            const badge = $('compress-info-badge');
            if(badge) badge.textContent = `Size: ${data.size_kb} | Space Saved: ${data.ratio}`;
        }
    }, 120);
}

// Hubungkan pergerakan thumb slider ke fungsi preview
$('s-compress-quality')?.addEventListener('input', (e) => {
    $('v-compress-quality').textContent = e.target.value + '%';
    previewCompression();
});

// 5. Tombol Kompresi OK (Save Image secara permanen ke tumpukan Undo/Redo)
$('btn-compress-ok').onclick = async () => {
    if (!S.hasImage) return;
    const qVal = parseInt($('s-compress-quality').value);
    closeCompressModal();
    
    // Tembak API Save untuk mencatatkan state ke tumpukan riwayat Python
    await api('compress/save', { quality: qVal });
    await snapshotRestoreBase(); // Refresh snapshot basis
};