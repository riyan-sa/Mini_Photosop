/* ══════════════════════════════════════════════════════════
   Mini Photoshop — app.js v4
   Live preview via CSS transform, commit on release
   ══════════════════════════════════════════════════════════ */

/* ─── State ─────────────────────────────────────────────── */
const S = {
  hasImage: false,
  imgW: 0, imgH: 0,
  // geo state (mirrors server)
  geo: { flip_h: false, flip_v: false, crop: null,
         scale: 1.0, rotate: 0.0, tx: 0, ty: 0 },
  // enh state
  enh: { brightness: 1.0, contrast: 1.0, sharpen: 1.0, blur: 0.0 },
  cropMode: false,
  resizeMode: false,
  dragMode: false,   // translation drag
};

/* ─── Elements ───────────────────────────────────────────── */
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

/* ─── Helpers ────────────────────────────────────────────── */
const setStatus = (msg, type='') => {
  statusBar.textContent = msg;
  statusBar.className = 'status-bar ' + type;
};
const showLoading = show => loading.style.display = show ? 'flex' : 'none';

function showImage(b64, target) {
  target.src = 'data:image/jpeg;base64,' + b64;
  target.style.display = 'block';
  target.style.transform = '';   // clear CSS preview transform on new image
}

function updateInfo(info) {
  if (!info?.width) return;
  S.imgW = info.width; S.imgH = info.height;
  imgInfo.textContent = `${info.width} × ${info.height}px · ${info.mode}`;
  $('n-width').value  = info.width;
  $('n-height').value = info.height;
}

function getEnhValues() {
  return {
    brightness: +ENH_SLIDERS.brightness.el.value / 100,
    contrast:   +ENH_SLIDERS.contrast.el.value   / 100,
    sharpen:    +ENH_SLIDERS.sharpen.el.value     / 100,
    blur:       +ENH_SLIDERS.blur.el.value        / 2,
  };
}

function resetEnhSliders() {
  Object.values(ENH_SLIDERS).forEach(s => {
    s.el.value = s.default;
    s.val.textContent = s.default;
  });
  S.enh = { brightness:1.0, contrast:1.0, sharpen:1.0, blur:0.0 };
}

function resetGeoUI() {
  $('s-rotate').value = 0;  $('v-rotate').textContent = '0°';
  $('s-scale').value  = 100; $('v-scale').textContent  = '100%';
  $('n-tx').value = 0; $('n-ty').value = 0;
  S.geo = { flip_h:false, flip_v:false, crop:null, scale:1.0, rotate:0.0, tx:0, ty:0 };
  imgAfter.style.transform = '';
  imgAfter.style.transformOrigin = '';
}

function clearCanvas() {
  imgBefore.style.display = imgAfter.style.display = 'none';
  imgBefore.src = imgAfter.src = '';
  emptyState.style.display = '';
  S.hasImage = false;
  imgInfo.textContent = '—';
  resetEnhSliders(); resetGeoUI();
  exitCropMode(); exitResizeMode(); exitDragMode();
}

/* ─── Tabs ───────────────────────────────────────────────── */
document.querySelectorAll('.tab').forEach(tab =>
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    $('tab-' + tab.dataset.tab).classList.add('active');
  })
);

