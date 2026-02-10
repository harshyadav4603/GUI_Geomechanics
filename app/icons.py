"""
Icon generation utilities – creates SVG-style icons as PIL Images
so the app works without shipping external icon files.
"""

from PIL import Image, ImageDraw, ImageFont
import math


def _new(size=64, bg="#1a1a2e"):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    return img, draw


def _circle(draw, cx, cy, r, **kw):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], **kw)


# ── Individual icon generators ────────────────────────────────────

def icon_home(size=64, color="#00d4ff"):
    img, d = _new(size)
    m = size // 2
    pad = size // 8
    # roof
    d.polygon([(m, pad), (size - pad, m), (pad, m)], fill=color)
    # body
    d.rectangle([pad + size // 8, m, size - pad - size // 8, size - pad], fill=color)
    # door
    dw = size // 8
    d.rectangle([m - dw, size - pad - size // 4, m + dw, size - pad], fill="#1a1a2e")
    return img


def icon_stress(size=64, color="#ff6b6b"):
    img, d = _new(size)
    m = size // 2
    pad = size // 6
    lw = max(3, size // 16)
    # σ arrows (compression arrows pointing inward)
    # Horizontal arrows
    d.line([(pad, m), (size - pad, m)], fill=color, width=lw)
    # Arrow heads left
    d.polygon([(pad + size // 6, m - size // 10), (pad, m), (pad + size // 6, m + size // 10)], fill=color)
    # Arrow heads right
    d.polygon([(size - pad - size // 6, m - size // 10), (size - pad, m),
               (size - pad - size // 6, m + size // 10)], fill=color)
    # Vertical arrows
    d.line([(m, pad), (m, size - pad)], fill=color, width=lw)
    d.polygon([(m - size // 10, pad + size // 6), (m, pad), (m + size // 10, pad + size // 6)], fill=color)
    d.polygon([(m - size // 10, size - pad - size // 6), (m, size - pad),
               (m + size // 10, size - pad - size // 6)], fill=color)
    # Center circle
    _circle(d, m, m, size // 8, outline=color, width=lw)
    return img


def icon_moduli(size=64, color="#feca57"):
    img, d = _new(size)
    pad = size // 6
    lw = max(3, size // 16)
    w = size - 2 * pad
    h = size - 2 * pad
    # Stress-strain curve axes
    d.line([(pad, size - pad), (pad, pad)], fill=color, width=lw)  # Y axis
    d.line([(pad, size - pad), (size - pad, size - pad)], fill=color, width=lw)  # X axis
    # Curve (linear elastic then yielding)
    pts = []
    for i in range(20):
        t = i / 19.0
        x = pad + int(t * w)
        if t < 0.5:
            y = size - pad - int((t / 0.5) * h * 0.7)
        else:
            y = size - pad - int((0.7 + 0.25 * math.sin((t - 0.5) * math.pi)) * h)
        pts.append((x, y))
    d.line(pts, fill=color, width=lw + 1)
    return img


def icon_rock_physics(size=64, color="#48dbfb"):
    img, d = _new(size)
    m = size // 2
    pad = size // 6
    lw = max(2, size // 20)
    # Layered rock representation
    colors_layers = [color, "#2ed573", color, "#2ed573"]
    layer_h = (size - 2 * pad) // len(colors_layers)
    for i, c in enumerate(colors_layers):
        y0 = pad + i * layer_h
        y1 = y0 + layer_h
        d.rectangle([pad, y0, size - pad, y1], fill=c, outline="#1a1a2e", width=2)
    # Grain dots
    for angle in range(0, 360, 45):
        cx = m + int(size // 5 * math.cos(math.radians(angle)))
        cy = m + int(size // 5 * math.sin(math.radians(angle)))
        _circle(d, cx, cy, size // 18, fill="#ffffff")
    return img


def icon_strength(size=64, color="#ff9ff3"):
    img, d = _new(size)
    m = size // 2
    pad = size // 6
    lw = max(3, size // 16)
    # Mohr circle
    r = size // 4
    _circle(d, m, m, r, outline=color, width=lw)
    # Failure envelope (tangent lines)
    d.line([(pad, m + r + size // 10), (size - pad, pad)], fill=color, width=lw)
    d.line([(pad, m - r - size // 10 + size // 3), (size - pad, size - pad)], fill=color, width=lw)
    # Sigma axis
    d.line([(pad // 2, m), (size - pad // 2, m)], fill="#aaaaaa", width=max(1, lw // 2))
    return img


def icon_wellbore(size=64, color="#00d2d3"):
    img, d = _new(size)
    m = size // 2
    pad = size // 6
    lw = max(3, size // 16)
    # Outer wellbore circle
    r_out = size // 3
    _circle(d, m, m, r_out, outline=color, width=lw)
    # Inner hole
    r_in = size // 7
    _circle(d, m, m, r_in, fill="#1a1a2e", outline=color, width=lw)
    # Radial stress lines
    for angle in [0, 45, 90, 135, 180, 225, 270, 315]:
        x1 = m + int((r_in + 2) * math.cos(math.radians(angle)))
        y1 = m + int((r_in + 2) * math.sin(math.radians(angle)))
        x2 = m + int((r_out - 2) * math.cos(math.radians(angle)))
        y2 = m + int((r_out - 2) * math.sin(math.radians(angle)))
        d.line([(x1, y1), (x2, y2)], fill=color, width=max(1, lw // 2))
    return img


def icon_upload(size=64, color="#2ed573"):
    img, d = _new(size)
    m = size // 2
    pad = size // 5
    lw = max(3, size // 14)
    # Upload arrow
    d.line([(m, size - pad), (m, pad + size // 6)], fill=color, width=lw)
    arr = size // 6
    d.polygon([(m - arr, pad + arr + size // 8), (m, pad), (m + arr, pad + arr + size // 8)], fill=color)
    # Base tray
    d.arc([pad, size - pad - size // 5, size - pad, size - pad + size // 5], 0, 180, fill=color, width=lw)
    return img


ICON_MAP = {
    "home":      icon_home,
    "stress":    icon_stress,
    "moduli":    icon_moduli,
    "rock":      icon_rock_physics,
    "strength":  icon_strength,
    "wellbore":  icon_wellbore,
    "upload":    icon_upload,
}


def get_icon(name, size=40):
    """Return a CTkImage-ready PIL Image for the given icon name."""
    fn = ICON_MAP.get(name)
    if fn:
        return fn(size)
    # Fallback: colored square
    img = Image.new("RGBA", (size, size), "#555555")
    return img
