import cv2
import numpy as np
from PIL import Image

class BinaryEdgeProcessor:
    @staticmethod
    def apply_threshold(img: Image.Image, value: int) -> Image.Image:
        """1. Thresholding Biner Murni"""
        arr = np.array(img.convert("L"))
        _, thresh = cv2.threshold(arr, value, 255, cv2.THRESH_BINARY)
        return Image.fromarray(thresh).convert("RGB")

    @staticmethod
    def edge_detection(img: Image.Image, method: str, p1: int = 50, p2: int = 150) -> Image.Image:
        """2. Kelompok 6 Dewa Edge Detection"""
        gray = np.array(img.convert("L"))
        
        if method == "canny":
            res = cv2.Canny(gray, p1, p2)
        elif method == "sobel":
            grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
            abs_x = cv2.convertScaleAbs(grad_x)
            abs_y = cv2.convertScaleAbs(grad_y)
            res = cv2.addWeighted(abs_x, 0.5, abs_y, 0.5, 0)
        elif method == "prewitt":
            kernelx = np.array([[1,1,1],[0,0,0],[-1,-1,-1]], dtype=np.float32)
            kernely = np.array([[-1,0,1],[-1,0,1],[-1,0,1]], dtype=np.float32)
            img_x = cv2.filter2D(gray, -1, kernelx)
            img_y = cv2.filter2D(gray, -1, kernely)
            res = cv2.addWeighted(img_x, 0.5, img_y, 0.5, 0)
        elif method == "robert":
            kernelx = np.array([[1, 0], [0, -1]], dtype=np.float32)
            kernely = np.array([[0, 1], [-1, 0]], dtype=np.float32)
            img_x = cv2.filter2D(gray, -1, kernelx)
            img_y = cv2.filter2D(gray, -1, kernely)
            res = cv2.addWeighted(img_x, 0.5, img_y, 0.5, 0)
        elif method == "laplacian":
            res = cv2.Laplacian(gray, cv2.CV_8U, ksize=3)
        elif method == "log": # Laplacian of Gaussian
            blur = cv2.GaussianBlur(gray, (3, 3), 0)
            res = cv2.Laplacian(blur, cv2.CV_8U, ksize=3)
        else:
            return img
            
        return Image.fromarray(res).convert("RGB")

    @staticmethod
    def morphology(img: Image.Image, operation: str, kernel_size: int) -> Image.Image:
        """3. Operasi Morfologi Citra Biner"""
        arr = np.array(img.convert("RGB"))
        # Buat matriks structuring element kotak murni berbasis kernel size ganjil
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        
        if operation == "erosion":
            res = cv2.erode(arr, kernel, iterations=1)
        elif operation == "dilation":
            res = cv2.dilate(arr, kernel, iterations=1)
        else:
            return img
            
        return Image.fromarray(res)