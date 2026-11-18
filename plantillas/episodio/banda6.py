"""Hojas de la franja inferior que quedará visible con el zoom extra Z (anclado arriba), solo cuadros sin corte encima.
Uso: banda6.py base5.mp4 plan5.json Z fps prefijo"""
import json, subprocess, sys
from PIL import Image, ImageDraw
Z, FPS = float(sys.argv[3]), float(sys.argv[4]); cortes = json.load(open(sys.argv[2]))["cortes"]
ybot = int(1080 / Z); ytop = ybot - 230; cw, chh = 640, int(230 * 640 / 1920 * 1.0) ; chh = 77
x0 = int((1920 - 1920 / Z) / 2); ww = int(1920 / Z)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-vf", f"fps={FPS},crop={ww}:{ybot - ytop}:{x0}:{ytop},scale={cw}:{chh}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
items = []; k = 0
while True:
    a = p.stdout.read(cw * chh * 3)
    if len(a) < cw * chh * 3: break
    t = (k + 0.5) / FPS; k += 1
    if not any(a0 - 0.05 <= t < b0 + 0.05 for a0, b0 in cortes): items.append((t, Image.frombytes("RGB", (cw, chh), a)))
C, F = 2, 26
for s in range(0, len(items), C * F):
    lote = items[s:s + C * F]; h = Image.new("RGB", (C * cw, F * (chh + 13)), "black"); d = ImageDraw.Draw(h)
    for n, (t, im) in enumerate(lote):
        x, y = (n % C) * cw, (n // C) * (chh + 13); h.paste(im, (x, y + 13)); d.text((x + 3, y), f"{t:.2f}", fill="yellow")
    h.save(f"{sys.argv[5]}_{s // (C * F):02d}.jpg", quality=88)
print(len(items), "cuadros revisables")
