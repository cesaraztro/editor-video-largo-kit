"""Hoja de caras en instantes dados (base5). Uso: caras6.py base5.mp4 tiempos.json salida.jpg"""
import json, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
ts = json.load(open(sys.argv[2])); cw, ch = 300, 200; C = 6
hoja = Image.new("RGB", (C * cw, ((len(ts) + C - 1) // C) * (ch + 14)), "black"); d = ImageDraw.Draw(hoja)
for n, t in enumerate(ts):
    a = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", sys.argv[1], "-frames:v", "1", "-vf", "crop=900:600:510:60,scale=300:200",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    im = Image.frombytes("RGB", (cw, ch), a); x, y = (n % C) * cw, (n // C) * (ch + 14)
    hoja.paste(im, (x, y + 14)); d.text((x + 3, y + 1), f"#{n} {t:.2f}", fill="yellow")
hoja.save(sys.argv[3], quality=85)
