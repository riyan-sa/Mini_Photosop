"""
Image Router — v8 (Ultimate Architecture - Fully Repaired & Tested)
Optimized for Draggable Popup Windows, Realtime Floating Histogram, 
Tab Segmentation (Feature 7) & Smooth Dynamic History System.
"""

import io
import base64
import copy
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Pastikan registrasi path selesai sebelum memanggil folder modules
from modules.image_manager import ImageManager
from modules.image_enhancer import ImageEnhancer
from modules.geometric_transformer import GeometricTransformer
from modules.image_restorer import ImageRestorer
from modules.color_processor import ColorProcessor
from modules.segmenter import ImageSegmenter
from modules.compressor import ImageCompressor
from modules.binary_edge_processor import BinaryEdgeProcessor

router  = APIRouter()
manager = ImageManager()

# ── Global States ─────────────────────────────────────────────
geo_state = dict(flip_h=False, flip_v=False, crop=None, scale=1.0, rotate=0.0, tx=0, ty=0)
enh_state = dict(brightness=1.0, contrast=1.0, sharpen=1.0, blur=0.0)

undo_history = []
redo_history = []
MAX_HISTORY = 20
_restore_base = None

# ── Pydantic Schemas Input Validation ─────────────────────────
class EnhanceParams(BaseModel):
    brightness: float = 1.0
    contrast:   float = 1.0
    sharpen:    float = 1.0
    blur:       float = 0.0

class GeoCommitParams(BaseModel):
    flip_h:  bool             = False
    flip_v:  bool             = False
    crop:    list | None      = None
    scale:   float            = 1.0
    rotate:  float            = 0.0
    tx:      int              = 0
    ty:      int              = 0

class CropParams(BaseModel): 
    left: int; top: int; right: int; bottom: int

class ResizeParams(BaseModel): 
    width: int; height: int

class SplitChannelParams(BaseModel): 
    channel: str

class HSVParams(BaseModel): 
    hue: float; saturation: float; lightness: float

class ThreshParams(BaseModel): 
    threshold: int

class EdgeParams(BaseModel): 
    low: int; high: int

class KmeansParams(BaseModel): 
    clusters: int

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

# ── System core Helpers ───────────────────────────────────────────
def img_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()

def compose_geo(base: Image.Image) -> Image.Image:
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
    return {
        "message": msg, 
        "image": img_to_b64(final_img), 
        "info": info, 
        "geo_state": dict(geo_state), 
        "enh_state": dict(enh_state)
    }

def reset_states():
    global geo_state, enh_state
    geo_state = dict(flip_h=False, flip_v=False, crop=None, scale=1.0, rotate=0.0, tx=0, ty=0)
    enh_state = dict(brightness=1.0, contrast=1.0, sharpen=1.0, blur=0.0)

def _save_to_history_stack():
    global undo_history, redo_history
    undo_history.append((
        copy.deepcopy(geo_state), 
        copy.deepcopy(enh_state), 
        manager.original_image.copy() if manager.original_image else None
    ))
    if len(undo_history) > MAX_HISTORY: 
        undo_history.pop(0)
    redo_history.clear()

def commit_restoration(img: Image.Image, msg: str) -> dict:
    """Mengunci hasil warnal/efek destuktif tanpa merusak panel BEFORE asli."""
    _save_to_history_stack()
    manager.original_image = img.copy()
    manager.update_current(img)
    
    global geo_state, enh_state
    geo_state = dict(flip_h=False, flip_v=False, crop=None, scale=1.0, rotate=0.0, tx=0, ty=0)
    enh_state = dict(brightness=1.0, contrast=1.0, sharpen=1.0, blur=0.0)
    
    info = manager.get_info()
    return {
        "message": msg, 
        "image": img_to_b64(img), 
        "info": info, 
        "geo_state": dict(geo_state), 
        "enh_state": dict(enh_state)
    }
