#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SOURCE_ENGINE="${UPSCALE_STUDIO_ENGINE_DIR:-$HOME/.local/share/realesrgan}"
VERSION="0.1.1"
STAGE="$ROOT/build/stage-${VERSION}"
PACKAGE="$ROOT/dist/upscale-studio_${VERSION}_amd64.deb"

for file in "$SOURCE_ENGINE/realesrgan-ncnn-vulkan" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus.bin" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus.param" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus-anime.bin" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus-anime.param"; do
    if [ ! -f "$file" ]; then
        echo "Falta el archivo del motor: $file" >&2
        exit 1
    fi
done

mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/bin" "$STAGE/usr/lib/upscale-studio/engine/models" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/doc/upscale-studio" "$ROOT/dist"

install -m 0644 "$ROOT/app.py" "$ROOT/core.py" "$STAGE/usr/lib/upscale-studio/"
install -m 0755 "$SOURCE_ENGINE/realesrgan-ncnn-vulkan" "$STAGE/usr/lib/upscale-studio/engine/"
install -m 0644 "$SOURCE_ENGINE/models/realesrgan-x4plus.bin" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus.param" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus-anime.bin" \
    "$SOURCE_ENGINE/models/realesrgan-x4plus-anime.param" \
    "$STAGE/usr/lib/upscale-studio/engine/models/"
install -m 0644 "$ROOT/LICENSE-Real-ESRGAN" "$ROOT/LICENSE-NCNN" "$ROOT/README.md" \
    "$STAGE/usr/share/doc/upscale-studio/"
install -m 0644 "$ROOT/upscale-studio.desktop" "$STAGE/usr/share/applications/"
for size in 16 32 48 64 128 256 512; do
    icon="$ROOT/icons/upscale-studio-${size}.png"
    if [ ! -f "$icon" ]; then
        echo "Falta el icono: $icon" >&2
        exit 1
    fi
    mkdir -p "$STAGE/usr/share/icons/hicolor/${size}x${size}/apps"
    install -m 0644 "$icon" "$STAGE/usr/share/icons/hicolor/${size}x${size}/apps/upscale-studio.png"
done

cat > "$STAGE/usr/bin/upscale-studio" <<'LAUNCHER'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/upscale-studio/app.py "$@"
LAUNCHER
chmod 0755 "$STAGE/usr/bin/upscale-studio"

cat > "$STAGE/DEBIAN/control" <<'CONTROL'
Package: upscale-studio
Version: 0.1.1
Section: graphics
Priority: optional
Architecture: amd64
Maintainer: N3ruk <264709581+N3ruk@users.noreply.github.com>
Depends: python3 (>= 3.10), python3-pyqt6, python3-pil, imagemagick (>= 8:7.0), libvulkan1, libgomp1
Description: Interfaz local para reescalar imágenes con Real-ESRGAN y Lanczos
 Incluye Real-ESRGAN NCNN Vulkan y modelos para fotografía e ilustración.
 Permite TTA, preajustes, tamaño libre, recorte, márgenes y nitidez.
CONTROL

dpkg-deb --build --root-owner-group "$STAGE" "$PACKAGE"
echo "$PACKAGE"
