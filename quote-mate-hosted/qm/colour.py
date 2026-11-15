"""Colour helpers: a business on the full plan can choose its own accent colour, and the pages must stay readable."""
import re

CHARCOAL = "#1B1D21"          # the page background the accent is read against
DARK_TEXT, LIGHT_TEXT = "#0B1220", "#FFFFFF"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def on_accent(accent):
    """Dark or white text, whichever reads better on a button of this colour."""
    return DARK_TEXT if contrast(DARK_TEXT, accent) >= contrast(LIGHT_TEXT, accent) else LIGHT_TEXT


def check_accent(value):
    """'' (use the crew blue) or a #RRGGBB colour that is readable as text on the dark page. Returns it normalised."""
    value = str(value or "").strip()
    if not value:
        return ""
    if not HEX.match(value):
        raise ValueError("the colour must look like #3D8BFF")
    value = value.upper()
    if contrast(value, CHARCOAL) < 4.5:
        raise ValueError("that colour is too dark to read on the dark background. Pick a lighter one")
    return value
