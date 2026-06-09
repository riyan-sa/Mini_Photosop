import io
from PIL import Image

class ImageCompressor:
    @staticmethod
    def compress_jpeg_simulation(img: Image.Image, quality: int) -> tuple[Image.Image, int, float]:
        """
        Simulasi kompresi JPEG berdasarkan level kualitas kuantisasi (0-100).
        Mengembalikan: (Gambar_Kompresi, Ukuran_Byte, Rasio_Kompresi)
        """
        # 1. Hitung ukuran data mentah asli dalam memori (uncompressed)
        w, h = img.size
        original_size_bytes = w * h * 3 # RGB = 3 bytes per piksel
        
        # 2. Lakukan simulasi kuantisasi & kompresi JPEG ke dalam buffer memori
        buf = io.BytesIO()
        # Menggunakan format JPEG dengan parameter quality bawaan Pillow (berbasis matriks kuantisasi standar)
        img.save(buf, format="JPEG", quality=quality)
        compressed_size_bytes = buf.tell()
        
        # 3. Ambil kembali objek gambarnya untuk di-render ke canvas
        buf.seek(0)
        compressed_img = Image.open(buf).convert("RGB")
        
        # 4. Hitung rasio kompresi (dalam persen %)
        compression_ratio = round((1 - (compressed_size_bytes / original_size_bytes)) * 100, 2)
        if compression_ratio < 0:
            compression_ratio = 0.0
            
        return compressed_img, compressed_size_bytes, compression_ratio