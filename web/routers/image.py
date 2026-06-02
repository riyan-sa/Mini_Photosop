"""
Image Router — v3
Geo state pipeline (compose order):
  original → flip_h → flip_v → crop → scale → rotate → translate
  lalu di-stack dengan enhancement di atas hasilnya.
"""

import io, base64
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.image_manager import ImageManager
from modules.image_enhancer import ImageEnhancer
from modules.geometric_transformer import GeometricTransformer

router  = APIRouter()
manager = ImageManager()

# ── Geo state ─────────────────────────────────────────────────
geo_state = dict(
    flip_h=False, flip_v=False,
    crop=None,          # (left, top, right, bottom) piksel, atau None
    scale=1.0,
    rotate=0.0,
    tx=0, ty=0,
)

# ── Enhancement state ─────────────────────────────────────────
enh_state = dict(brightness=1.0, contrast=1.0, sharpen=1.0, blur=0.0)

# ── Helpers ───────────────────────────────────────────────────
def img_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def compose_geo(base: Image.Image) -> Image.Image:
    """Terapkan semua geo ops secara berurutan dari original."""
    img = base.copy()
    if geo_state["flip_h"]: img = GeometricTransformer.flip_horizontal(img)
    if geo_state["flip_v"]: img = GeometricTransformer.flip_vertical(img)
    if geo_state["crop"]:
        l, t, r, b = geo_state["crop"]
        img = GeometricTransformer.crop(img, l, t, r, b)
    if geo_state["scale"] != 1.0:
        img = GeometricTransformer.resize_by_scale(img, geo_state["scale"])
    if geo_state["rotate"] != 0.0:
        img = GeometricTransformer.rotate(img, geo_state["rotate"], expand=True)
    if geo_state["tx"] != 0 or geo_state["ty"] != 0:
        img = GeometricTransformer.translate(img, geo_state["tx"], geo_state["ty"])
    return img

def compose_enh(img: Image.Image) -> Image.Image:
    img = ImageEnhancer.adjust_brightness(img, enh_state["brightness"])
    img = ImageEnhancer.adjust_contrast(img,   enh_state["contrast"])
    img = ImageEnhancer.sharpen(img,            enh_state["sharpen"])
    img = ImageEnhancer.blur(img,               enh_state["blur"])
    return img

def rebuild(msg: str) -> dict:
    geo_img   = compose_geo(manager.original_image)
    final_img = compose_enh(geo_img)
    manager.update_current(final_img)
    info = manager.get_info()
    return {"message": msg, "image": img_to_b64(final_img), "info": info}

def reset_states():
    global geo_state, enh_state
    geo_state = dict(flip_h=False, flip_v=False, crop=None,
                     scale=1.0, rotate=0.0, tx=0, ty=0)
    enh_state = dict(brightness=1.0, contrast=1.0, sharpen=1.0, blur=0.0)

# ── Upload ────────────────────────────────────────────────────
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File harus berupa gambar.")
    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")
    manager.original_image = img.copy()
    manager.current_image  = img.copy()
    manager.file_path      = file.filename
    reset_states()
    w, h = img.size
    return {"message": f"'{file.filename}' diupload.",
            "image": img_to_b64(img),
            "info": {"width": w, "height": h, "mode": img.mode, "file_path": file.filename}}

# ── Enhancement ───────────────────────────────────────────────
class EnhanceParams(BaseModel):
    brightness: float = 1.0
    contrast:   float = 1.0
    sharpen:    float = 1.0
    blur:       float = 0.0