/* ─── API ────────────────────────────────────────────────── */
async function api(endpoint, body=null, method='POST') {
  showLoading(true);
  try {
    const opts = { method };
    if (body) { opts.headers = {'Content-Type':'application/json'}; opts.body = JSON.stringify(body); }
    const res  = await fetch('/api/' + endpoint, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error');
    showImage(data.image, imgAfter);
    updateInfo(data.info);
    setStatus('✓ ' + data.message, 'ok');
    return data;
  } catch(e) {
    setStatus('✕ ' + e.message, 'error');
    return null;
  } finally { showLoading(false); }
}

function commitGeo(msg='') {
  return api('geo_commit', { ...S.geo, crop: S.geo.crop ? [...S.geo.crop] : null });
}

async function pushHistory() {
  try { await fetch('/api/push_history', {method:'POST'}); } catch(e) {}
}

/* ─── Upload ─────────────────────────────────────────────── */
async function uploadImage(file) {
  const form = new FormData();
  form.append('file', file);
  showLoading(true);
  try {
    const res  = await fetch('/api/upload', { method:'POST', body:form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    emptyState.style.display = 'none';
    showImage(data.image, imgBefore);
    showImage(data.image, imgAfter);
    S.hasImage = true;
    updateInfo(data.info);
    resetEnhSliders(); resetGeoUI();
    setStatus(`✓ ${file.name} diupload.`, 'ok');
  } catch(e) { setStatus('✕ ' + e.message, 'error'); }
  finally { showLoading(false); }
}

/* ─── Enhancement — live on input, commit on change ─────── */
let enhTimer;
Object.entries(ENH_SLIDERS).forEach(([k, s]) => {
  // update label instantly
  s.el.addEventListener('input', () => {
    s.val.textContent = s.el.value;
    if (!S.hasImage) return;
    S.enh = getEnhValues();
    clearTimeout(enhTimer);
    enhTimer = setTimeout(() => api('enhance', getEnhValues()), 80);
  });
});

/* ─── ROTATE — debounce direct to server ────────────────── */
const sRotate = $('s-rotate');
const vRotate = $('v-rotate');
let rotateTimer;

sRotate.addEventListener('input', () => {
  const deg = +sRotate.value;
  vRotate.textContent = deg + '°';
  S.geo.rotate = deg;
  if (!S.hasImage) return;
  clearTimeout(rotateTimer);
  rotateTimer = setTimeout(() => commitGeo(), 120);
});

/* ─── SCALE — debounce direct to server ─────────────────── */
const sScale = $('s-scale');
const vScale = $('v-scale');
let scaleTimer;

sScale.addEventListener('input', () => {
  const pct = +sScale.value;
  vScale.textContent = pct + '%';
  const nScale = document.getElementById('n-scale');
  if (nScale) nScale.value = pct;
  S.geo.scale = pct / 100;
  if (!S.hasImage) return;
  clearTimeout(scaleTimer);
  scaleTimer = setTimeout(() => commitGeo(), 120);
});

// Input angka scale
const nScaleEl = document.getElementById('n-scale');
if (nScaleEl) {
  nScaleEl.addEventListener('change', () => {
    const pct = Math.max(10, Math.min(2000, +nScaleEl.value));
    nScaleEl.value = pct;
    sScale.value = Math.min(1000, pct);
    vScale.textContent = pct + '%';
    S.geo.scale = pct / 100;
    if (S.hasImage) commitGeo();
  });
}

/* CSS transform helper (used only for drag translation preview) */
function buildCSSTransform() {
  if (S.geo.tx || S.geo.ty) return `translate(${S.geo.tx}px, ${S.geo.ty}px)`;
  return '';
}

/* ─── TRANSLATION — drag the image ──────────────────────── */
let dragStartX, dragStartY, dragOrigTx, dragOrigTy;

function enterDragMode() {
  if (!S.hasImage) return;
  S.dragMode = true;
  imgAfter.style.cursor = 'grab';
  $('btn-drag-mode').textContent = '✕ Keluar Mode Geser';
  imgAfter.addEventListener('pointerdown', startImageDrag);
}
function exitDragMode() {
  S.dragMode = false;
  if (imgAfter) { imgAfter.style.cursor = ''; imgAfter.removeEventListener('pointerdown', startImageDrag); }
  const btn = $('btn-drag-mode');
  if (btn) btn.textContent = '⤳ Mode Geser Gambar';
}
function startImageDrag(e) {
  e.preventDefault();
  imgAfter.style.cursor = 'grabbing';
  dragStartX = e.clientX; dragStartY = e.clientY;
  dragOrigTx = S.geo.tx;  dragOrigTy = S.geo.ty;

  function onMove(e) {
    const dx = Math.round(e.clientX - dragStartX);
    const dy = Math.round(e.clientY - dragStartY);
    S.geo.tx = dragOrigTx + dx;
    S.geo.ty = dragOrigTy + dy;
    $('n-tx').value = S.geo.tx;
    $('n-ty').value = S.geo.ty;
    imgAfter.style.transform = buildCSSTransform();
    imgAfter.style.transformOrigin = 'center center';
  }
  function onUp() {
    imgAfter.style.cursor = 'grab';
    imgAfter.style.transform = '';
    commitGeo();
    document.removeEventListener('pointermove', onMove);
    document.removeEventListener('pointerup', onUp);
  }
  document.addEventListener('pointermove', onMove);
  document.addEventListener('pointerup', onUp);
}

/* ─── CROP — interactive overlay ────────────────────────── */
let crop = { x:10, y:10, w:80, h:80 }; // in % of displayed image

function enterCropMode() {
  if (!S.hasImage) return;
  exitResizeMode(); exitDragMode();
  S.cropMode = true;
  crop = { x:10, y:10, w:80, h:80 };
  cropOverlay.hidden = false;
  cropActions.hidden = false;
  $('btn-crop-mode').textContent = '✕ Keluar Crop';
  $('after-label').textContent = 'AFTER — MODE CROP';
  updateCropBox();
  initCropDrag();
}
function exitCropMode() {
  S.cropMode = false;
  cropOverlay.hidden = true;
  cropActions.hidden = true;
  const b = $('btn-crop-mode'); if (b) b.textContent = '✂ Mode Crop';
  const l = $('after-label');   if (l) l.textContent = 'AFTER';
}

function updateCropBox() {
  const wrap = afterWrap.getBoundingClientRect();
  const img  = imgAfter.getBoundingClientRect();
  const ox = img.left - wrap.left, oy = img.top - wrap.top;
  const iw = img.width, ih = img.height;
  const bx = ox + (crop.x/100)*iw, by = oy + (crop.y/100)*ih;
  const bw = (crop.w/100)*iw,      bh = (crop.h/100)*ih;

  cropBox.style.cssText = `left:${bx}px;top:${by}px;width:${bw}px;height:${bh}px`;
  $('crop-mask-top').style.cssText    = `top:${oy}px;left:${ox}px;width:${iw}px;height:${by-oy}px`;
  $('crop-mask-left').style.cssText   = `top:${by}px;left:${ox}px;width:${bx-ox}px;height:${bh}px`;
  $('crop-mask-right').style.cssText  = `top:${by}px;left:${bx+bw}px;width:${ox+iw-bx-bw}px;height:${bh}px`;
  $('crop-mask-bottom').style.cssText = `top:${by+bh}px;left:${ox}px;width:${iw}px;height:${oy+ih-by-bh}px`;
}

function initCropDrag() {
  cropBox.querySelectorAll('.crop-handle').forEach(h => {
    h.onpointerdown = e => {
      e.preventDefault(); e.stopPropagation();
      const pos = h.dataset.pos;
      const img = imgAfter.getBoundingClientRect();
      const sx = e.clientX, sy = e.clientY, orig = {...crop};
      const onMove = e => {
        const dx=(e.clientX-sx)/img.width*100, dy=(e.clientY-sy)/img.height*100;
        let {x,y,w,h} = orig;
        if(pos.includes('r')) w=Math.max(5,Math.min(100-x, w+dx));
        if(pos.includes('b')) h=Math.max(5,Math.min(100-y, h+dy));
        if(pos.includes('l')){ w=Math.max(5,w-dx); x=Math.min(orig.x+orig.w-5, orig.x+dx); }
        if(pos.includes('t')){ h=Math.max(5,h-dy); y=Math.min(orig.y+orig.h-5, orig.y+dy); }
        crop={x,y,w,h}; updateCropBox();
      };
      const onUp = () => { document.removeEventListener('pointermove',onMove); document.removeEventListener('pointerup',onUp); };
      document.addEventListener('pointermove',onMove);
      document.addEventListener('pointerup',onUp);
    };
  });
  cropBox.onpointerdown = e => {
    if(e.target.classList.contains('crop-handle')) return;
    e.preventDefault();
    const img=imgAfter.getBoundingClientRect();
    const sx=e.clientX, sy=e.clientY, orig={...crop};
    const onMove=e=>{
      crop.x=Math.max(0,Math.min(100-orig.w, orig.x+(e.clientX-sx)/img.width*100));
      crop.y=Math.max(0,Math.min(100-orig.h, orig.y+(e.clientY-sy)/img.height*100));
      updateCropBox();
    };
    const onUp=()=>{ document.removeEventListener('pointermove',onMove); document.removeEventListener('pointerup',onUp); };
    document.addEventListener('pointermove',onMove);
    document.addEventListener('pointerup',onUp);
  };
}

async function applyCrop() {
  // konversi % display → piksel gambar di server (setelah flip, sebelum scale/rotate)
  // ambil ukuran geo_img sebelum scale/rotate: approx = imgW/scale
  const baseW = Math.round(S.imgW / S.geo.scale);
  const baseH = Math.round(S.imgH / S.geo.scale);
  const l = Math.round((crop.x/100)*baseW);
  const t = Math.round((crop.y/100)*baseH);
  const r = Math.round(((crop.x+crop.w)/100)*baseW);
  const b = Math.round(((crop.y+crop.h)/100)*baseH);
  await pushHistory(); await api('crop', {left:l, top:t, right:r, bottom:b});
  // sync scale ke 1 karena crop sudah mengubah ukuran dasar
  S.geo.scale = 1.0; $('s-scale').value=100; $('v-scale').textContent='100%';
  exitCropMode();
}

/* ─── RESIZE drag ────────────────────────────────────────── */
function enterResizeMode() {
  if (!S.hasImage) return;
  exitCropMode(); exitDragMode();
  S.resizeMode = true;
  resizeOverlay.hidden = false;
  $('btn-resize-mode').textContent = '✕ Keluar Mode Tarik';
  positionResizeHandles();
  resizeOverlay.querySelectorAll('.resize-handle').forEach(h => h.addEventListener('pointerdown', startResizeDrag));
}
function exitResizeMode() {
  S.resizeMode = false;
  resizeOverlay.hidden = true;
  const b = $('btn-resize-mode'); if(b) b.textContent = '⤡ Mode Tarik';
  resizeOverlay.querySelectorAll('.resize-handle').forEach(h => h.removeEventListener('pointerdown', startResizeDrag));
}
function positionResizeHandles() {
  const img  = imgAfter.getBoundingClientRect();
  const wrap = afterWrap.getBoundingClientRect();
  resizeOverlay.style.cssText = `left:${img.left-wrap.left}px;top:${img.top-wrap.top}px;width:${img.width}px;height:${img.height}px`;
}
function startResizeDrag(e) {
  e.preventDefault();
  const pos=e.target.dataset.pos;
  const sx=e.clientX, sy=e.clientY;
  const sw=S.imgW, sh=S.imgH;
  const scale = imgAfter.getBoundingClientRect().width / S.imgW;
  let resizeTimer;
  const onMove=e=>{
    const dx=e.clientX-sx, dy=e.clientY-sy;
    let nw=sw, nh=sh;
    if(pos.includes('r')||pos==='br') nw=Math.max(10, sw+Math.round(dx/scale));
    if(pos.includes('b')||pos==='br') nh=Math.max(10, sh+Math.round(dy/scale));
    $('n-width').value=nw; $('n-height').value=nh;
    // CSS preview
    imgAfter.style.width  = (nw/sw*imgAfter.getBoundingClientRect().width)+'px';
    clearTimeout(resizeTimer);
  };
  const onUp=async e=>{
    document.removeEventListener('pointermove',onMove);
    document.removeEventListener('pointerup',onUp);
    imgAfter.style.width='';
    const nw=parseInt($('n-width').value);
    const nh=parseInt($('n-height').value);
    await pushHistory().then(()=>api('resize',{width:nw,height:nh}));
    positionResizeHandles();
  };
  document.addEventListener('pointermove',onMove);
  document.addEventListener('pointerup',onUp);
}

/* ─── Event Listeners ────────────────────────────────────── */
fileInput.addEventListener('change', e => { if(e.target.files[0]) uploadImage(e.target.files[0]); e.target.value=''; });
beforeWrap.addEventListener('click', ()=>{ if(!S.hasImage) fileInput.click(); });

$('btn-clear').addEventListener('click', ()=>{ if(S.hasImage){ clearCanvas(); setStatus('Gambar dihapus.'); } });

$('btn-apply').addEventListener('click', ()=>{ if(S.hasImage) api('enhance', getEnhValues()); });
// histeq handled by histogram modal below
$('btn-reset-sliders').addEventListener('click', ()=>{ resetEnhSliders(); if(S.hasImage) api('enhance', getEnhValues()); });

$('btn-reset').addEventListener('click', async ()=>{
  if(!S.hasImage) return;
  exitCropMode(); exitResizeMode(); exitDragMode();
  const data = await api('reset', null, 'GET');
  if(data){ showImage(data.image, imgBefore); resetEnhSliders(); resetGeoUI(); }
});

$('btn-rotate-reset').addEventListener('click', ()=>{
  sRotate.value=0; vRotate.textContent='0°'; S.geo.rotate=0;
  imgAfter.style.transform=''; if(S.hasImage) commitGeo();
});
$('btn-scale-reset').addEventListener('click', ()=>{
  sScale.value=100; vScale.textContent='100%'; S.geo.scale=1.0;
  imgAfter.style.transform=''; if(S.hasImage) commitGeo();
});

$('btn-flip-h').addEventListener('click', ()=>{ S.geo.flip_h=!S.geo.flip_h; if(S.hasImage) pushHistory().then(()=>commitGeo()); });
$('btn-flip-v').addEventListener('click', ()=>{ S.geo.flip_v=!S.geo.flip_v; if(S.hasImage) pushHistory().then(()=>commitGeo()); });

$('btn-resize').addEventListener('click', ()=>{
  const w=parseInt($('n-width').value), h=parseInt($('n-height').value);
  if(!w||!h){ setStatus('Isi width dan height.','error'); return; }
  api('resize',{width:w,height:h});
});
$('btn-resize-mode').addEventListener('click', ()=>{ S.resizeMode ? exitResizeMode() : enterResizeMode(); });

$('btn-crop-mode').addEventListener('click', ()=>{ S.cropMode ? exitCropMode() : enterCropMode(); });
$('btn-crop-apply').addEventListener('click', applyCrop);
$('btn-crop-cancel').addEventListener('click', exitCropMode);

$('btn-drag-mode').addEventListener('click', ()=>{ S.dragMode ? exitDragMode() : enterDragMode(); });
$('btn-translate').addEventListener('click', ()=>{
  S.geo.tx = parseInt($('n-tx').value)||0;
  S.geo.ty = parseInt($('n-ty').value)||0;
  if(S.hasImage) commitGeo();
});

$('btn-undo').addEventListener('click', async () => {
  if (!S.hasImage) return;
  const data = await api('undo');
  if (data) {
    // Sync enhancement sliders from server state
    if (data.enh_state) {
      const e = data.enh_state;
      ENH_SLIDERS.brightness.el.value = Math.round(e.brightness * 100);
      ENH_SLIDERS.brightness.val.textContent = Math.round(e.brightness * 100);
      ENH_SLIDERS.contrast.el.value   = Math.round(e.contrast   * 100);
      ENH_SLIDERS.contrast.val.textContent   = Math.round(e.contrast   * 100);
      ENH_SLIDERS.sharpen.el.value    = Math.round(e.sharpen    * 100);
      ENH_SLIDERS.sharpen.val.textContent    = Math.round(e.sharpen    * 100);
      ENH_SLIDERS.blur.el.value       = Math.round(e.blur       * 2);
      ENH_SLIDERS.blur.val.textContent       = Math.round(e.blur       * 2);
      S.enh = {...e};
    }
    // Sync geo sliders from server state
    if (data.geo_state) {
      const g = data.geo_state;
      S.geo = {...S.geo, ...g};
      sRotate.value = g.rotate; vRotate.textContent = g.rotate + '°';
      sScale.value  = Math.round(g.scale * 100); vScale.textContent = Math.round(g.scale * 100) + '%';
      $('n-tx').value = g.tx; $('n-ty').value = g.ty;
    }
  }
});

window.addEventListener('resize', ()=>{
  if(S.cropMode) updateCropBox();
  if(S.resizeMode) positionResizeHandles();
});

/* ═══════════════════════════════════════════════
   HISTOGRAM
═══════════════════════════════════════════════ */
let histData = null;
let histChannel = 'rgb';

const histModal  = document.getElementById('hist-modal');
const histCanvas = document.getElementById('hist-canvas');
const histCtx    = histCanvas ? histCanvas.getContext('2d') : null;

function drawHistogram(channel) {
  if (!histData || !histCtx) return;
  const W = histCanvas.width, H = histCanvas.height;
  histCtx.clearRect(0, 0, W, H);

  // background grid
  histCtx.strokeStyle = 'rgba(255,255,255,0.04)';
  histCtx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = (H / 4) * i;
    histCtx.beginPath(); histCtx.moveTo(0, y); histCtx.lineTo(W, y); histCtx.stroke();
  }
  for (let i = 0; i <= 4; i++) {
    const x = (W / 4) * i;
    histCtx.beginPath(); histCtx.moveTo(x, 0); histCtx.lineTo(x, H); histCtx.stroke();
  }

  const channels = channel === 'rgb'
    ? [{ data: histData.r, color: 'rgba(255,80,80,0.7)'  },
       { data: histData.g, color: 'rgba(80,255,120,0.7)' },
       { data: histData.b, color: 'rgba(80,160,255,0.7)' }]
    : channel === 'r'    ? [{ data: histData.r,    color: 'rgba(255,80,80,0.9)'   }]
    : channel === 'g'    ? [{ data: histData.g,    color: 'rgba(80,255,120,0.9)'  }]
    : channel === 'b'    ? [{ data: histData.b,    color: 'rgba(80,160,255,0.9)'  }]
    : /* gray */           [{ data: histData.gray, color: 'rgba(180,180,220,0.9)' }];

  const maxVal = Math.max(...channels.flatMap(c => c.data));

  channels.forEach(({ data, color }) => {
    histCtx.beginPath();
    histCtx.strokeStyle = color;
    histCtx.lineWidth = 1.5;
    data.forEach((v, i) => {
      const x = (i / 255) * W;
      const y = H - (v / maxVal) * (H - 4);
      i === 0 ? histCtx.moveTo(x, y) : histCtx.lineTo(x, y);
    });
    histCtx.stroke();

    // fill under curve
    histCtx.lineTo(W, H); histCtx.lineTo(0, H);
    histCtx.closePath();
    histCtx.fillStyle = color.replace('0.7', '0.08').replace('0.9', '0.1');
    histCtx.fill();
  });

  // x axis labels
  histCtx.fillStyle = 'rgba(100,120,160,0.8)';
  histCtx.font = '10px Share Tech Mono, monospace';
  [0, 64, 128, 192, 255].forEach(v => {
    histCtx.fillText(v, (v / 255) * W - 6, H - 4);
  });
}

async function openHistogram() {
  if (!S.hasImage) return;
  showLoading(true);
  try {
    const res  = await fetch('/api/histogram');
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    histData = data;
    histModal.hidden = false;
    drawHistogram(histChannel);
  } catch(e) {
    setStatus('✕ ' + e.message, 'error');
  } finally {
    showLoading(false);
  }
}

// Histogram button — now opens modal instead of applying filter
document.getElementById('btn-histeq').textContent = '📊 Histogram';
document.getElementById('btn-histeq').onclick = openHistogram;

// Close modal
document.getElementById('hist-close').addEventListener('click', () => {
  histModal.hidden = true;
});
histModal.addEventListener('click', e => {
  if (e.target === histModal) histModal.hidden = true;
});

// Channel tabs
document.querySelectorAll('.hist-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.hist-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    histChannel = tab.dataset.ch;
    drawHistogram(histChannel);
  });
});

