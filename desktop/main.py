"""
Mini Photoshop — Main Window
GUI utama dengan PyQt5
Tahap 2: Image Enhancement (brightness, contrast, sharpen, blur, hist. eq.)
"""

import sys
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QHBoxLayout, QVBoxLayout, QToolBar, QAction,
    QFileDialog, QMessageBox, QSizePolicy, QStatusBar,
    QSplitter, QFrame, QSlider, QPushButton, QGroupBox,
    QScrollArea,
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QSize, QTimer

from PIL import Image
from modules.image_manager import ImageManager
from modules.image_enhancer import ImageEnhancer


# ─── Helper ──────────────────────────────────────────────────
def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    img_rgb = img.convert("RGB")
    data = img_rgb.tobytes("raw", "RGB")
    qimg = QImage(data, img_rgb.width, img_rgb.height, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


# ─── Image Panel ─────────────────────────────────────────────
class ImagePanel(QFrame):
    def __init__(self, label_text: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)
        self._pixmap_original = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.header = QLabel(label_text)
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setFont(QFont("Consolas", 10, QFont.Bold))
        self.header.setStyleSheet("color: #cba6f7; background: transparent; border: none;")
        layout.addWidget(self.header)

        self.image_label = QLabel("Belum ada gambar")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #6c7086; background: transparent; border: none;")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.image_label)

    def set_image(self, img: Image.Image):
        self._pixmap_original = pil_to_qpixmap(img)
        self._rescale()

    def clear(self):
        self._pixmap_original = None
        self.image_label.clear()
        self.image_label.setText("Belum ada gambar")

    def _rescale(self):
        if self._pixmap_original:
            scaled = self._pixmap_original.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()


# ─── Slider Row ──────────────────────────────────────────────
class SliderRow(QWidget):
    def __init__(self, label: str, min_val: int, max_val: int, default: int, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("color: #cdd6f4; font-size: 12px;")
        layout.addWidget(lbl)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #313244;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #cba6f7;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #cba6f7;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.slider)

        self.value_label = QLabel(str(default))
        self.value_label.setFixedWidth(30)
        self.value_label.setAlignment(Qt.AlignRight)
        self.value_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
        layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(lambda v: self.value_label.setText(str(v)))


# ─── Enhancement Panel ───────────────────────────────────────
class EnhancementPanel(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setWidgetResizable(True)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #181825;
                border: none;
                border-left: 1px solid #313244;
            }
            QScrollBar:vertical {
                background: #1e1e2e;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #45475a;
                border-radius: 3px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background-color: #181825;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(16)

        title = QLabel("Enhancement")
        title.setFont(QFont("Consolas", 13, QFont.Bold))
        title.setStyleSheet("color: #cba6f7;")
        layout.addWidget(title)

        group_style = """
            QGroupBox {
                color: #a6adc8;
                font-size: 11px;
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """

        grp1 = QGroupBox("Tone")
        grp1.setStyleSheet(group_style)
        g1 = QVBoxLayout(grp1)
        self.s_brightness = SliderRow("Brightness", 0, 200, 100)
        self.s_contrast   = SliderRow("Contrast",   0, 200, 100)
        g1.addWidget(self.s_brightness)
        g1.addWidget(self.s_contrast)
        layout.addWidget(grp1)

        grp2 = QGroupBox("Detail")
        grp2.setStyleSheet(group_style)
        g2 = QVBoxLayout(grp2)
        self.s_sharpen = SliderRow("Sharpen", 100, 500, 100)
        self.s_blur    = SliderRow("Blur",    0,   20,  0)
        g2.addWidget(self.s_sharpen)
        g2.addWidget(self.s_blur)
        layout.addWidget(grp2)

        btn_style = """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
        """

        self.btn_apply = QPushButton("✅  Terapkan")
        self.btn_apply.setStyleSheet(
            btn_style.replace("background-color: #313244", "background-color: #4c4f69")
                     .replace("color: #cdd6f4", "color: #cba6f7")
        )
        self.btn_histeq        = QPushButton("📊  Histogram EQ")
        self.btn_histeq.setStyleSheet(btn_style)
        self.btn_reset_sliders = QPushButton("↩  Reset Slider")
        self.btn_reset_sliders.setStyleSheet(btn_style)

        layout.addWidget(self.btn_apply)
        layout.addWidget(self.btn_histeq)
        layout.addWidget(self.btn_reset_sliders)
        layout.addStretch()

        self.setWidget(container)

    def get_values(self) -> dict:
        return {
            "brightness": self.s_brightness.slider.value() / 100,
            "contrast":   self.s_contrast.slider.value()   / 100,
            "sharpen":    self.s_sharpen.slider.value()     / 100,
            "blur":       self.s_blur.slider.value()        / 2,
        }

    def reset_sliders(self):
        self.s_brightness.slider.setValue(100)
        self.s_contrast.slider.setValue(100)
        self.s_sharpen.slider.setValue(100)
        self.s_blur.slider.setValue(0)


# ─── Main Window ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager  = ImageManager()
        self.enhancer = ImageEnhancer()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Mini Photoshop")
        self.resize(1280, 720)
        self.setStyleSheet("""
            QMainWindow { background-color: #181825; }
            QToolBar {
                background-color: #1e1e2e;
                border-bottom: 1px solid #313244;
                padding: 4px 8px;
                spacing: 6px;
            }
            QToolBar QToolButton {
                color: #cdd6f4;
                background: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
            }
            QToolBar QToolButton:hover { background-color: #313244; border-color: #45475a; }
            QToolBar QToolButton:pressed { background-color: #45475a; }
            QStatusBar {
                background-color: #1e1e2e;
                color: #6c7086;
                font-size: 11px;
                border-top: 1px solid #313244;
            }
        """)
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

    def _build_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        for text, tip, slot in [
            ("📂  Buka", "Buka gambar", self.action_open),
            ("💾  Simpan", "Simpan gambar", self.action_save),
            ("↩  Reset", "Reset ke awal", self.action_reset),
        ]:
            act = QAction(text, self)
            act.setStatusTip(tip)
            act.triggered.connect(slot)
            toolbar.addAction(act)
            toolbar.addSeparator()

    def _build_central(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #313244; width: 2px; }")
        self.panel_before = ImagePanel("BEFORE")
        self.panel_after  = ImagePanel("AFTER")
        splitter.addWidget(self.panel_before)
        splitter.addWidget(self.panel_after)
        splitter.setSizes([500, 500])

        self.enh_panel = EnhancementPanel()
        self.enh_panel.btn_apply.clicked.connect(self.action_apply_enhancement)
        self.enh_panel.btn_histeq.clicked.connect(self.action_histeq)
        self.enh_panel.btn_reset_sliders.clicked.connect(self.enh_panel.reset_sliders)

        # Live preview dengan debounce 300ms
        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._live_preview)
        for row in [
            self.enh_panel.s_brightness,
            self.enh_panel.s_contrast,
            self.enh_panel.s_sharpen,
            self.enh_panel.s_blur,
        ]:
            row.slider.valueChanged.connect(lambda _: self._preview_timer.start(300))

        root = QWidget()
        root.setStyleSheet("background-color: #181825;")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(12, 12, 0, 12)
        layout.setSpacing(0)
        layout.addWidget(splitter)
        layout.addWidget(self.enh_panel)
        self.setCentralWidget(root)

    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Buka gambar untuk mulai.")

    # ─── Live Preview ────────────────────────────────────────
    def _live_preview(self):
        if not self.manager.has_image():
            return
        result = self._apply_enhancements(self.manager.original_image)
        self.panel_after.set_image(result)

    def _apply_enhancements(self, base_img: Image.Image) -> Image.Image:
        v = self.enh_panel.get_values()
        img = base_img.copy()
        img = ImageEnhancer.adjust_brightness(img, v["brightness"])
        img = ImageEnhancer.adjust_contrast(img, v["contrast"])
        img = ImageEnhancer.sharpen(img, v["sharpen"])
        img = ImageEnhancer.blur(img, v["blur"])
        return img

    # ─── Actions ─────────────────────────────────────────────
    def action_open(self):
        file_filter = ";;".join(
            f"{name} ({ext})" for name, ext in self.manager.SUPPORTED_FORMATS
        )
        path, _ = QFileDialog.getOpenFileName(self, "Buka Gambar", "", file_filter)
        if not path:
            return
        try:
            img = self.manager.load_image(path)
            self.panel_before.set_image(img)
            self.panel_after.set_image(img)
            self.enh_panel.reset_sliders()
            info = self.manager.get_info()
            self.status.showMessage(
                f"📂  {Path(path).name}   |   {info['width']} × {info['height']} px   |   {info['mode']}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def action_save(self):
        if not self.manager.has_image():
            QMessageBox.warning(self, "Belum ada gambar", "Buka gambar dulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Simpan", "", "JPEG (*.jpg *.jpeg);;PNG (*.png);;BMP (*.bmp)"
        )
        if not path:
            return
        try:
            self.manager.save_image(path)
            self.status.showMessage(f"✅  Tersimpan: {Path(path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def action_reset(self):
        if not self.manager.has_image():
            return
        img = self.manager.reset_image()
        self.panel_before.set_image(img)
        self.panel_after.set_image(img)
        self.enh_panel.reset_sliders()
        self.status.showMessage("↩  Reset ke gambar awal.")

    def action_apply_enhancement(self):
        if not self.manager.has_image():
            QMessageBox.warning(self, "Belum ada gambar", "Buka gambar dulu.")
            return
        result = self._apply_enhancements(self.manager.original_image)
        self.manager.update_current(result)
        self.panel_after.set_image(result)
        self.status.showMessage("✅  Enhancement diterapkan.")

    def action_histeq(self):
        if not self.manager.has_image():
            return
        result = ImageEnhancer.histogram_equalization(self.manager.current_image)
        self.manager.update_current(result)
        self.panel_after.set_image(result)
        self.status.showMessage("📊  Histogram equalization diterapkan.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 