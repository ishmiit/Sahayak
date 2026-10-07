"""Photos and screenshots from phones, decoded safely for the QR and screenshot readers.

A small file can declare a huge picture: a 0.9 MB PNG can unpack to 900 MB, and decoding it took the
node from 0.7 GB to 1.8 GB of memory. So the size is read from the file's header first, and anything
larger than any phone camera makes is refused before a single pixel is decoded.
"""
from __future__ import annotations

import io

import numpy as np

MAX_PIXELS = 64_000_000  # a 50-megapixel phone photo is about 8160 x 6120


class ImageError(ValueError):
    pass


def load(image: bytes, *, color: bool, longest: int) -> np.ndarray:
    """The picture in `image` as an OpenCV array, shrunk so its longest side is at most `longest`."""
    import cv2
    from PIL import Image, UnidentifiedImageError
    if not image:
        raise ImageError("no image")
    try:
        with Image.open(io.BytesIO(image)) as im:  # reads the header only
            w, h = im.size
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError):
        raise ImageError("not an image") from None
    if w * h > MAX_PIXELS:
        raise ImageError("image too large")
    try:
        img = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE)
    except cv2.error:
        img = None
    if img is None:
        raise ImageError("not an image")
    h, w = img.shape[:2]
    if max(h, w) > longest:  # phone photos are large; reading is faster and as good when smaller
        scale = longest / max(h, w)
        img = cv2.resize(img, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    return img