# ── Core Action Endpoints ───────────────────────────────────────────
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
    
    global undo_history, redo_history
    undo_history.clear()
    redo_history.clear()
    
    w, h = img.size
    return {
        "message": f"'{file.filename}' diupload.", 
        "image": img_to_b64(img), 
        "info": {"width": w, "height": h, "mode": img.mode, "file_path": file.filename}
    }

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
    return commit_restoration(eq_img, "Histogram equalization diterapkan.")

@router.get("/reset")
def reset_image():
    img = manager.reset_image()
    if img is None: raise HTTPException(400, "Belum ada gambar.")
    reset_states()
    global undo_history, redo_history
    undo_history.clear()
    redo_history.clear()
    w, h = img.size
    return {"message": "Reset ke gambar awal.", "image": img_to_b64(img), "info": {"width": w, "height": h, "mode": img.mode}}

@router.get("/download")
def download_image():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    buf = io.BytesIO()
    manager.current_image.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png", headers={"Content-Disposition": "attachment; filename=result.png"})

@router.post("/geo_commit")
def geo_commit(params: GeoCommitParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    geo_state.update(params.dict(exclude_unset=True))
    return rebuild("Geometric diterapkan.")

@router.post("/crop")
def crop_image(params: CropParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    geo_img = compose_geo(manager.original_image)
    w, h = geo_img.size
    l = max(0, min(params.left,  w)); t = max(0, min(params.top,   h))
    r = max(0, min(params.right, w)); b = max(0, min(params.bottom,h))
    
    # Potong gambar dari hasil komposisi geometri saat ini
    cropped_img = GeometricTransformer.crop(geo_img, l, t, r, b)
    
    # Simpan hasil potong ke original_image secara permanen (destructive + mendukung Undo/Redo)
    return commit_restoration(cropped_img, "Crop diterapkan.")

@router.post("/resize")
def resize_image(params: ResizeParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    geo_img = compose_geo(manager.original_image)
    img = GeometricTransformer.resize(geo_img, params.width, params.height)
    return commit_restoration(img, f"Resize ke {params.width}×{params.height}.")

# ── Dynamic History Stack Controller (Undo/Redo Engine) ───────────
@router.post("/push_history")
def push_history_endpoint():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    _save_to_history_stack()
    return {"message": "History saved."}

@router.post("/undo")
def undo():
    global geo_state, enh_state, redo_history, undo_history
    if not undo_history: 
        raise HTTPException(400, "Tidak ada riwayat untuk di-undo.")
    
    # Masukkan state saat ini ke Redo sebelum mundur ke belakang
    redo_history.append((
        copy.deepcopy(geo_state), 
        copy.deepcopy(enh_state), 
        manager.original_image.copy() if manager.original_image else None
    ))
    
    # Ambil snapshot masa lalu dari stack Undo
    geo_snap, enh_snap, orig_snap = undo_history.pop()
    
    # Kembalikan semua state dan objek gambar induknya
    geo_state.update(geo_snap)
    enh_state.update(enh_snap)
    if orig_snap:
        manager.original_image = orig_snap.copy()
    
    # Bangun ulang visual asli masa lalu tersebut
    res = rebuild("Undo berhasil.")
    res.update({"enh_state": dict(enh_state), "geo_state": dict(geo_state)})
    return res

@router.post("/redo")
def redo():
    global geo_state, enh_state, redo_history, undo_history
    if not redo_history: 
        raise HTTPException(400, "Tidak ada riwayat untuk di-redo.")
    
    # Masukkan state saat ini ke Undo sebelum maju ke depan
    undo_history.append((
        copy.deepcopy(geo_state), 
        copy.deepcopy(enh_state), 
        manager.original_image.copy() if manager.original_image else None
    ))
    
    # Ambil snapshot masa depan dari stack Redo
    geo_snap, enh_snap, orig_snap = redo_history.pop()
    
    # Aplikasikan kembali
    geo_state.update(geo_snap)
    enh_state.update(enh_snap)
    if orig_snap:
        manager.original_image = orig_snap.copy()
        
    # Bangun ulang visualnya
    res = rebuild("Redo berhasil.")
    res.update({"enh_state": dict(enh_state), "geo_state": dict(geo_state)})
    return res

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
    gray = np.array(img.convert("L"))
    hist_gray, _ = np.histogram(gray.flatten(), bins=256, range=(0,256))
    result['gray'] = hist_gray.tolist()
    return result

# ── Color Processing Endpoints ────────────────────────────────
@router.post("/color/grayscale")
def color_grayscale():
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ColorProcessor.to_grayscale(manager.current_image)
    return commit_restoration(img, "Grayscale diterapkan.")

@router.post("/color/split")
def color_split(params: SplitChannelParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ColorProcessor.split_channel(manager.current_image, params.channel)
    return commit_restoration(img, f"Channel {params.channel} diisolasi.")

@router.post("/color/hsv")
def color_hsv(params: HSVParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ColorProcessor.adjust_hsv(manager.current_image, params.hue, params.saturation, params.lightness)
    return commit_restoration(img, "Hue/Saturation diterapkan.")

@router.post("/color/preview/hsv")
def preview_hsv(params: HSVParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ColorProcessor.adjust_hsv(_restore_base, params.hue, params.saturation, params.lightness)
    manager.update_current(img)
    return {"message": "Preview HSV.", "image": img_to_b64(img), "info": manager.get_info()}

# ── Fitur 7: Image Segmentation Endpoints ──────────────────────
@router.post("/segment/threshold")
def segment_threshold(params: ThreshParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.threshold_segment(manager.current_image, params.threshold)
    return commit_restoration(img, f"Thresholding biner ({params.threshold}) diterapkan.")

@router.post("/segment/preview/threshold")
def preview_threshold(params: ThreshParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.threshold_segment(_restore_base, params.threshold)
    manager.update_current(img)
    return {"image": img_to_b64(img)}

@router.post("/segment/edge")
def segment_edge(params: EdgeParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.edge_segment(manager.current_image, params.low, params.high)
    return commit_restoration(img, "Edge-based Canny diterapkan.")

@router.post("/segment/preview/edge")
def preview_edge(params: EdgeParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.edge_segment(_restore_base, params.low, params.high)
    manager.update_current(img)
    return {"image": img_to_b64(img)}

@router.post("/segment/kmeans")
def segment_kmeans(params: KmeansParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.region_kmeans_segment(manager.current_image, params.clusters)
    return commit_restoration(img, f"K-Means region {params.clusters} clusters diterapkan.")

@router.post("/segment/preview/kmeans")
def preview_kmeans(params: KmeansParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageSegmenter.region_kmeans_segment(_restore_base, params.clusters)
    manager.update_current(img) 
    return {"image": img_to_b64(img)}

# ── Image Restoration Endpoints ─────────────────────────────────
@router.post("/restore/snapshot")
def restore_snapshot():
    global _restore_base
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    _restore_base = manager.current_image.copy()
    return {"ok": True}

@router.post("/restore/revert")
def restore_revert():
    global _restore_base
    if _restore_base is None: return {"ok": True}
    manager.update_current(_restore_base.copy())
    global geo_state
    geo_state.update(dict(flip_h=False, flip_v=False, crop=None, scale=1.0, rotate=0.0, tx=0, ty=0))
    return rebuild("Revert ke base.")

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

@router.post("/restore/preview/gaussian")
def preview_gaussian(params: GaussianParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.gaussian_blur(_restore_base, params.radius)
    manager.update_current(img)
    return {"message": "Preview.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/median")
def preview_median(params: MedianParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.median_filter(_restore_base, params.size)
    manager.update_current(img)
    return {"message": "Preview.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/mean")
def preview_mean(params: MeanParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.mean_filter(_restore_base, params.size)
    manager.update_current(img)
    return {"message": "Preview.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/saltpepper")
def preview_saltpepper(params: SaltPepperParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.remove_salt_pepper(_restore_base, params.strength)
    manager.update_current(img)
    return {"message": "Preview.", "image": img_to_b64(img), "info": manager.get_info()}

@router.post("/restore/preview/unsharp")
def preview_unsharp(params: UnsharpParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = ImageRestorer.unsharp_mask(_restore_base, params.radius, params.percent, params.threshold)
    manager.update_current(img)
    return {"message": "Preview.", "image": img_to_b64(img), "info": manager.get_info()}


# ═══════════════════════════════════════════════════════════
# FITUR 8: IMAGE COMPRESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════
class CompressParams(BaseModel):
    quality: int

@router.post("/compress/preview")
def compress_preview(params: CompressParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    # Gunakan _restore_base sebagai landasan preview agar pergeseran slider bersifat real-time & non-destructive
    global _restore_base
    if _restore_base is None:
        _restore_base = manager.current_image.copy()
        
    comp_img, bytes_size, ratio = ImageCompressor.compress_jpeg_simulation(_restore_base, params.quality)
    manager.update_current(comp_img)
    
    # Konversi ukuran bytes menjadi KB yang mudah dibaca manusia
    size_kb = round(bytes_size / 1024, 2)
    return {
        "image": img_to_b64(comp_img),
        "size_kb": f"{size_kb} KB",
        "ratio": f"{ratio}%"
    }

@router.post("/compress/save")
def compress_save(params: CompressParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    global _restore_base
    base_img = _restore_base if _restore_base else manager.current_image.copy()
    
    comp_img, _, _ = ImageCompressor.compress_jpeg_simulation(base_img, params.quality)
    
    # Kunci hasilnya ke sistem Undo/Redo history
    return commit_restoration(comp_img, f"Kompresi JPEG kualitas {params.quality}% disimpan.")

# ═══════════════════════════════════════════════════════════
# FITUR 5: BINARY & EDGE PROCESSING ENDPOINTS
# ═══════════════════════════════════════════════════════════
class EdgeParams(BaseModel):
    method: str
    p1: int = 50
    p2: int = 150

class MorphParams(BaseModel):
    operation: str
    size: int = 3

@router.post("/binary/threshold")
def binary_threshold_apply(params: ThreshParams): # Menggunakan ThreshParams yang sudah ada
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.apply_threshold(manager.current_image, params.threshold)
    return commit_restoration(img, f"Thresholding biner ({params.threshold}) sukses.")

@router.post("/binary/preview/threshold")
def binary_threshold_preview(params: ThreshParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.apply_threshold(_restore_base, params.threshold)
    manager.update_current(img)
    return {"image": img_to_b64(img)}

@router.post("/binary/edge")
def binary_edge_apply(params: EdgeParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.edge_detection(manager.current_image, params.method, params.p1, params.p2)
    return commit_restoration(img, f"Edge Detection {params.method.upper()} sukses.")

@router.post("/binary/preview/edge")
def binary_edge_preview(params: EdgeParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.edge_detection(_restore_base, params.method, params.p1, params.p2)
    manager.update_current(img)
    return {"image": img_to_b64(img)}

@router.post("/binary/morph")
def binary_morph_apply(params: MorphParams):
    if not manager.has_image(): raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.morphology(manager.current_image, params.operation, params.size)
    return commit_restoration(img, f"Morfologi {params.operation} size {params.size} sukses.")

@router.post("/binary/preview/morph")
def binary_morph_preview(params: MorphParams):
    if not manager.has_image() or _restore_base is None: raise HTTPException(400, "Belum ada gambar.")
    img = BinaryEdgeProcessor.morphology(_restore_base, params.operation, params.size)
    manager.update_current(img)
    return {"image": img_to_b64(img)}