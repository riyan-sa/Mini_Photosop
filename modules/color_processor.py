import numpy as np
from PIL import Image
import matplotlib.colors as mcolors

class ColorProcessor:
    @staticmethod
    def to_grayscale(img: Image.Image) -> Image.Image:
        """Mengubah gambar menjadi Grayscale namun tetap dalam format RGB matrix"""
        return img.convert("L").convert("RGB")

    @staticmethod
    def split_channel(img: Image.Image, channel: str) -> Image.Image:
        """Memisahkan channel warna spesifik (R, G, atau B)"""
        arr = np.array(img.convert("RGB"))
        zeros = np.zeros_like(arr[:, :, 0])
        
        if channel == 'R':
            res = np.stack([arr[:, :, 0], zeros, zeros], axis=-1)
        elif channel == 'G':
            res = np.stack([zeros, arr[:, :, 1], zeros], axis=-1)
        elif channel == 'B':
            res = np.stack([zeros, zeros, arr[:, :, 2]], axis=-1)
        else:
            return img
        return Image.fromarray(res)

    @staticmethod
    def adjust_hsv(img: Image.Image, hue: float, sat: float, val: float) -> Image.Image:
        """
        hue: -180 hingga 180 (derajat perputaran warna)
        sat: -100 hingga 100 (persentase saturasi)
        val: -100 hingga 100 (persentase lightness/kecerahan)
        """
        arr = np.array(img.convert("RGB")) / 255.0
        hsv = mcolors.rgb_to_hsv(arr)
        
        # Geser Hue
        h_shift = hue / 360.0
        hsv[..., 0] = (hsv[..., 0] + h_shift) % 1.0
        
        # Geser Saturation
        s_shift = sat / 100.0
        hsv[..., 1] = np.clip(hsv[..., 1] + s_shift, 0.0, 1.0)
        
        # Geser Value / Lightness
        v_shift = val / 100.0
        hsv[..., 2] = np.clip(hsv[..., 2] + v_shift, 0.0, 1.0)
        
        rgb = mcolors.hsv_to_rgb(hsv)
        res_arr = np.clip(rgb * 255, 0, 255).astype(np.uint8)
        return Image.fromarray(res_arr)