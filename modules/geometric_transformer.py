"""
Geometric Transformation Module
Fitur: rotate, flip, crop, resize, translation
Teknis: affine matrix transformation + interpolasi
"""

from PIL import Image
import numpy as np


class GeometricTransformer:

    # ─── Rotate ──────────────────────────────────────────────
    @staticmethod
    def rotate(img: Image.Image, angle: float, expand: bool = True) -> Image.Image:
        """
        Rotasi gambar searah jarum jam.
        angle: 0–360 derajat
        expand: True = canvas ikut membesar agar gambar tidak terpotong
        """
        return img.rotate(-angle, expand=expand, resample=Image.BICUBIC)

    # ─── Flip ────────────────────────────────────────────────
    @staticmethod
    def flip_horizontal(img: Image.Image) -> Image.Image:
        return img.transpose(Image.FLIP_LEFT_RIGHT)

    @staticmethod
    def flip_vertical(img: Image.Image) -> Image.Image:
        return img.transpose(Image.FLIP_TOP_BOTTOM)

    # ─── Crop ────────────────────────────────────────────────
    @staticmethod
    def crop(img: Image.Image, left: int, top: int, right: int, bottom: int) -> Image.Image:
        """
        Crop area (left, top, right, bottom) dalam piksel.
        Koordinat otomatis di-clamp ke ukuran gambar.
        """
        w, h = img.size
        left   = max(0, min(left,   w))
        top    = max(0, min(top,    h))
        right  = max(0, min(right,  w))
        bottom = max(0, min(bottom, h))

        if right <= left or bottom <= top:
            return img.copy()

        return img.crop((left, top, right, bottom))

    # ─── Resize ──────────────────────────────────────────────
    @staticmethod
    def resize(img: Image.Image, width: int, height: int,
               interpolation: str = "bilinear") -> Image.Image:
        """
        Resize ke ukuran (width x height).
        interpolation: 'nearest' atau 'bilinear'
        """
        resample = Image.NEAREST if interpolation == "nearest" else Image.BILINEAR
        return img.resize((width, height), resample=resample)

    @staticmethod
    def resize_by_scale(img: Image.Image, scale: float,
                        interpolation: str = "bilinear") -> Image.Image:
        """
        Resize berdasarkan skala (0.1 – 4.0).
        """
        w, h = img.size
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return GeometricTransformer.resize(img, new_w, new_h, interpolation)

    # ─── Translation ─────────────────────────────────────────
    @staticmethod
    def translate(img: Image.Image, tx: int, ty: int) -> Image.Image:
        """
        Geser gambar tx piksel ke kanan dan ty piksel ke bawah.
        Area kosong diisi hitam.
        Menggunakan affine matrix: [[1,0,-tx],[0,1,-ty]]
        """
        # PIL affine: (a,b,c,d,e,f) → x' = ax+by+c, y' = dx+ey+f
        # Untuk translasi: a=1,b=0,c=-tx, d=0,e=1,f=-ty
        return img.transform(
            img.size,
            Image.AFFINE,
            (1, 0, -tx, 0, 1, -ty),
            resample=Image.BILINEAR,
        )