/* ═══════════════════════════════════════════════
   RESTORATION
═══════════════════════════════════════════════ */
function setupSlider(sliderId, valId, transform) {
  const s = $(sliderId), v = $(valId);
  if (!s || !v) return;
  s.addEventListener('input', () => { v.textContent = transform(+s.value); });
}

// Gaussian: slider 1-20 → radius 0.5-10
setupSlider('s-gauss',     'v-gauss',     v => (v / 2).toFixed(1));
// Median: slider 1-4 → size 3,5,7,9
setupSlider('s-median',    'v-median',    v => v * 2 + 1);
// Mean: slider 1-3 → size 3,5,7
setupSlider('s-mean',      'v-mean',      v => v * 2 + 1);
// Salt pepper
setupSlider('s-sp-remove', 'v-sp-remove', v => v);
setupSlider('s-sp-add',    'v-sp-add',    v => v + '%');
// Unsharp
setupSlider('s-unsharp-r', 'v-unsharp-r', v => v);
setupSlider('s-unsharp-p', 'v-unsharp-p', v => v);

/* ═══════════════════════════════════════════════
   RESTORATION — satu filter aktif, slider = preview dari base,
   Terapkan = commit ke gambar
═══════════════════════════════════════════════ */
let activeRestoreFilter = 'gaussian';
let restoreBase = null;   // snapshot current_image saat masuk/ganti filter
let restoreTimer;

