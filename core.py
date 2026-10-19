"""Motor local de Upscale Studio. No ejecuta comandos mediante shell."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image


INSTALL_ENGINE = Path('/usr/lib/upscale-studio/engine')
USER_ENGINE = Path.home() / '.local/share/realesrgan'
EXTENSIONS = {'PNG': 'png', 'JPEG': 'jpg', 'WebP': 'webp'}
GRAVITIES = {
    'Centro': 'center', 'Arriba': 'north', 'Abajo': 'south',
    'Izquierda': 'west', 'Derecha': 'east',
    'Superior izquierda': 'northwest', 'Superior derecha': 'northeast',
    'Inferior izquierda': 'southwest', 'Inferior derecha': 'southeast',
}


@dataclass(frozen=True)
class Job:
    source: Path
    output_dir: Path
    width: int
    height: int
    method: str = 'fast'
    content: str = 'photo'
    aspect: str = 'crop'
    sharpness: int = 60
    format: str = 'PNG'
    background: str = 'black'
    gravity: str = 'center'


class Cancelled(Exception):
    pass


def engine_dir() -> Path:
    override = os.environ.get('UPSCALE_STUDIO_ENGINE_DIR')
    if override:
        return Path(override)
    if (INSTALL_ENGINE / 'realesrgan-ncnn-vulkan').is_file():
        return INSTALL_ENGINE
    return USER_ENGINE


def diagnostics() -> list[str]:
    issues = []
    if not shutil.which('magick'):
        issues.append('Falta ImageMagick (magick).')
    base = engine_dir()
    if not os.access(base / 'realesrgan-ncnn-vulkan', os.X_OK):
        issues.append('Falta el ejecutable Real-ESRGAN NCNN Vulkan.')
    for name in ('realesrgan-x4plus', 'realesrgan-x4plus-anime'):
        if not (base / 'models' / (name + '.bin')).is_file() or not (base / 'models' / (name + '.param')).is_file():
            issues.append('Falta el modelo ' + name + '.')
    if not Path('/usr/lib/x86_64-linux-gnu/libvulkan.so.1').exists() and not Path('/lib/x86_64-linux-gnu/libvulkan.so.1').exists():
        issues.append('Falta el cargador Vulkan. Instala libvulkan1.')
    return issues


def source_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        w, h = image.size
        if image.getexif().get(274, 1) in (5, 6, 7, 8):
            return h, w
        return w, h


def validate(job: Job) -> None:
    if not job.source.is_file():
        raise ValueError('La imagen de origen no existe.')
    if not job.output_dir.is_dir():
        raise ValueError('La carpeta de salida no existe.')
    if not 16 <= job.width <= 16384 or not 16 <= job.height <= 16384:
        raise ValueError('La resolución debe estar entre 16 y 16384 píxeles por lado.')
    if job.width * job.height > 134_217_728:
        raise ValueError('El destino supera 134 megapíxeles.')
    if job.method not in ('fast', 'quality', 'classic'):
        raise ValueError('Método desconocido.')
    if job.content not in ('photo', 'anime') or job.aspect not in ('crop', 'fit', 'stretch'):
        raise ValueError('Modelo o ajuste de proporciones desconocido.')
    if job.format not in EXTENSIONS:
        raise ValueError('Formato de salida desconocido.')
    if not 0 <= job.sharpness <= 150:
        raise ValueError('La nitidez debe estar entre 0 y 150.')
    if job.background not in ('black', 'white', 'none') or job.gravity not in GRAVITIES.values():
        raise ValueError('Fondo o posición de recorte desconocidos.')
    if job.format == 'JPEG' and job.background == 'none' and job.aspect == 'fit':
        raise ValueError('JPEG no admite márgenes transparentes.')
    source_size(job.source)
    if not shutil.which('magick'):
        raise RuntimeError('Falta ImageMagick. Instala el DEB con apt para resolver dependencias.')
    if job.method != 'classic':
        base = engine_dir()
        model = 'realesrgan-x4plus-anime' if job.content == 'anime' else 'realesrgan-x4plus'
        if not os.access(base / 'realesrgan-ncnn-vulkan', os.X_OK):
            raise RuntimeError('No se encuentra Real-ESRGAN. Instala el DEB completo.')
        if not all((base / 'models' / (model + ext)).is_file() for ext in ('.bin', '.param')):
            raise RuntimeError('Falta el modelo ' + model + '.')


def _run(argv: list[str], cancelled: threading.Event) -> None:
    if cancelled.is_set():
        raise Cancelled()
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        while True:
            try:
                _out, err = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if cancelled.is_set():
                    process.terminate()
                    try:
                        process.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                    raise Cancelled()
        if process.returncode:
            detail = err.decode('utf-8', errors='replace')[-2200:].strip()
            raise RuntimeError(detail or 'El proceso terminó con error ' + str(process.returncode))
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def _output_path(job: Job) -> Path:
    stem = job.source.stem + '_upscale_' + job.method + '_' + str(job.width) + 'x' + str(job.height) + '_' + job.aspect
    ext = EXTENSIONS[job.format]
    path = job.output_dir / (stem + '.' + ext)
    number = 2
    while path.exists():
        path = job.output_dir / (stem + '_' + str(number) + '.' + ext)
        number += 1
    return path


def process(job: Job, report: Callable[[str], None], cancelled: threading.Event) -> Path:
    validate(job)
    destination = _output_path(job)
    with tempfile.TemporaryDirectory(prefix='.upscale-studio-', dir=job.output_dir) as temporary:
        work = Path(temporary)
        normalized = work / 'oriented.png'
        report('Preparando y orientando la imagen…')
        _run(['magick', str(job.source), '-auto-orient', str(normalized)], cancelled)
        image = normalized
        if job.method != 'classic':
            base = engine_dir()
            model = 'realesrgan-x4plus-anime' if job.content == 'anime' else 'realesrgan-x4plus'
            image = work / 'ai.png'
            argv = [str(base / 'realesrgan-ncnn-vulkan'), '-i', str(normalized), '-o', str(image),
                    '-m', str(base / 'models'), '-n', model, '-s', '4', '-f', 'png']
            if job.method == 'quality':
                argv.append('-x')
            report('Procesando con IA ' + ('TTA (lento)…' if job.method == 'quality' else 'rápida…'))
            _run(argv, cancelled)
        report('Ajustando tamaño, proporciones y nitidez…')
        argv = ['magick', str(image), '-filter', 'Lanczos']
        size = str(job.width) + 'x' + str(job.height)
        if job.aspect == 'crop':
            argv += ['-resize', size + '^', '-gravity', job.gravity, '-extent', size]
        elif job.aspect == 'fit':
            argv += ['-resize', size, '-background', job.background, '-gravity', 'center', '-extent', size]
        else:
            argv += ['-resize', size + '!']
        if job.sharpness:
            argv += ['-unsharp', '0x0.6+' + format(job.sharpness / 100, '.2f') + '+0.008']
        if job.format == 'JPEG':
            argv += ['-quality', '94']
        elif job.format == 'WebP':
            argv += ['-quality', '95']
        staged = work / ('result.' + EXTENSIONS[job.format])
        argv.append(str(staged))
        _run(argv, cancelled)
        if cancelled.is_set():
            raise Cancelled()
        if destination.exists():
            destination = _output_path(job)
        os.replace(staged, destination)
    report('Terminado: ' + str(destination))
    return destination
