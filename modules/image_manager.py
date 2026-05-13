"""
Image Manager Module
Handles: load, save, reset, dan state gambar (original vs current)
"""

from PIL import Image
import numpy as np
import copy


class ImageManager:
    def __init__(self):
        self.original_image: Image.Image | None = None  # gambar asli, tidak pernah diubah
        self.current_image: Image.Image | None = None   # gambar yang sedang diedit
        self.file_path: str | None = None

        self.SUPPORTED_FORMATS = [
            ("Image Files", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif"),
            ("JPEG", "*.jpg *.jpeg"),
            ("PNG", "*.png"),
            ("BMP", "*.bmp"),
            ("All Files", "*.*"),
        ]

    # ─── Load ────────────────────────────────────────────────
    def load_image(self, file_path: str) -> Image.Image:
        """Load gambar dari file. Return PIL Image."""
        img = Image.open(file_path).convert("RGB")
        self.original_image = img.copy()
        self.current_image = img.copy()
        self.file_path = file_path
        return self.current_image

    # ─── Save ────────────────────────────────────────────────
    def save_image(self, file_path: str) -> bool:
        """Simpan current_image ke file. Return True jika berhasil."""
        if self.current_image is None:
            return False
        self.current_image.save(file_path)
        return True

    # ─── Reset ───────────────────────────────────────────────
    def reset_image(self) -> Image.Image | None:
        """Kembalikan gambar ke kondisi original (sebelum semua edit)."""
        if self.original_image is None:
            return None
        self.current_image = self.original_image.copy()
        return self.current_image

    # ─── Update current ──────────────────────────────────────
    def update_current(self, img: Image.Image):
        """Dipakai oleh modul lain (enhancement, filter, dll) untuk update gambar."""
        self.current_image = img.copy()

    # ─── Helpers ─────────────────────────────────────────────
    def has_image(self) -> bool:
        return self.current_image is not None

    def get_info(self) -> dict:
        """Return info gambar: ukuran, mode, path."""
        if not self.has_image():
            return {}
        w, h = self.current_image.size
        return {
            "width": w,
            "height": h,
            "mode": self.current_image.mode,
            "file_path": self.file_path or "-",
        }
