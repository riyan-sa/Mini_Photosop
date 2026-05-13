"""
Image Router
Endpoints:
  POST /api/upload          — upload gambar
  POST /api/enhance         — apply enhancement
  POST /api/histeq          — histogram equalization
  GET  /api/reset           — reset ke original
"""

import io
import base64
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.image_manager import ImageManager
from modules.image_enhancer import ImageEnhancer

router = APIRouter()

# Session sederhana — satu instance (cukup untuk localhost single-user)
manager = ImageManager()


# ─── Helper ──────────────────────────────────────────────────
def img_to_base64(img: Image.Image) -> str:
    """Konversi PIL Image → base64 string untuk dikirim ke frontend."""
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def image_response(img: Image.Image, message: str = "OK") -> dict:
    info = manager.get_info()
    return {
        "message": message,
        "image": img_to_base64(img),
        "info": info,
    }


# ─── Upload ──────────────────────────────────────────────────
@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File harus berupa gambar.")

    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")

    # Simpan ke manager manual (bypass file path)
    manager.original_image = img.copy()
    manager.current_image  = img.copy()
    manager.file_path      = file.filename

    return image_response(img, f"Gambar '{file.filename}' berhasil diupload.")


# ─── Enhance ─────────────────────────────────────────────────
class EnhanceParams(BaseModel):
    brightness: float = 1.0   # 0.0 – 2.0
    contrast:   float = 1.0
    sharpen:    float = 1.0
    blur:       float = 0.0   # radius


@router.post("/enhance")
def enhance_image(params: EnhanceParams):
    if not manager.has_image():
        raise HTTPException(400, "Belum ada gambar. Upload dulu.")

    img = manager.original_image.copy()
    img = ImageEnhancer.adjust_brightness(img, params.brightness)
    img = ImageEnhancer.adjust_contrast(img, params.contrast)
    img = ImageEnhancer.sharpen(img, params.sharpen)
    img = ImageEnhancer.blur(img, params.blur)

    manager.update_current(img)
    return image_response(img, "Enhancement diterapkan.")


# ─── Histogram EQ ────────────────────────────────────────────
@router.post("/histeq")
def histeq():
    if not manager.has_image():
        raise HTTPException(400, "Belum ada gambar.")

    img = ImageEnhancer.histogram_equalization(manager.current_image)
    manager.update_current(img)
    return image_response(img, "Histogram equalization diterapkan.")


# ─── Reset ───────────────────────────────────────────────────
@router.get("/reset")
def reset_image():
    img = manager.reset_image()
    if img is None:
        raise HTTPException(400, "Belum ada gambar.")
    return image_response(img, "Gambar direset ke original.")


# ─── Download ────────────────────────────────────────────────
@router.get("/download")
def download_image():
    if not manager.has_image():
        raise HTTPException(400, "Belum ada gambar.")

    buffer = io.BytesIO()
    manager.current_image.save(buffer, format="PNG")
    buffer.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buffer,
        media_type="image/png",
        headers={"Content-Disposition": "attachment; filename=result.png"},
    )
