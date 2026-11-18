"""v7: hoja de cada unión entre piezas: últimos 6 cuadros de la pieza i | primeros 6 de la i+1, cuadro por cuadro (base5)."""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W = Path(__file__).resolve().parent.parent
P = json.load(open(W / "plan2.json")); SEGS = P["segs"]
FPS = 30000 / 1001; T = 150; N = 6
# cuadro de inicio de cada pieza en base5
ini = []; k = 0
for s in SEGS: ini.append(k); k += s["n"]
total = k
quiero = {}
for i in range(len(SEGS)):
    for j in range(N):
        quiero[ini[i] + j] = None                       # primeros N
        f = ini[i] + SEGS[i]["n"] - N + j               # últimos N
        if 0 <= f < total: quiero[f] = None
X0, Y0, S = 560, 0, 800                                  # zona de la cabeza en base5 (1920x1080)
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(W / "base5.mp4"), "-vf", f"crop={S}:{S}:{X0}:{Y0},scale={T}:{T}",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
f = 0
while True:
    b = proc.stdout.read(T * T * 3)
    if len(b) < T * T * 3: break
    if f in quiero: quiero[f] = Image.frombuffer("RGB", (T, T), b)
    f += 1
fnt = ImageFont.load_default()
filas = []
for i in range(len(SEGS) - 1):
    row = Image.new("RGB", (T * 2 * N + 8 + 60, T), "black")
    d = ImageDraw.Draw(row); d.text((2, 60), f"#{i}|{i+1}", fill="yellow", font=fnt)
    t_out = SEGS[i + 1]["t"] / 1.10
    d.text((2, 80), f"{int(t_out//60)}:{t_out%60:04.1f}", fill="white", font=fnt)
    for j in range(N):
        im = quiero.get(ini[i] + SEGS[i]["n"] - N + j)
        if im: row.paste(im, (60 + j * T, 0))
        im = quiero.get(ini[i + 1] + j)
        if im: row.paste(im, (60 + N * T + 8 + j * T, 0))
    filas.append(row)
out = W / "qa7"
for h in range(0, len(filas), 8):
    sh = Image.new("RGB", (filas[0].width, T * 8), "black")
    for r, row in enumerate(filas[h:h + 8]): sh.paste(row, (0, r * T))
    sh.save(out / f"union_{h // 8:02d}.jpg", quality=82)
print(len(filas), "uniones")
