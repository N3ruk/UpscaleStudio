# Upscale Studio

English · [Español](README.md)

A local desktop app for upscaling **one image at a time** on Linux. It accepts PNG, JPEG and WebP images. The GUI is currently in Spanish.

## What it does

Select an input image and output folder, then choose a preset or custom size (16–16384 pixels per side, up to 134 megapixels), processing method, aspect-ratio handling, sharpness and output format. The preview shows framing and margins; it does **not** preview AI detail or sharpening. Processing stays on the local machine, and cancelling removes intermediate output.

| Method | Processing |
| --- | --- |
| Fast AI | Real-ESRGAN NCNN Vulkan at ×4, then Lanczos resize |
| Detailed AI / TTA | The same model with test-time augmentation (`-x`), then Lanczos; slower and not guaranteed to look better |
| Lanczos | ImageMagick resize without AI or a GPU requirement |

For AI, choose the `realesrgan-x4plus` general/photo model or `realesrgan-x4plus-anime` model. Both AI methods always run at ×4 before resizing to the selected output size, so large inputs may need substantial time and memory.

Aspect options: **fill and crop** (select retained edge/corner), **fit with margins** (black, white or transparent), or **stretch** (changes proportions). Transparent margins require PNG or WebP, not JPEG. The sharpness slider ranges from 0.00 to 1.50 (default 0.60). Output names include the method, size and aspect option; existing files and the source are not overwritten.

## Install

Download `upscale-studio_0.1.1_amd64.deb` from the [latest release](https://github.com/N3ruk/UpscaleStudio/releases/latest), then run from the download directory:

```bash
sudo apt install ./upscale-studio_0.1.1_amd64.deb
```

The package targets amd64 Ubuntu versions with ImageMagick 7 and declares Python 3, PyQt6, Pillow, ImageMagick, Vulkan loader and libgomp dependencies. It bundles the Real-ESRGAN NCNN Vulkan executable and two models; no models are downloaded at runtime. AI requires a working Vulkan GPU driver. Lanczos works without a GPU. Use `apt install`, since `dpkg -i` alone does not resolve dependencies.

## Run from source / build the DEB

```bash
python3 app.py
./build-deb.sh
```

The source run needs Python 3, PyQt6, Pillow and ImageMagick 7. For AI, the app looks for Real-ESRGAN under `~/.local/share/realesrgan`, or set `UPSCALE_STUDIO_ENGINE_DIR` to another directory containing `realesrgan-ncnn-vulkan` and the `models/` folder. The build script uses the same engine directory and writes the package to `dist/`. The executable and models are **not** committed to this repository; they are bundled in the release DEB.

Third-party license texts distributed with the package are in `LICENSE-Real-ESRGAN` and `LICENSE-NCNN`. No reuse license has been published for the application’s own code yet.
