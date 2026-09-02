#!/opt/homebrew/bin/python3
"""Generate the Lazy Downloader icon: black rounded square + green terminal prompt."""
import math, struct, zlib

W = H = 1024
GREEN = (0x00, 0xFF, 0x00)
BLACK = (0x00, 0x00, 0x00)

def rounded_rect_sd(px, py, cx, cy, half_w, half_h, r):
    qx = abs(px - cx) - (half_w - r)
    qy = abs(py - cy) - (half_h - r)
    outside = math.hypot(max(qx, 0), max(qy, 0))
    inside = min(max(qx, qy), 0)
    return outside + inside - r  # negative = inside

def cov(d, aa=1.5):
    if d <= -aa: return 1.0
    if d >= aa: return 0.0
    x = (aa - d) / (2 * aa)
    return x * x * (3 - 2 * x)

def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        return math.hypot(px - ax, py - ay)
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return math.hypot(px - bx, py - by)
    t = c1 / c2
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))

def stroke_cov(px, py, ax, ay, bx, by, half_w, aa=1.5):
    return cov(seg_dist(px, py, ax, ay, bx, by) - half_w, aa)

def rect_cov(px, py, x0, y0, x1, y1, aa=1.5):
    if x0 <= px <= x1 and y0 <= py <= y1:
        return 1.0
    dx = max(x0 - px, px - x1, 0)
    dy = max(y0 - py, py - y1, 0)
    d = math.hypot(dx, dy)
    return cov(d, aa)

# ── Geometry ──
# Rounded square: full-bleed with rounded corners
SQ_CX, SQ_CY = 512, 512
SQ_HALF = 510
SQ_R = 180
BORDER = 12  # green border thickness

# Down arrow — shaft, arrowhead (two edges to a bottom tip), plus a tray line below
SHAFT_X, SHAFT_Y0, SHAFT_Y1 = 512, 320, 540   # vertical shaft
SHAFT_W = 46
TIP_X, TIP_Y = 512, 668                        # arrowhead tip (bottom point)
LSHOULDER_X, LSHOULDER_Y = 392, 540            # left shoulder
RSHOULDER_X, RSHOULDER_Y = 632, 540            # right shoulder
EDGE_W = 46                                     # arrowhead edge thickness
TRAY_X0, TRAY_X1, TRAY_Y = 368, 656, 736       # baseline tray under the arrow
TRAY_W = 28

pixels = bytearray(W * H * 4)

for y in range(H):
    for x in range(W):
        # 1. Rounded square fill (black), with green border
        sd_outer = rounded_rect_sd(x, y, SQ_CX, SQ_CY, SQ_HALF, SQ_HALF, SQ_R)
        sd_inner = rounded_rect_sd(x, y, SQ_CX, SQ_CY, SQ_HALF - BORDER, SQ_HALF - BORDER, SQ_R - BORDER)

        is_black = sd_outer <= 0
        is_green_border = sd_outer <= 0 and sd_inner > 0

        # 2. Down arrow (green): shaft + two arrowhead edges + tray line
        shaft = stroke_cov(x, y, SHAFT_X, SHAFT_Y0, SHAFT_X, SHAFT_Y1, SHAFT_W)
        edge_l = stroke_cov(x, y, LSHOULDER_X, LSHOULDER_Y, TIP_X, TIP_Y, EDGE_W)
        edge_r = stroke_cov(x, y, RSHOULDER_X, RSHOULDER_Y, TIP_X, TIP_Y, EDGE_W)
        tray = stroke_cov(x, y, TRAY_X0, TRAY_Y, TRAY_X1, TRAY_Y, TRAY_W)

        arrow = max(shaft, edge_l, edge_r, tray)

        green = arrow
        if is_green_border:
            green = 1.0

        if is_black:
            r = g = b = 0
            # blend green over black
            if green > 0:
                g = int(255 * green)
                r = 0
            # subtle: keep green pure
            a = 255
        else:
            # outside the square → transparent
            r = g = b = a = 0

        idx = (y * W + x) * 4
        pixels[idx] = r
        pixels[idx + 1] = g
        pixels[idx + 2] = b
        pixels[idx + 3] = a

# ── Write PNG ──
def png_chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c

raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: none
    row_start = y * W * 4
    raw.extend(pixels[row_start:row_start + W * 4])

ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)  # 8-bit RGBA
png = b"\x89PNG\r\n\x1a\n"
png += png_chunk(b"IHDR", ihdr)
png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
png += png_chunk(b"IEND", b"")

out = "/tmp/lazy-icon-1024.png"
with open(out, "wb") as f:
    f.write(png)
print("wrote", out, len(png), "bytes")
