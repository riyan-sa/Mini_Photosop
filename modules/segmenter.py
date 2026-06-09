import cv2
import numpy as np
from PIL import Image

class ImageSegmenter:
    @staticmethod
    def threshold_segment(img: Image.Image, thresh_val: int) -> Image.Image:
        """1. Threshold-based Segmentation (Binarization)"""
        # Konversi ke numpy array grayscale
        arr = np.array(img.convert("L"))
        # Segmentasi biner murni
        _, thresh_arr = cv2.threshold(arr, thresh_val, 255, cv2.THRESH_BINARY)
        return Image.fromarray(thresh_arr).convert("RGB")

    @staticmethod
    def edge_segment(img: Image.Image, low_threshold: int, high_threshold: int) -> Image.Image:
        """2. Edge-based Segmentation (Canny)"""
        arr = np.array(img.convert("L"))
        # Deteksi kontur tepi objek
        edges = cv2.Canny(arr, low_threshold, high_threshold)
        return Image.fromarray(edges).convert("RGB")

    @staticmethod
    def region_kmeans_segment(img: Image.Image, k: int) -> Image.Image:
        """3. Region-based Segmentation (Simple K-Means Clustering)"""
        arr = np.array(img.convert("RGB"))
        # Ubah dimensi array menjadi barisan piksel (M, 3)
        pixel_vals = arr.reshape((-1, 3)).astype(np.float32)
        
        # Kriteria stop untuk K-Means
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        
        # Eksekusi clustering warna dominan
        _, labels, centers = cv2.kmeans(pixel_vals, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Konversi kembali pusat cluster ke format uint8 dan bentuk matriks awal
        centers = np.uint8(centers)
        segmented_pixels = centers[labels.flatten()]
        segmented_img = segmented_pixels.reshape(arr.shape)
        
        return Image.fromarray(segmented_img)