// Ambil snapshot base dari server saat masuk tab atau ganti filter
async function snapshotRestoreBase() {
  if (!S.hasImage) return;
  try {
    const res  = await fetch('/api/restore/snapshot', { method: 'POST' });
    const data = await res.json();
    if (data.ok) restoreBase = true;
  } catch(e) {}
}

// Preview filter aktif dari base (tanpa commit)
async function previewRestore() {
  if (!S.hasImage) return;
  clearTimeout(restoreTimer);
  restoreTimer = setTimeout(async () => {
    const f = activeRestoreFilter;
    let body = {};
    if (f === 'gaussian')   body = { radius: +$('s-gauss').value / 2 };
    if (f === 'median')     body = { size: +$('s-median').value * 2 + 1 };
    if (f === 'mean')       body = { size: +$('s-mean').value * 2 + 1 };
    if (f === 'saltpepper') body = { strength: +$('s-sp-remove').value };
    if (f === 'unsharp')    body = { radius: +$('s-unsharp-r').value, percent: +$('s-unsharp-p').value, threshold: 3 };
    await api(`restore/preview/${f}`, body);
  }, 200);
}

// Commit filter aktif ke gambar
async function commitRestore() {
  if (!S.hasImage) return;
  const f = activeRestoreFilter;
  let body = {};
  if (f === 'gaussian')   body = { radius: +$('s-gauss').value / 2 };
  if (f === 'median')     body = { size: +$('s-median').value * 2 + 1 };
  if (f === 'mean')       body = { size: +$('s-mean').value * 2 + 1 };
  if (f === 'saltpepper') body = { strength: +$('s-sp-remove').value };
  if (f === 'unsharp')    body = { radius: +$('s-unsharp-r').value, percent: +$('s-unsharp-p').value, threshold: 3 };
  await pushHistory();
  const data = await api(`restore/${f}`, body);
  if (data) await snapshotRestoreBase(); // update base setelah commit
}

