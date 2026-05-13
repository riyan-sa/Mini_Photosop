"""
Image Enhancement Module
Fitur: brightness, contrast, sharpening, smoothing/blur, histogram equalization
"""

from PIL import Image, ImageEnhance, ImageFilter
import numpy as np


class ImageEnhancer:

    # ─── Brightness ──────────────────────────────────────────
    @staticmethod
    def adjust_brightness(img: Image.Image, factor: float) -> Image.Image:
        """
        factor: 0.0 = gelap total, 1.0 = normal, 2.0 = 2x lebih terang
        """
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(factor)

    # ─── Contrast ────────────────────────────────────────────
    @staticmethod
    def adjust_contrast(img: Image.Image, factor: float) -> Image.Image:
        """
        factor: 0.0 = abu-abu datar, 1.0 = normal, 2.0 = kontras tinggi
        """
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(factor)

    # ─── Sharpening ──────────────────────────────────────────
    @staticmethod
    def sharpen(img: Image.Image, factor: float) -> Image.Image:
        """
        factor: 1.0 = normal, 2.0 = tajam, hingga 5.0
        """
        enhancer = ImageEnhance.Sharpness(img)
        return enhancer.enhance(factor)

    # ─── Smoothing / Blur ────────────────────────────────────
    @staticmethod
    def blur(img: Image.Image, radius: float) -> Image.Image:
        """
        radius: 0 = tidak blur, makin besar makin blur (max ~10)
        """
        if radius <= 0:
            return img.copy()
        return img.filter(ImageFilter.GaussianBlur(radius=radius))

    # ─── Histogram Equalization ──────────────────────────────
    @staticmethod
    def histogram_equalization(img: Image.Image) -> Image.Image:
        """
        Histogram equalization pada channel grayscale (luminance).
        Gambar RGB tetap berwarna, hanya kecerahan yang diratakan.
        """
        img_array = np.array(img.convert("RGB"))

        # Konversi ke YCbCr, equalize channel Y (luminance) saja
        img_ycbcr = img.convert("YCbCr")
        y, cb, cr = img_ycbcr.split()

        y_array = np.array(y)

        # Hitung histogram & CDF
        hist, bins = np.histogram(y_array.flatten(), bins=256, range=(0, 256))
        cdf = hist.cumsum()
        cdf_min = cdf[cdf > 0].min()
        total_pixels = y_array.size

        # Rumus equalization
        lut = np.round(
            (cdf - cdf_min) / (total_pixels - cdf_min) * 255
        ).astype(np.uint8)

        y_eq = Image.fromarray(lut[y_array])
        result = Image.merge("YCbCr", (y_eq, cb, cr)).convert("RGB")
        return result