@router.post("/enhance")
def enhance_image(params: EnhanceParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    enh_state.update(params.dict())
    return rebuild("Enhancement diterapkan.")

@router.post("/histeq")
def histeq():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    geo_img = compose_geo(manager.original_image)
    eq_img  = ImageEnhancer.histogram_equalization(geo_img)
    # simpan hasilnya sebagai original baru agar pipeline tetap konsisten
    manager.original_image = eq_img.copy()
    geo_state.update(dict(flip_h=False, flip_v=False, crop=None,
                          scale=1.0, rotate=0.0, tx=0, ty=0))
    return rebuild("Histogram equalization diterapkan.")

# ── Reset ─────────────────────────────────────────────────────
@router.get("/reset")
def reset_image():
    img = manager.reset_image()
    if img is None: raise HTTPException(400, "Belum ada gambar.")
    reset_states()
    w, h = img.size
    return {"message": "Reset ke gambar awal.",
            "image": img_to_b64(img),
            "info": {"width": w, "height": h, "mode": img.mode}}

# ── Download ──────────────────────────────────────────────────
@router.get("/download")
def download_image():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    buf = io.BytesIO()
    manager.current_image.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=result.png"})

# ── Geo state endpoint — commit semua geo sekaligus ───────────
class GeoCommitParams(BaseModel):
    flip_h:  bool             = False
    flip_v:  bool             = False
    crop:    list | None      = None   # [l,t,r,b] atau null
    scale:   float            = 1.0
    rotate:  float            = 0.0
    tx:      int              = 0
    ty:      int              = 0

@router.post("/geo_commit")
def geo_commit(params: GeoCommitParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    geo_state["flip_h"]  = params.flip_h
    geo_state["flip_v"]  = params.flip_v
    geo_state["crop"]    = tuple(params.crop) if params.crop else None
    geo_state["scale"]   = params.scale
    geo_state["rotate"]  = params.rotate
    geo_state["tx"]      = params.tx
    geo_state["ty"]      = params.ty
    return rebuild("Geometric diterapkan.")

# ── Crop apply (khusus, karena koordinat dalam piksel geo_img) ─
class CropParams(BaseModel):
    left: int; top: int; right: int; bottom: int

@router.post("/crop")
def crop_image(params: CropParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    # crop diterapkan setelah flip, sebelum scale/rotate/translate
    # hitung ukuran geo_img sampai tahap flip saja
    img = manager.original_image.copy()
    if geo_state["flip_h"]: img = GeometricTransformer.flip_horizontal(img)
    if geo_state["flip_v"]: img = GeometricTransformer.flip_vertical(img)
    w, h = img.size
    l = max(0, min(params.left,  w))
    t = max(0, min(params.top,   h))
    r = max(0, min(params.right, w))
    b = max(0, min(params.bottom,h))
    geo_state["crop"] = (l, t, r, b)
    return rebuild("Crop diterapkan.")

# ── Flip (toggle via geo_commit) — kept for direct call ───────
@router.post("/flip")
def flip_image(params: BaseModel):
    pass  # handled via geo_commit

# ── Resize ────────────────────────────────────────────────────
class ResizeParams(BaseModel):
    width: int; height: int

@router.post("/resize")
def resize_image(params: ResizeParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    from modules.geometric_transformer import GeometricTransformer
    geo_img = compose_geo(manager.original_image)
    img = GeometricTransformer.resize(geo_img, params.width, params.height)
    # update original so pipeline stays consistent
    manager.original_image = img.copy()
    geo_state.update(dict(flip_h=False,flip_v=False,crop=None,scale=1.0,rotate=0.0,tx=0,ty=0))
    return rebuild(f"Resize ke {params.width}×{params.height}.")

# ── Undo ──────────────────────────────────────────────────────
history = []   # list of (geo_state_snapshot, enh_state_snapshot, original_snapshot)
MAX_HISTORY = 20

def push_history():
    import copy
    history.append((
        copy.deepcopy(geo_state),
        copy.deepcopy(enh_state),
        manager.original_image.copy(),
    ))
    if len(history) > MAX_HISTORY:
        history.pop(0)

@router.post("/push_history")
def push_history_endpoint():
    """Dipanggil frontend sebelum setiap operasi destructive."""
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    push_history()
    return {"message": "History saved.", "history_len": len(history)}

@router.post("/undo")
def undo():
    if not history: raise HTTPException(400, "Tidak ada riwayat untuk di-undo.")
    global geo_state, enh_state
    geo_snap, enh_snap, orig_snap = history.pop()
    geo_state.update(geo_snap)
    enh_state.update(enh_snap)
    manager.original_image = orig_snap.copy()
    result = rebuild("Undo berhasil.")
    # Include states so frontend can sync UI
    result["enh_state"] = dict(enh_state)
    result["geo_state"] = dict(geo_state)
    return result

# ── Histogram data ─────────────────────────────────────────────
@router.get("/histogram")
def get_histogram():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    import numpy as np
    img = manager.current_image
    arr = np.array(img.convert("RGB"))
    result = {}
    for i, ch in enumerate(['r', 'g', 'b']):
        hist, _ = np.histogram(arr[:,:,i].flatten(), bins=256, range=(0,256))
        result[ch] = hist.tolist()
    # grayscale
    gray = np.array(img.convert("L"))
    hist_gray, _ = np.histogram(gray.flatten(), bins=256, range=(0,256))
    result['gray'] = hist_gray.tolist()
    return result

# ═══════════════════════════════════════════════════════════
# IMAGE RESTORATION
# ═══════════════════════════════════════════════════════════
from modules.image_restorer import ImageRestorer

class GaussianParams(BaseModel):
    radius: float = 2.0

class MedianParams(BaseModel):
    size: int = 3

class SaltPepperParams(BaseModel):
    strength: int = 2

class MeanParams(BaseModel):
    size: int = 3

class UnsharpParams(BaseModel):
    radius:    float = 2.0
    percent:   int   = 150
    threshold: int   = 3

class NoiseParams(BaseModel):
    amount: float = 0.05


def restoration_response(img: Image.Image, msg: str) -> dict:
    geo_img = img.copy()
    # simpan sebagai geo_image baru, reset geo state
    global geo_image
    geo_image = geo_img
    final = compose_enh(geo_img)
    manager.update_current(final)
    return {"message": msg, "image": img_to_b64(final), "info": manager.get_info()}


def commit_restoration(img: Image.Image, msg: str) -> dict:
    """
    Restoration langsung mengubah original_image dan reset geo state,
    supaya hasilnya permanen dan tidak di-override pipeline geo.
    """
    manager.original_image = img.copy()
    geo_state.update(dict(flip_h=False, flip_v=False, crop=None,
                          scale=1.0, rotate=0.0, tx=0, ty=0))
    return rebuild(msg)

@router.post("/restore/gaussian")
def restore_gaussian(params: GaussianParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.gaussian_blur(manager.current_image, params.radius)
    return commit_restoration(img, f"Gaussian blur radius={params.radius}.")

@router.post("/restore/median")
def restore_median(params: MedianParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.median_filter(manager.current_image, params.size)
    return commit_restoration(img, f"Median filter size={params.size}.")

@router.post("/restore/saltpepper")
def restore_saltpepper(params: SaltPepperParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.remove_salt_pepper(manager.current_image, params.strength)
    return commit_restoration(img, f"Salt & pepper removal strength={params.strength}.")

@router.post("/restore/mean")
def restore_mean(params: MeanParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.mean_filter(manager.current_image, params.size)
    return commit_restoration(img, f"Mean filter size={params.size}.")

@router.post("/restore/unsharp")
def restore_unsharp(params: UnsharpParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.unsharp_mask(manager.current_image, params.radius, params.percent, params.threshold)
    return commit_restoration(img, "Unsharp mask diterapkan.")

@router.post("/restore/add_noise")
def add_noise(params: NoiseParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.add_salt_pepper_noise(manager.current_image, params.amount)
    return commit_restoration(img, f"Noise {int(params.amount*100)}% ditambahkan.")

# ── Restoration snapshot/revert/preview ───────────────────────
_restore_base = None   # snapshot sebelum preview

@router.post("/restore/snapshot")
def restore_snapshot():
    """Simpan current_image sebagai base untuk preview restoration."""
    global _restore_base
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    _restore_base = manager.current_image.copy()
    return {"ok": True}

@router.post("/restore/revert")
def restore_revert():
    """Kembalikan gambar ke snapshot base (hapus preview)."""
    global _restore_base
    if _restore_base is None: return {"ok": True}
    manager.original_image = _restore_base.copy()
    geo_state.update(dict(flip_h=False,flip_v=False,crop=None,scale=1.0,rotate=0.0,tx=0,ty=0))
    result = rebuild("Revert ke base.")
    return result

# Preview endpoints — terapkan dari base tanpa commit ke original
@router.post("/restore/preview/gaussian")
def preview_gaussian(params: GaussianParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.gaussian_blur(_restore_base, params.radius)
    manager.update_current(img)
    return {"message": "Preview gaussian.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/median")
def preview_median(params: MedianParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.median_filter(_restore_base, params.size)
    manager.update_current(img)
    return {"message": "Preview median.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/mean")
def preview_mean(params: MeanParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.mean_filter(_restore_base, params.size)
    manager.update_current(img)
    return {"message": "Preview mean.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/saltpepper")
def preview_saltpepper(params: SaltPepperParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.remove_salt_pepper(_restore_base, params.strength)
    manager.update_current(img)
    return {"message": "Preview salt&pepper.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/unsharp")
def preview_unsharp(params: UnsharpParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.unsharp_mask(_restore_base, params.radius, params.percent, params.threshold)
    manager.update_current(img)
    return {"message": "Preview unsharp.", "image": img_to_b64(img), "info": manager.get_info()}