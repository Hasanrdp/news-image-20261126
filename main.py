#!/usr/bin/env python3
"""The World Today - Thursday 26 November 2026.

make.fun news-image-20261126 entry. Pure standard library, no network,
fully deterministic: the program draws a one-page newspaper front page
that sums up the world's news of Thursday 26 November 2026 and writes it
to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Layout (1024 x 1024):
  * masthead with the paper name and the date, twice, so the day the
    image sums up is unmistakable;
  * one large lead story with a drawn launch scene: North Korea's Kim
    Jong Un ordering a wider deployment of tactical nuclear weapons,
    reported by KCNA on Thursday 26 November;
  * 49 further dated stories from 10 regions and fields, in a 5 by 10
    grid, each with a small drawn pictogram, a region tag and the
    date 26 NOV;
  * a footer repeating the date and the story count.

Every headline below is a real story first reported on 26 November 2026
(Reuters world news summary, KCNA via Reuters, and the day's wire
round-ups). Nothing is invented: numbers are only used where the wires
reported them.

Determinism: no clock, no randomness, no I/O besides the single output
file. Two runs write byte-identical PNGs; the program pins its own
expected output hash and byte count and refuses to finish silently if
either ever changes.
"""

import binascii
import hashlib
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- PNG out

def png_bytes(rgb, w, h):
    """Encode a flat RGB bytearray as a PNG (filter 0 on every row)."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- canvas

PAPER = (247, 242, 232)
INK = (20, 20, 20)
RED = (176, 30, 36)
NAVY = (18, 33, 61)
NAVY2 = (28, 52, 96)
BLUE = (29, 78, 137)
GOLD = (200, 160, 40)
TEAL = (15, 120, 110)
GREEN = (34, 120, 60)
ORANGE = (214, 110, 20)
GREY = (110, 110, 105)
LIGHT = (235, 230, 218)
WHITE = (255, 255, 255)
SKY = (52, 84, 138)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)
        self.clip = None  # (x0, y0, x1, y1) or None

    def set_clip(self, x0, y0, x1, y1):
        self.clip = (x0, y0, x1, y1)

    def clear_clip(self):
        self.clip = None

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            if self.clip is not None:
                cx0, cy0, cx1, cy1 = self.clip
                if not (cx0 <= x < cx1 and cy0 <= y < cy1):
                    return
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if self.clip is not None:
            cx0, cy0, cx1, cy1 = self.clip
            x0 = max(x0, cx0)
            y0 = max(y0, cy0)
            x1 = min(x1, cx1)
            y1 = min(y1, cy1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def border(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, dx * 2 + 1, 1, c)

    def disc(self, cx, cy, r, c):
        self.circle(cx, cy, r, c)

    def ring(self, cx, cy, r, c, t=2):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            for xx in (cx - dx, cx + dx):
                for k in range(t):
                    self.set(xx - k if xx == cx - dx else xx + k, cy + dy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for a in range(t):
                for b in range(t):
                    self.set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def tri(self, ax, ay, bx, by, cx, cy, c):
        """Filled triangle by scanlines."""
        pts = sorted([(ax, ay), (bx, by), (cx, cy)], key=lambda p: p[1])
        (x0, y0), (x1, y1), (x2, y2) = pts
        if y0 == y2:
            return
        def edge(xa, ya, xb, yb, y):
            if yb == ya:
                return xa
            return xa + (xb - xa) * (y - ya) / (yb - ya)
        for y in range(y0, y2 + 1):
            if y < y1:
                xa = edge(x0, y0, x1, y1, y)
                xb = edge(x0, y0, x2, y2, y)
            else:
                xa = edge(x1, y1, x2, y2, y)
                xb = edge(x0, y0, x2, y2, y)
            if xa > xb:
                xa, xb = xb, xa
            self.rect(int(xa), y, int(xb) - int(xa) + 1, 1, c)


# ------------------------------------------------------- 5x7 bitmap font
# Each glyph is 7 strings of 5 bits. Uppercase only; all entry text is
# set in capitals, newspaper style.

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
}

BLANK = ("00000",) * 7


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, color, text):
    """Draw uppercase text, left aligned, at integer scale s."""
    cx = x
    for ch in text:
        g = FONT.get(ch, BLANK)
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(cx + col * s, y + row * s, s, s, color)
        cx += 6 * s
    return cx


def draw_text_c(cv, cx, y, s, color, text):
    draw_text(cv, cx - text_width(text, s) // 2, y, s, color, text)


def wrap(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    lines = []
    for word in text.split(" "):
        if not lines or len(lines[-1]) + 1 + len(word) > max_chars:
            lines.append(word)
        else:
            lines[-1] += " " + word
    return lines

# ------------------------------------------------------------ pictograms
# Every story tile carries one small drawn pictogram in a coloured
# square, so each story reads from its picture as well as its words.

def icon_bg(cv, x, y, s, color):
    cv.rect(x, y, s, s, color)
    cv.border(x, y, s, s, INK, 1)


def icon_rocket(cv, x, y, s, fg=WHITE):
    # rocket body, nose, fins, flame
    u = s // 24
    cv.rect(x + 10 * u, y + 3 * u, 4 * u, 12 * u, fg)
    cv.tri(x + 10 * u, y + 3 * u, x + 14 * u, y + 3 * u, x + 12 * u, y, RED)
    cv.tri(x + 10 * u, y + 12 * u, x + 7 * u, y + 17 * u, x + 10 * u, y + 15 * u, RED)
    cv.tri(x + 14 * u, y + 12 * u, x + 17 * u, y + 17 * u, x + 14 * u, y + 15 * u, RED)
    cv.disc(x + 12 * u, y + 8 * u, 2 * u, SKY)
    cv.tri(x + 11 * u, y + 15 * u, x + 13 * u, y + 15 * u, x + 12 * u, y + 22 * u, GOLD)
    cv.tri(x + 11 * u, y + 15 * u, x + 13 * u, y + 15 * u, x + 12 * u, y + 19 * u, ORANGE)


def icon_chart(cv, x, y, s, fg=WHITE):
    u = s // 24
    for i, h in enumerate((6, 11, 8, 14, 18)):
        cv.rect(x + (3 + i * 4) * u, y + (21 - h) * u, 3 * u, h * u, fg)
    cv.line(x + 2 * u, y + 21 * u, x + 22 * u, y + 21 * u, fg, 1)
    cv.line(x + 3 * u, y + 4 * u, x + 21 * u, y + 4 * u, GOLD, 1)


def icon_plane(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.rect(x + 2 * u, y + 11 * u, 20 * u, 3 * u, fg)
    cv.tri(x + 20 * u, y + 11 * u, x + 23 * u, y + 12 * u, x + 20 * u, y + 14 * u, fg)
    cv.rect(x + 8 * u, y + 6 * u, 3 * u, 5 * u, fg)
    cv.rect(x + 8 * u, y + 14 * u, 3 * u, 5 * u, fg)
    cv.rect(x + 4 * u, y + 14 * u, 2 * u, 6 * u, fg)


def icon_blast(cv, x, y, s, fg=WHITE):
    u = s // 24
    cx, cy = x + 12 * u, y + 12 * u
    for ang in range(0, 360, 30):
        import math
        r1, r2 = 4 * u, 11 * u
        a = math.radians(ang)
        cv.line(cx, cy, int(cx + r2 * math.cos(a)), int(cy + r2 * math.sin(a)), fg, 2)
    cv.disc(cx, cy, 4 * u, GOLD)
    cv.disc(cx, cy, 2 * u, RED)


def icon_flame(cv, x, y, s, fg=WHITE):
    u = s // 24
    cx = x + 12 * u
    cv.tri(cx - 6 * u, y + 18 * u, cx + 6 * u, y + 18 * u, cx, y + 3 * u, fg)
    cv.disc(cx, y + 15 * u, 5 * u, GOLD)
    cv.disc(cx, y + 17 * u, 3 * u, ORANGE)


def icon_ship(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.rect(x + 3 * u, y + 13 * u, 18 * u, 5 * u, fg)
    cv.tri(x + 3 * u, y + 13 * u, x + 21 * u, y + 13 * u, x + 18 * u, y + 18 * u, fg)
    cv.rect(x + 6 * u, y + 8 * u, 4 * u, 5 * u, GOLD)
    cv.rect(x + 11 * u, y + 8 * u, 4 * u, 5 * u, fg)
    cv.rect(x + 16 * u, y + 8 * u, 4 * u, 5 * u, GOLD)
    cv.line(x + 12 * u, y + 3 * u, x + 12 * u, y + 8 * u, fg, 1)
    cv.rect(x + 2 * u, y + 20 * u, 20 * u, 1 * u, SKY)


def icon_coin(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.disc(x + 12 * u, y + 12 * u, 9 * u, GOLD)
    cv.ring(x + 12 * u, y + 12 * u, 9 * u, fg, 1)
    cv.rect(x + 11 * u, y + 6 * u, 2 * u, 12 * u, fg)
    cv.rect(x + 8 * u, y + 9 * u, 8 * u, 2 * u, fg)
    cv.rect(x + 8 * u, y + 13 * u, 8 * u, 2 * u, fg)


def icon_dome(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.rect(x + 3 * u, y + 19 * u, 18 * u, 2 * u, fg)
    for i in range(4):
        cv.rect(x + (4 + i * 5) * u, y + 12 * u, 2 * u, 7 * u, fg)
    cv.rect(x + 3 * u, y + 11 * u, 18 * u, 1 * u, fg)
    cv.tri(x + 4 * u, y + 11 * u, x + 20 * u, y + 11 * u, x + 12 * u, y + 3 * u, GOLD)
    cv.disc(x + 12 * u, y + 3 * u, 1 * u, fg)


def icon_gavel(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 5 * u, y + 19 * u, x + 19 * u, y + 5 * u, fg, 3)
    cv.rect(x + 13 * u, y + 3 * u, 8 * u, 4 * u, GOLD)
    cv.rect(x + 3 * u, y + 19 * u, 8 * u, 2 * u, fg)


def icon_shield(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.tri(x + 4 * u, y + 4 * u, x + 20 * u, y + 4 * u, x + 12 * u, y + 8 * u, fg)
    cv.rect(x + 4 * u, y + 4 * u, 16 * u, 8 * u, fg)
    cv.tri(x + 4 * u, y + 12 * u, x + 20 * u, y + 12 * u, x + 12 * u, y + 21 * u, fg)
    cv.line(x + 8 * u, y + 12 * u, x + 11 * u, y + 15 * u, NAVY, 2)
    cv.line(x + 11 * u, y + 15 * u, x + 16 * u, y + 8 * u, NAVY, 2)


def icon_scale(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 12 * u, y + 3 * u, x + 12 * u, y + 19 * u, fg, 2)
    cv.line(x + 4 * u, y + 6 * u, x + 20 * u, y + 6 * u, fg, 2)
    cv.line(x + 4 * u, y + 6 * u, x + 4 * u, y + 11 * u, fg, 1)
    cv.line(x + 20 * u, y + 6 * u, x + 20 * u, y + 11 * u, fg, 1)
    cv.tri(x + 1 * u, y + 11 * u, x + 7 * u, y + 11 * u, x + 4 * u, y + 15 * u, GOLD)
    cv.tri(x + 17 * u, y + 11 * u, x + 23 * u, y + 11 * u, x + 20 * u, y + 15 * u, GOLD)
    cv.rect(x + 7 * u, y + 19 * u, 10 * u, 2 * u, fg)


def icon_flag(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 5 * u, y + 3 * u, x + 5 * u, y + 21 * u, fg, 2)
    cv.tri(x + 5 * u, y + 3 * u, x + 20 * u, y + 7 * u, x + 5 * u, y + 11 * u, RED)
    cv.disc(x + 5 * u, y + 3 * u, 1 * u, GOLD)


def icon_satellite(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.rect(x + 9 * u, y + 9 * u, 6 * u, 6 * u, GOLD)
    cv.rect(x + 2 * u, y + 10 * u, 6 * u, 4 * u, fg)
    cv.rect(x + 16 * u, y + 10 * u, 6 * u, 4 * u, fg)
    cv.line(x + 12 * u, y + 15 * u, x + 12 * u, y + 21 * u, fg, 1)
    cv.line(x + 3 * u, y + 5 * u, x + 9 * u, y + 9 * u, fg, 1)
    cv.line(x + 21 * u, y + 5 * u, x + 15 * u, y + 9 * u, fg, 1)


def icon_asteroid(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.disc(x + 12 * u, y + 12 * u, 8 * u, fg)
    cv.disc(x + 9 * u, y + 9 * u, 2 * u, GREY)
    cv.disc(x + 15 * u, y + 14 * u, 3 * u, GREY)
    cv.disc(x + 12 * u, y + 16 * u, 1 * u, GREY)


def icon_chess(cv, x, y, s, fg=WHITE):
    u = s // 24
    for r in range(4):
        for c in range(4):
            col = fg if (r + c) % 2 == 0 else NAVY
            cv.rect(x + (3 + c * 4) * u, y + (3 + r * 4) * u, 4 * u, 4 * u, col)
    cv.border(x + 3 * u, y + 3 * u, 16 * u, 16 * u, INK, 1)


def icon_cricket(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 6 * u, y + 4 * u, x + 17 * u, y + 18 * u, fg, 3)
    cv.rect(x + 15 * u, y + 16 * u, 6 * u, 2 * u, fg)
    cv.disc(x + 18 * u, y + 7 * u, 3 * u, RED)


def icon_music(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 15 * u, y + 4 * u, x + 15 * u, y + 16 * u, fg, 2)
    cv.line(x + 15 * u, y + 4 * u, x + 8 * u, y + 7 * u, fg, 2)
    cv.line(x + 8 * u, y + 7 * u, x + 8 * u, y + 16 * u, fg, 2)
    cv.disc(x + 6 * u, y + 17 * u, 3 * u, fg)
    cv.disc(x + 13 * u, y + 17 * u, 3 * u, fg)


def icon_oil(cv, x, y, s, fg=WHITE):
    u = s // 24
    cv.line(x + 5 * u, y + 20 * u, x + 12 * u, y + 4 * u, fg, 2)
    cv.line(x + 19 * u, y + 20 * u, x + 12 * u, y + 4 * u, fg, 2)
    cv.line(x + 8 * u, y + 13 * u, x + 16 * u, y + 13 * u, fg, 2)
    cv.line(x + 10 * u, y + 8 * u, x + 14 * u, y + 8 * u, fg, 2)
    cv.rect(x + 11 * u, y + 2 * u, 2 * u, 3 * u, GOLD)


ICONS = {
    "rocket": icon_rocket, "chart": icon_chart, "plane": icon_plane,
    "blast": icon_blast, "flame": icon_flame, "ship": icon_ship,
    "coin": icon_coin, "dome": icon_dome, "gavel": icon_gavel,
    "shield": icon_shield, "scale": icon_scale, "flag": icon_flag,
    "satellite": icon_satellite, "asteroid": icon_asteroid,
    "chess": icon_chess, "cricket": icon_cricket, "music": icon_music,
    "oil": icon_oil,
}

REGION_COLORS = {
    "ASIA": (176, 30, 36), "EUROPE": (29, 78, 137), "MIDEAST": (15, 120, 110),
    "AMERICAS": (120, 60, 140), "AFRICA": (214, 110, 20), "PACIFIC": (15, 120, 110),
    "SCIENCE": (40, 90, 160), "SPORT": (34, 120, 60), "BUSINESS": (140, 100, 20),
    "CULTURE": (160, 40, 90),
}

# ------------------------------------------------------------- the stories
# (headline, region, icon) - 49 grid stories + 1 lead story = 50 stories
# from 10 regions, all first reported on Thursday 26 November 2026.
# Headlines are kept short so each fits its tile in two lines.

STORIES = [
    ("PAKISTANI IN ORBIT", "ASIA", "rocket"),
    ("US TARIFFS HIT 14", "AMERICAS", "chart"),
    ("UKRAINE HITS AIR BASE", "EUROPE", "plane"),
    ("RUSSIA STRIKES KYIV", "EUROPE", "blast"),
    ("SAUDI REFINERY HIT", "MIDEAST", "flame"),
    ("MINES HIT IN HORMUZ", "MIDEAST", "ship"),
    ("GAZA: HAMAS KILLED", "MIDEAST", "blast"),
    ("BANGLADESH WAGE UP 36%", "ASIA", "coin"),
    ("26/11: 18 YEARS ON", "ASIA", "dome"),
    ("SUDAN DRONES KILL 19", "AFRICA", "blast"),
    ("EGYPT FIRE KILLS 31", "AFRICA", "flame"),
    ("NIGERIA: 30 KILLED", "AFRICA", "blast"),
    ("CULT LEADER CONVICTED", "AFRICA", "gavel"),
    ("20 HOSTAGES FREED", "AMERICAS", "shield"),
    ("VENEZUELA 237.5 BN", "AMERICAS", "coin"),
    ("PETROBRAS PLANS 122 BN", "AMERICAS", "oil"),
    ("MURMANSK CHIEF HELD", "EUROPE", "gavel"),
    ("34 NATIONS: HALT GAS", "EUROPE", "scale"),
    ("PYONGYANG EXPELS SWISS", "ASIA", "flag"),
    ("2ND AIRPORT: LEBANON", "MIDEAST", "plane"),
    ("IRAN READY FOR BLOCKADE", "MIDEAST", "ship"),
    ("JUDGE BLOCKS TRUMP ORDER", "AMERICAS", "gavel"),
    ("PLANE CRASH: SIX DEAD", "AMERICAS", "plane"),
    ("PROBE AT MERCURY", "SCIENCE", "satellite"),
    ("ASTEROID CRATER FOUND", "SCIENCE", "asteroid"),
    ("GUKESH DRAWS FINAL", "SPORT", "chess"),
    ("TEEN SMASHES RECORD 204", "SPORT", "cricket"),
    ("1,220 FOR IPL SALE", "SPORT", "cricket"),
    ("FLIPKART CEO TO STEP DOWN", "BUSINESS", "chart"),
    ("DURAN DURAN STAR DIES", "CULTURE", "music"),
    ("SOLOMON ISLES PACT", "PACIFIC", "shield"),
    ("INDIA-NEPAL AID DEAL", "ASIA", "coin"),
    ("XI PROBES SHANGHAI", "ASIA", "gavel"),
    ("MALAYSIA SUES GOOGLE", "ASIA", "gavel"),
    ("MINE FLOOD KILLS 9", "ASIA", "blast"),
    ("IITS ADD 6,000 SEATS", "ASIA", "dome"),
    ("UK MOVES WARPLANES", "EUROPE", "plane"),
    ("NATO CALLS URGENT MEET", "EUROPE", "shield"),
    ("FTSE 100 EDGES UP", "EUROPE", "chart"),
    ("HOUTHI DRONE HITS TOWER", "MIDEAST", "blast"),
    ("QATAR GP GOES AHEAD", "MIDEAST", "flag"),
    ("BRAZIL VIRUS DOWN 68%", "AMERICAS", "chart"),
    ("NVIDIA FACES SENATE", "AMERICAS", "scale"),
    ("TRUMP'S TURKEYS", "AMERICAS", "flag"),
    ("RAMAPHOSA WINS CASE", "AFRICA", "gavel"),
    ("OPENAI SORRY OVER FILES", "PACIFIC", "scale"),
    ("AUSSIE PRICES UP", "PACIFIC", "chart"),
    ("HERA EYES ASTEROID", "SCIENCE", "asteroid"),
    ("A KIDMAN CAROL OPENS", "CULTURE", "music"),
]

LEAD_KICKER = "NORTH KOREA  -  26 NOV 2026"
LEAD_HEAD = ["KIM ORDERS MORE", "TACTICAL NUCLEAR", "WEAPONS"]
LEAD_SUB = ("KCNA: OUTPUT EXPANDING. STATUS AS NUCLEAR STATE "
            "IS ABSOLUTELY INVIOLABLE.")

# ------------------------------------------------------------- the page

def draw_masthead(cv):
    # Top black band: edition line.
    cv.rect(0, 0, W, 30, INK)
    draw_text(cv, 14, 8, 2, WHITE, "ONE DAY  -  ONE IMAGE  -  THE WORLD IN BRIEF")
    draw_text(cv, W - 14 - text_width("26 NOVEMBER 2026", 2), 8, 2, GOLD, "26 NOVEMBER 2026")
    # Paper name.
    draw_text_c(cv, W // 2, 44, 7, INK, "THE WORLD TODAY")
    draw_text_c(cv, W // 2, 100, 3, RED, "THURSDAY 26 NOVEMBER 2026")
    cv.hline(24, 130, W - 48, INK, 3)
    cv.hline(24, 136, W - 48, RED, 2)


def draw_lead_scene(cv, x, y, w, h):
    """Drawn launch scene: night sky, moon, stars, a rocket climbing
    from a pad over dark hills, smoke curling below it. Everything is
    clipped to the scene rectangle so nothing spills onto the page."""
    cv.set_clip(x, y, x + w, y + h)
    cv.rect(x, y, w, h, NAVY)
    for i in range(h):
        # gentle vertical darkening toward the top
        shade = 18 + (i * 14) // h
        cv.rect(x, y + i, w, 1, (shade, shade + 12, shade + 36))
    # stars (fixed positions, deterministic)
    for sx, sy in ((30, 44), (90, 60), (150, 52), (210, 70), (260, 48),
                   (320, 54), (370, 44), (60, 100), (330, 110), (180, 96),
                   (250, 130), (40, 140), (300, 150)):
        cv.rect(x + sx, y + sy, 3, 3, WHITE)
    # moon
    cv.disc(x + w - 70, y + 55, 30, (240, 236, 214))
    cv.disc(x + w - 80, y + 48, 7, (210, 206, 184))
    cv.disc(x + w - 58, y + 66, 5, (210, 206, 184))
    # hills
    cv.disc(x + 40, y + h + 60, 180, (10, 18, 34))
    cv.disc(x + w - 30, y + h + 40, 200, (13, 24, 44))
    cv.rect(x, y + h - 26, w, 26, (8, 14, 28))
    # launch pad
    cv.rect(x + 150, y + h - 58, 90, 32, (60, 60, 64))
    cv.rect(x + 158, y + h - 66, 74, 8, (90, 90, 96))
    # rocket (large, centre-left of the panel)
    rx, ry = x + 150, y + 28
    cv.rect(rx + 30, ry + 40, 30, 110, WHITE)
    cv.tri(rx + 30, ry + 40, rx + 60, ry + 40, rx + 45, ry, RED)
    cv.tri(rx + 30, ry + 120, rx + 8, ry + 168, rx + 30, ry + 150, RED)
    cv.tri(rx + 60, ry + 120, rx + 82, ry + 168, rx + 60, ry + 150, RED)
    cv.disc(rx + 45, ry + 66, 11, SKY)
    cv.disc(rx + 45, ry + 66, 6, (180, 220, 245))
    cv.rect(rx + 30, ry + 96, 30, 5, RED)
    # flame and smoke
    cv.tri(rx + 33, ry + 150, rx + 57, ry + 150, rx + 45, ry + 196, GOLD)
    cv.tri(rx + 37, ry + 150, rx + 53, ry + 150, rx + 45, ry + 180, ORANGE)
    cv.disc(rx + 18, y + h - 40, 13, (170, 170, 168))
    cv.disc(rx + 72, y + h - 34, 16, (150, 150, 148))
    cv.disc(rx + 45, y + h - 28, 19, (130, 130, 128))
    # caption at the top of the scene, clear of the rocket and smoke
    draw_text(cv, x + 14, y + 8, 2, WHITE, "KIM ORDERS THE ARSENAL WIDER")
    cv.clear_clip()


def draw_lead(cv, y, h):
    cv.rect(0, y, W, h, NAVY2)
    cv.border(0, y, W, h, INK, 2)
    draw_lead_scene(cv, 12, y + 12, 400, h - 24)
    tx = 436
    draw_text(cv, tx, y + 22, 2, GOLD, LEAD_KICKER)
    yy = y + 52
    for line in LEAD_HEAD:
        draw_text(cv, tx, yy, 5, WHITE, line)
        yy += 40
    yy += 8
    for line in wrap(LEAD_SUB, 46):
        draw_text(cv, tx, yy, 2, (220, 224, 232), line)
        yy += 17
    yy += 6
    cv.hline(tx, yy, 560, GOLD, 2)
    yy += 10
    draw_text(cv, tx, yy, 2, GOLD, "KCNA, THURSDAY  -  FULL STORY, PAGE ONE")


def draw_tile(cv, x, y, w, h, headline, region, kind):
    cv.rect(x, y, w, h, WHITE)
    cv.border(x, y, w, h, (200, 194, 178), 1)
    col = REGION_COLORS[region]
    # region tag + date row
    draw_text(cv, x + 8, y + 4, 2, col, region)
    d = "26 NOV"
    draw_text(cv, x + w - 8 - text_width(d, 2), y + 4, 2, RED, d)
    cv.hline(x + 8, y + 19, w - 16, (220, 214, 198), 1)
    # pictogram (24 px) and headline, up to 2 lines at scale 2
    ix, iy, isize = x + 8, y + 22, 24
    icon_bg(cv, ix, iy, isize, NAVY)
    ICONS[kind](cv, ix, iy, isize)
    lines = wrap(headline, 12)[:2]
    ly = y + 22
    for line in lines:
        draw_text(cv, ix + isize + 6, ly, 2, INK, line)
        ly += 12


def draw_grid(cv, y, h):
    cols, rows = 5, 10
    gap = 5
    tw = (W - 18 - (cols - 1) * gap) // cols
    th = (h - (rows - 1) * gap) // rows
    draw_text(cv, 10, y - 24, 2, INK, "WORLD IN BRIEF  -  49 MORE STORIES, 26 NOVEMBER 2026")
    draw_text(cv, W - 10 - text_width("ALL DATED 26 NOV", 2), y - 24, 2, RED, "ALL DATED 26 NOV")
    for i, (headline, region, kind) in enumerate(STORIES):
        r, c = divmod(i, cols)
        x = 9 + c * (tw + gap)
        yy = y + r * (th + gap)
        draw_tile(cv, x, yy, tw, th, headline, region, kind)


def draw_footer(cv):
    y = H - 34
    cv.rect(0, y, W, 34, INK)
    draw_text_c(cv, W // 2, y + 9, 2, WHITE,
                "THE WORLD TODAY  -  THURSDAY 26 NOVEMBER 2026  -  50 STORIES FROM 10 REGIONS")
    draw_text_c(cv, W // 2, y + 24, 1, GOLD,
                "SOURCES: REUTERS, KCNA, WIRE ROUND-UPS  -  ALL STORIES FIRST REPORTED 26 NOVEMBER 2026")


def draw_page():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_lead(cv, 146, 252)
    draw_grid(cv, 434, 548)
    draw_footer(cv)
    return cv

# ------------------------------------------------------------------ main

EXPECTED_SHA256 = "a306a30102ef2ceb702492797808bae73f5534aa9239fa86cc2e65e1f6e2975b"
EXPECTED_BYTES = 33389


def main():
    # Guards: every character the page prints must exist in the font,
    # and every grid headline must fit its tile in two lines.
    texts = [LEAD_KICKER, LEAD_SUB]
    texts += [h for line in LEAD_HEAD for h in [line]]
    for headline, _, _ in STORIES:
        texts.append(headline)
        assert len(wrap(headline, 12)) <= 2, headline
    for t in texts:
        for ch in t:
            assert ch in FONT, (t, ch)

    cv = draw_page()
    data = png_bytes(cv.px, W, H)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)

    digest = hashlib.sha256(data).hexdigest()
    print("wrote %s (%d bytes, sha256 %s)" % (path, len(data), digest))
    if EXPECTED_SHA256 is not None:
        assert digest == EXPECTED_SHA256, "output hash changed!"
    if EXPECTED_BYTES is not None:
        assert len(data) == EXPECTED_BYTES, "output size changed!"
    assert len(data) <= 1024 * 1024, "over the 1 MiB gate"
    return 0


if __name__ == "__main__":
    sys.exit(main())
