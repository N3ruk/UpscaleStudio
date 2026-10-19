#!/usr/bin/python3
"""Interfaz Qt de Upscale Studio."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal, QRectF, QUrl, QSize
from PyQt6.QtGui import QDesktopServices, QIcon, QImageReader, QPainter, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from core import Cancelled, GRAVITIES, Job, diagnostics, process, source_size


PRESETS = [
    ('4K UHD · 3840 × 2160', 3840, 2160),
    ('1440p · 2560 × 1440', 2560, 1440),
    ('1080p · 1920 × 1080', 1920, 1080),
    ('8K UHD · 7680 × 4320', 7680, 4320),
    ('Vertical 4K · 2160 × 3840', 2160, 3840),
    ('Vertical 1080 · 1080 × 1920', 1080, 1920),
    ('Cuadrado · 2048 × 2048', 2048, 2048),
    ('Personalizada', None, None),
]


class Worker(QThread):
    progress = pyqtSignal(str)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)
    interrupted = pyqtSignal()

    def __init__(self, job: Job) -> None:
        super().__init__()
        self.job = job
        self.cancel_flag = threading.Event()

    def run(self) -> None:
        try:
            result = process(self.job, self.progress.emit, self.cancel_flag)
            self.succeeded.emit(str(result))
        except Cancelled:
            self.interrupted.emit()
        except Exception as error:
            self.failed.emit(str(error))

    def cancel(self) -> None:
        self.cancel_flag.set()


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Upscale Studio')
        self.resize(1040, 790)
        self.worker: Worker | None = None
        self.last_output: Path | None = None
        self.source_pixmap = QPixmap()
        self.source_dimensions = (0, 0)

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        main.addWidget(scroll)
        panel = QWidget()
        scroll.setWidget(panel)
        layout = QGridLayout(panel)
        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 3)

        files = QGroupBox('Archivos')
        files_box = QFormLayout(files)
        source_row = QHBoxLayout()
        self.source = QLineEdit()
        source_row.addWidget(self.source)
        pick_source = QPushButton('Elegir…')
        pick_source.clicked.connect(self.choose_source)
        source_row.addWidget(pick_source)
        files_box.addRow('Imagen:', source_row)
        output_row = QHBoxLayout()
        self.output_dir = QLineEdit()
        self.output_dir.setText(str(Path.home() / 'Imágenes' if (Path.home() / 'Imágenes').is_dir() else Path.home()))
        output_row.addWidget(self.output_dir)
        pick_output = QPushButton('Carpeta…')
        pick_output.clicked.connect(self.choose_output)
        output_row.addWidget(pick_output)
        files_box.addRow('Guardar en:', output_row)
        layout.addWidget(files, 0, 0, 1, 2)

        controls = QGroupBox('Procesamiento')
        form = QFormLayout(controls)
        self.preset = QComboBox()
        for label, width, height in PRESETS:
            self.preset.addItem(label, (width, height))
        form.addRow('Resolución:', self.preset)
        dimensions = QHBoxLayout()
        self.width = QSpinBox()
        self.height = QSpinBox()
        for spin in (self.width, self.height):
            spin.setRange(16, 16384)
            spin.setSingleStep(16)
            dimensions.addWidget(spin)
        dimensions.insertWidget(1, QLabel('×'))
        form.addRow('Ancho × alto:', dimensions)
        self.method = QComboBox()
        self.method.addItem('IA rápida · método actual', 'fast')
        self.method.addItem('IA detallada · TTA, más lenta', 'quality')
        self.method.addItem('Lanczos · sin IA', 'classic')
        form.addRow('Motor:', self.method)
        self.content = QComboBox()
        self.content.addItem('Fotografía / general', 'photo')
        self.content.addItem('Ilustración / anime', 'anime')
        form.addRow('Modelo:', self.content)
        self.aspect = QComboBox()
        self.aspect.addItem('Rellenar y recortar · sin deformar', 'crop')
        self.aspect.addItem('Ajustar con márgenes · imagen completa', 'fit')
        self.aspect.addItem('Estirar · deforma proporciones', 'stretch')
        form.addRow('Proporciones:', self.aspect)
        self.gravity = QComboBox()
        for label, value in GRAVITIES.items():
            self.gravity.addItem(label, value)
        form.addRow('Zona conservada:', self.gravity)
        self.background = QComboBox()
        self.background.addItem('Negro', 'black')
        self.background.addItem('Blanco', 'white')
        self.background.addItem('Transparente', 'none')
        form.addRow('Color de márgenes:', self.background)
        self.sharpness = QSlider(Qt.Orientation.Horizontal)
        self.sharpness.setRange(0, 150)
        self.sharpness.setValue(60)
        self.sharp_label = QLabel('0,60 · como upscale4k')
        sharp_row = QHBoxLayout()
        sharp_row.addWidget(self.sharpness)
        sharp_row.addWidget(self.sharp_label)
        form.addRow('Nitidez:', sharp_row)
        self.format = QComboBox()
        for name in ('PNG', 'JPEG', 'WebP'):
            self.format.addItem(name)
        form.addRow('Formato:', self.format)
        layout.addWidget(controls, 1, 0)

        preview_group = QGroupBox('Vista previa de encuadre')
        preview_box = QVBoxLayout(preview_group)
        self.preview = QLabel('Selecciona una imagen')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(430, 360)
        self.preview.setStyleSheet('background: #242424; color: white; border: 1px solid #555;')
        preview_box.addWidget(self.preview)
        self.preview_note = QLabel('Muestra geometría y márgenes, no el resultado de la IA.')
        self.preview_note.setWordWrap(True)
        preview_box.addWidget(self.preview_note)
        self.info = QLabel('')
        self.info.setWordWrap(True)
        preview_box.addWidget(self.info)
        layout.addWidget(preview_group, 1, 1)

        issues = diagnostics()
        if issues:
            self.dependencies = QLabel('Diagnóstico: ' + ' '.join(issues))
            self.dependencies.setWordWrap(True)
            self.dependencies.setStyleSheet('color: #b34b00;')
            layout.addWidget(self.dependencies, 2, 0, 1, 2)

        actions = QHBoxLayout()
        self.start = QPushButton('Reescalar')
        self.start.clicked.connect(self.start_job)
        self.cancel = QPushButton('Cancelar')
        self.cancel.setEnabled(False)
        self.cancel.clicked.connect(self.cancel_job)
        self.open_result = QPushButton('Abrir resultado')
        self.open_result.setEnabled(False)
        self.open_result.clicked.connect(self.open_file)
        actions.addWidget(self.start)
        actions.addWidget(self.cancel)
        actions.addWidget(self.open_result)
        actions.addStretch()
        main.addLayout(actions)
        self.status = QLabel('Listo.')
        main.addWidget(self.status)

        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.width.valueChanged.connect(self.custom_size_changed)
        self.height.valueChanged.connect(self.custom_size_changed)
        self.source.textChanged.connect(self.load_source)
        for combo in (self.aspect, self.gravity, self.background, self.format):
            combo.currentIndexChanged.connect(self.refresh_preview)
        self.sharpness.valueChanged.connect(self.refresh_sharpness)
        self.method.currentIndexChanged.connect(self.update_controls)
        self.aspect.currentIndexChanged.connect(self.update_controls)
        self.apply_preset()
        self.update_controls()

    def choose_source(self) -> None:
        file, _ = QFileDialog.getOpenFileName(self, 'Seleccionar imagen', str(Path.home()),
                                              'Imágenes (*.png *.jpg *.jpeg *.webp)')
        if file:
            self.source.setText(file)
            self.output_dir.setText(str(Path(file).parent))

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Carpeta de salida', self.output_dir.text())
        if folder:
            self.output_dir.setText(folder)

    def apply_preset(self) -> None:
        width, height = self.preset.currentData()
        if width is not None:
            for spin, value in ((self.width, width), (self.height, height)):
                spin.blockSignals(True)
                spin.setValue(value)
                spin.blockSignals(False)
        self.refresh_preview()

    def custom_size_changed(self) -> None:
        if self.preset.currentData() != (None, None):
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(len(PRESETS) - 1)
            self.preset.blockSignals(False)
        self.refresh_preview()

    def load_source(self) -> None:
        path = Path(self.source.text().strip())
        self.source_pixmap = QPixmap()
        self.source_dimensions = (0, 0)
        if path.is_file():
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            dimensions = reader.size()
            if dimensions.isValid() and max(dimensions.width(), dimensions.height()) > 1200:
                scale = 1200 / max(dimensions.width(), dimensions.height())
                reader.setScaledSize(QSize(max(1, round(dimensions.width() * scale)),
                                           max(1, round(dimensions.height() * scale))))
            image = reader.read()
            if not image.isNull():
                self.source_pixmap = QPixmap.fromImage(image)
                self.source_dimensions = source_size(path)
        self.refresh_preview()

    def update_controls(self) -> None:
        mode = self.aspect.currentData()
        self.gravity.setEnabled(mode == 'crop')
        self.background.setEnabled(mode == 'fit')
        self.content.setEnabled(self.method.currentData() != 'classic')
        self.refresh_preview()

    def refresh_sharpness(self) -> None:
        value = self.sharpness.value()
        suffix = ' · como upscale4k' if value == 60 else ''
        self.sharp_label.setText(format(value / 100, '.2f').replace('.', ',') + suffix)

    def refresh_preview(self) -> None:
        if self.source_pixmap.isNull():
            self.preview.setText('Selecciona una imagen')
            self.info.setText('')
            return
        width, height = self.width.value(), self.height.value()
        src_w, src_h = self.source_pixmap.width(), self.source_pixmap.height()
        available_w, available_h = 570, 380
        factor = min(available_w / width, available_h / height)
        canvas_w = max(1, round(width * factor))
        canvas_h = max(1, round(height * factor))
        canvas = QPixmap(canvas_w, canvas_h)
        bg = self.background.currentData()
        canvas.fill(QColor('#ddd') if bg == 'none' else QColor(bg))
        painter = QPainter(canvas)
        if bg == 'none':
            for y in range(0, canvas_h, 20):
                for x in range(0, canvas_w, 20):
                    if (x // 20 + y // 20) % 2:
                        painter.fillRect(x, y, 20, 20, QColor('#999'))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        source = QRectF(0, 0, src_w, src_h)
        mode = self.aspect.currentData()
        if mode == 'stretch':
            target = QRectF(0, 0, canvas_w, canvas_h)
            note = 'Estiramiento: la imagen completa cambia de proporciones.'
        elif mode == 'fit':
            scale = min(canvas_w / src_w, canvas_h / src_h)
            draw_w, draw_h = src_w * scale, src_h * scale
            target = QRectF((canvas_w - draw_w) / 2, (canvas_h - draw_h) / 2, draw_w, draw_h)
            note = 'Imagen completa; los márgenes completan el lienzo.'
        else:
            target = QRectF(0, 0, canvas_w, canvas_h)
            target_ar = width / height
            source_ar = src_w / src_h
            if source_ar > target_ar:
                crop_w, crop_h = src_h * target_ar, src_h
            else:
                crop_w, crop_h = src_w, src_w / target_ar
            gravity = self.gravity.currentData()
            x_fraction = 0 if 'west' in gravity else 1 if 'east' in gravity else 0.5
            y_fraction = 0 if 'north' in gravity else 1 if 'south' in gravity else 0.5
            source = QRectF((src_w - crop_w) * x_fraction, (src_h - crop_h) * y_fraction, crop_w, crop_h)
            retained = (crop_w * crop_h) / (src_w * src_h)
            note = 'Recorte aproximado: se conserva el ' + str(round(retained * 100, 1)).replace('.', ',') + '% del área.'
        painter.drawPixmap(target, self.source_pixmap, source)
        painter.end()
        self.preview.setPixmap(canvas)
        actual_w, actual_h = self.source_dimensions
        self.info.setText(str(actual_w) + ' × ' + str(actual_h) + ' → ' + str(width) + ' × ' + str(height) + '. ' + note)

    def make_job(self) -> Job:
        source = Path(self.source.text().strip()).expanduser().resolve()
        output = Path(self.output_dir.text().strip()).expanduser().resolve()
        source_size(source)
        return Job(source=source, output_dir=output, width=self.width.value(),
                   height=self.height.value(), method=self.method.currentData(),
                   content=self.content.currentData(), aspect=self.aspect.currentData(),
                   sharpness=self.sharpness.value(), format=self.format.currentText(),
                   background=self.background.currentData(), gravity=self.gravity.currentData())

    def start_job(self) -> None:
        if self.worker is not None:
            return
        try:
            job = self.make_job()
        except Exception as error:
            QMessageBox.warning(self, 'Imagen no válida', str(error))
            return
        self.worker = Worker(job)
        self.worker.progress.connect(self.status.setText)
        self.worker.succeeded.connect(self.finished)
        self.worker.failed.connect(self.error)
        self.worker.interrupted.connect(self.cancelled)
        self.worker.finished.connect(self.worker_done)
        self.start.setEnabled(False)
        self.cancel.setEnabled(True)
        self.open_result.setEnabled(False)
        self.status.setText('Iniciando…')
        self.worker.start()

    def cancel_job(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.status.setText('Cancelando…')
            self.cancel.setEnabled(False)

    def finished(self, file: str) -> None:
        self.last_output = Path(file)
        self.open_result.setEnabled(True)
        self.status.setText('Terminado: ' + file)

    def error(self, message: str) -> None:
        self.status.setText('Error: ' + message)
        QMessageBox.critical(self, 'No se pudo reescalar', message)

    def cancelled(self) -> None:
        self.status.setText('Cancelado; no se creó un resultado incompleto.')

    def worker_done(self) -> None:
        self.worker = None
        self.start.setEnabled(True)
        self.cancel.setEnabled(False)

    def open_file(self) -> None:
        if self.last_output is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_output)))

    def closeEvent(self, event) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.worker.wait(5000)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('upscale-studio')
    app.setApplicationDisplayName('Upscale Studio')
    app.setDesktopFileName('upscale-studio')
    packaged_icon = Path('/usr/share/icons/hicolor/256x256/apps/upscale-studio.png')
    local_icon = Path(__file__).resolve().parent / 'icons/upscale-studio-256.png'
    icon_path = packaged_icon if packaged_icon.is_file() else local_icon
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = Window()
    window.setWindowIcon(app.windowIcon())
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
        window.source.setText(str(Path(sys.argv[1]).resolve()))
        window.output_dir.setText(str(Path(sys.argv[1]).resolve().parent))
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
