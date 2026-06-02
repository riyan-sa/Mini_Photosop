"""
Image Restoration Module
Fitur: Gaussian blur, Median filter, Noise removal (salt & pepper)
Teknis: spatial filtering & kernel convolution (manual + PIL/scipy)
"""

import numpy as np
from PIL import Image, ImageFilter


class ImageRestorer:

    # ─── Gaussian Blur ────────────────────────────────────────
    @staticmethod
    def gaussian_blur(img: Image.Image, radius: float = 2.0) -> Image.Image:
        """
        Gaussian blur via PIL (wrapper kernel convolution).
        radius: 0.5 – 10.0
        """
        return img.filter(ImageFilter.GaussianBlur(radius=max(0.1, radius)))

    # ─── Median Filter ────────────────────────────────────────
    @staticmethod
    def median_filter(img: Image.Image, size: int = 3) -> Image.Image:
        """
        Median filter — efektif untuk noise salt & pepper.
        size: ukuran kernel (3, 5, 7) — harus ganjil
        """
        size = max(3, size if size % 2 == 1 else size + 1)
        return img.filter(ImageFilter.MedianFilter(size=size))

    # ─── Salt & Pepper Noise Removal ─────────────────────────
    @staticmethod
    def remove_salt_pepper(img: Image.Image, strength: int = 2) -> Image.Image:
        """
        Hapus salt & pepper noise dengan adaptive median filter.
        strength: 1 (ringan) – 3 (kuat), menentukan ukuran kernel (3,5,7)
        """
        size = 2 * strength + 1   # 3, 5, atau 7
        size = min(size, 7)
        return img.filter(ImageFilter.MedianFilter(size=size))

    # ─── Add Salt & Pepper (untuk demo) ──────────────────────
    @staticmethod
    def add_salt_pepper_noise(img: Image.Image, amount: float = 0.05) -> Image.Image:
        """
        Tambahkan noise salt & pepper ke gambar (untuk testing).
        amount: 0.01 – 0.2 (proporsi piksel yang di-noise)
        """
        arr = np.array(img.convert("RGB"), dtype=np.uint8).copy()
        total = arr.shape[0] * arr.shape[1]
        n = int(total * amount)

        # Salt (putih)
        coords = [np.random.randint(0, d, n) for d in arr.shape[:2]]
        arr[coords[0], coords[1]] = 255

        # Pepper (hitam)
        coords = [np.random.randint(0, d, n) for d in arr.shape[:2]]
        arr[coords[0], coords[1]] = 0

        return Image.fromarray(arr)

    # ─── Mean Filter (manual kernel convolution) ──────────────
    @staticmethod
    def mean_filter(img: Image.Image, size: int = 3) -> Image.Image:
        """
        Mean/average filter — kernel konvolusi manual pakai numpy.
        size: 3 atau 5
        """
        size = max(3, size if size % 2 == 1 else size + 1)
        kernel_val = 1.0 / (size * size)
        kernel = ImageFilter.Kernel(
            size=size,
            kernel=[int(kernel_val * 256)] * (size * size),
            scale=256,
            offset=0,
        )
        return img.filter(kernel)

    # ─── Sharpening via Unsharp Mask ─────────────────────────
    @staticmethod
    def unsharp_mask(img: Image.Image, radius: float = 2.0,
                     percent: int = 150, threshold: int = 3) -> Image.Image:
        """
        Unsharp mask — restoration dengan mempertajam tepi.
        radius: 1–5, percent: 50–300, threshold: 0–10
        """
        return img.filter(ImageFilter.UnsharpMask(
            radius=radius, percent=percent, threshold=threshold
        ))