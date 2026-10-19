# Upscale Studio

[English](README.en.md) · Español

Aplicación gráfica local para reescalar **una imagen cada vez**. Acepta PNG, JPEG y WebP y permite escoger resolución, método de procesamiento, tratamiento de proporciones, nitidez y formato de salida. Adapta el flujo local de `upscale4k`, pero **no modifica ese comando**.

## Cómo se usa

1. Seleccionar la imagen de origen y la carpeta donde guardar el resultado.
2. Elegir un preset de resolución o «Personalizada» e introducir ancho y alto. Al cambiar una dimensión, se activa automáticamente el modo personalizado.
3. Elegir motor, modelo (si se usa IA), tratamiento de proporciones, nitidez y formato.
4. Revisar la vista previa de **encuadre** y pulsar «Reescalar». La vista previa no muestra la calidad final de la IA.
5. Pulsar «Abrir resultado» al terminar. Se puede cancelar mientras se procesa; no se conserva una salida incompleta.

## Motores

| Motor | Qué hace | Cuándo elegirlo |
| --- | --- | --- |
| IA rápida · método actual | Real-ESRGAN NCNN Vulkan ×4; después Lanczos hasta el tamaño solicitado | Flujo equivalente al comando existente, con más controles de salida |
| IA detallada · TTA | El **mismo** Real-ESRGAN con `-x` (test-time augmentation), seguido de Lanczos | Comparar si la mejora visual de una imagen compensa el mayor tiempo y consumo |
| Lanczos · sin IA | Escala directamente con ImageMagick | Imagen ya grande, o cuando se prefiera no añadir detalles sintéticos |

Para los dos modos de IA se puede seleccionar `realesrgan-x4plus` (fotografía/general) o `realesrgan-x4plus-anime` (ilustración/anime). TTA **no es otro modelo ni garantiza mayor calidad** en todas las imágenes. El escalado con IA siempre calcula ×4 primero, incluso si la salida final es menor; no adapta el factor a la resolución solicitada. Las imágenes muy grandes pueden tardar y consumir mucha memoria.

## Resolución y proporciones

Presets: 4K UHD (3840 × 2160), 1440p (2560 × 1440), 1080p (1920 × 1080), 8K UHD (7680 × 4320), vertical 4K (2160 × 3840), vertical 1080 (1080 × 1920) y cuadrado (2048 × 2048). La resolución personalizada admite de 16 a 16384 píxeles por lado, con un límite de 134 megapíxeles en el resultado.

| Modo | Resultado | Control asociado |
| --- | --- | --- |
| Rellenar y recortar | Llena exactamente el lienzo **sin deformar**, eliminando las partes sobrantes | «Zona conservada»: centro, bordes o esquinas |
| Ajustar con márgenes | Conserva toda la imagen y sus proporciones; completa el lienzo | Márgenes negros, blancos o transparentes |
| Estirar | Llena exactamente el lienzo sin recorte ni márgenes, pero **deforma** la imagen cuando la proporción cambia | No requiere posición ni color |

Los márgenes transparentes se pueden guardar en PNG o WebP, **no en JPEG**. La vista previa aproxima el encuadre, la proporción y los márgenes; no previsualiza la nitidez ni el detalle generado por IA.

## Nitidez y salida

El regulador de nitidez va de **0,00** (sin máscara de nitidez) a **1,50**. El valor inicial **0,60** reproduce el ajuste de `upscale4k`; subirlo puede aumentar halos y ruido. La nitidez se aplica tras ajustar al tamaño final.

Se exporta en PNG, JPEG (calidad 94) o WebP (calidad 95). Los resultados se guardan junto a un nombre que incluye método, dimensiones y tipo de ajuste; si ya existe, se añade un número. El origen no se sobrescribe. La imagen se auto-orienta antes de procesar y todos los pasos se ejecutan localmente.

## Instalar el DEB

En una versión de Ubuntu compatible con ImageMagick 7:

```bash
sudo apt install ./upscale-studio_0.1.1_amd64.deb
```

APT detecta los paquetes presentes e instala los que falten de las dependencias declaradas: Python 3, PyQt6, Pillow, ImageMagick 7, cargador Vulkan y libgomp. El DEB **incluye** el ejecutable Real-ESRGAN NCNN Vulkan, los dos modelos usados y el icono. No descarga modelos durante la ejecución. `dpkg -i` por sí solo no resuelve dependencias; usar APT.

Los modos de IA requieren una GPU con controlador Vulkan operativo. El DEB no instala automáticamente el controlador del fabricante, porque depende de la GPU y la distribución; Lanczos funciona sin GPU. La aplicación avisa de componentes básicos ausentes y muestra el error del motor si Vulkan no está operativo. No pide credenciales ni envía imágenes a servicios externos.

Tras instalar, aparece como **Upscale Studio** en el menú de aplicaciones con el icono incluido en este proyecto. La ventana usa el mismo icono y declara el ID de escritorio para asociarse a la barra de aplicaciones abiertas. Si estaba abierta una versión anterior, hay que cerrarla y volver a iniciarla. El icono puede tardar unos segundos en actualizarse por la caché del entorno gráfico.

## Ejecutar desde el proyecto y reconstruir

```bash
python3 app.py
./build-deb.sh
```

Sin instalar, usa el motor de `~/.local/share/realesrgan`. Para elegir otro: `UPSCALE_STUDIO_ENGINE_DIR=/ruta/al/motor python3 app.py`. Desde el proyecto, la ventana carga el icono de `icons/`. El script de construcción utiliza una copia local del motor y los modelos y genera el DEB en `dist/`; arquitectura amd64. Los tamaños del icono PNG para el paquete están en `icons/`.

Real-ESRGAN: BSD-3-Clause; ejecutable NCNN: MIT y licencias de componentes indicadas en `LICENSE-NCNN`. Ambos textos se incluyen en el DEB. El ejecutable usado para construir esta versión coincide byte a byte con el ZIP de Real-ESRGAN NCNN Vulkan 20220424 ya presente en este equipo.

## Licencia

Las licencias de los componentes de terceros distribuidos en el DEB están en `LICENSE-Real-ESRGAN` y `LICENSE-NCNN`. El código propio de esta aplicación no tiene una licencia de reutilización publicada por ahora.
