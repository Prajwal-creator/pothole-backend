from PIL import Image
from io import BytesIO


def rgb565_to_jpeg(
    raw_data,
    width,
    height,
    quality=85
):
    """
    Convert raw RGB565 bytes into JPEG.

    Expected:
        width  = 240
        height = 240

    RGB565:
        16 bits / pixel
        2 bytes / pixel
    """

    expected_size = width * height * 2

    if len(raw_data) != expected_size:
        raise ValueError(
            f"Invalid RGB565 size. "
            f"Expected {expected_size}, "
            f"received {len(raw_data)}"
        )

    rgb = bytearray(
        width * height * 3
    )

    out = 0

    for i in range(0, len(raw_data), 2):

        # ESP32 RGB565 byte order
        value = (
            raw_data[i]
            | (raw_data[i + 1] << 8)
        )

        # RGB565
        r = (value >> 11) & 0x1F
        g = (value >> 5) & 0x3F
        b = value & 0x1F

        # Convert to 8-bit RGB
        r = (r * 255) // 31
        g = (g * 255) // 63
        b = (b * 255) // 31

        rgb[out] = r
        rgb[out + 1] = g
        rgb[out + 2] = b

        out += 3

    image = Image.frombytes(
        "RGB",
        (width, height),
        bytes(rgb)
    )

    output = BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=quality
    )

    output.seek(0)

    return output