// Filter selector
document.querySelectorAll('.restore-filter-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    // revert preview dulu ke base sebelum ganti filter
    if (S.hasImage) await api('restore/revert', null, 'POST');

    document.querySelectorAll('.restore-filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.restore-params').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    activeRestoreFilter = btn.dataset.filter;
    $('rp-' + activeRestoreFilter).classList.add('active');

    await snapshotRestoreBase();
    previewRestore();
  });
});

// Masuk tab restoration → snapshot
document.querySelector('[data-tab="restoration"]').addEventListener('click', async () => {
  await snapshotRestoreBase();
  previewRestore();
});

// Slider listeners — semua trigger previewRestore
['s-gauss','s-median','s-mean','s-sp-remove','s-unsharp-r','s-unsharp-p'].forEach(id => {
  const el = $(id);
  if (el) el.addEventListener('input', previewRestore);
});

// Terapkan
$('btn-restore-apply').addEventListener('click', commitRestore);

// Preview ulang (revert ke base lalu preview)
$('btn-restore-preview').addEventListener('click', async () => {
  if (!S.hasImage) return;
  await api('restore/revert', null, 'POST');
  await snapshotRestoreBase();
  previewRestore();
});

// Add noise
$('btn-sp-add').addEventListener('click', () => {
  const amount = +$('s-sp-add').value / 100;
  pushHistory().then(() => api('restore/add_noise', { amount }));
});