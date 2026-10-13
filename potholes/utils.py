from PIL import Image
from io import BytesIO


def rgb565_to_jpeg(
    raw_data,
    width,
    height,
    quality=85,
    byte_order="little",
):
    """
    Convert raw RGB565 bytes to JPEG.

    Args:
        raw_data: Raw RGB565 image bytes.
        width: Actual frame width.
        height: Actual frame height.
        quality: JPEG quality from 1 to 95.
        byte_order: "little" or "big".

    Returns:
        BytesIO containing the JPEG image.
    """

    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive")

    expected_size = width * height * 2

    if len(raw_data) != expected_size:
        raise ValueError(
            f"Invalid RGB565 size: expected {expected_size} "
            f"bytes for {width}x{height}, "
            f"received {len(raw_data)} bytes"
        )

    if byte_order not in ("little", "big"):
        raise ValueError("byte_order must be 'little' or 'big'")

    # Interpret each pair of bytes as one RGB565 pixel.
    rgb = bytearray(width * height * 3)
    out = 0

    for i in range(0, expected_size, 2):

        if byte_order == "little":
            value = raw_data[i] | (raw_data[i + 1] << 8)
        else:
            value = (raw_data[i] << 8) | raw_data[i + 1]

        # Extract RGB565 channels.
        r = (value >> 11) & 0x1F
        g = (value >> 5) & 0x3F
        b = value & 0x1F

        # Expand channels to 8-bit RGB.
        rgb[out] = (r * 255) // 31
        rgb[out + 1] = (g * 255) // 63
        rgb[out + 2] = (b * 255) // 31

        out += 3

    image = Image.frombytes(
        "RGB",
        (width, height),
        bytes(rgb),
    )

    output = BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=quality,
    )

    output.seek(0)
    return output