"""Hoja por evento: 12 cuadros repartidos entre a-0.25 y b+0.25 s (base5), para revisar a ojo."""
import json, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
FPS = 30000 / 1001; T = 150; NT = 12
ev = json.load(open(sys.argv[1])); pref = sys.argv[2]
ev = [e for e in ev if eval(sys.argv[3])]
quiero = {}
for e in ev:
    f0, f1 = e["f0"] - 8, e["f1"] + 8
    e["fr"] = [round(f0 + (f1 - f0) * k / (NT - 1)) for k in range(NT)]
    for f in e["fr"]: quiero[f] = None
X0, S = 510, 900
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base5.mp4", "-vf", f"crop={S}:{S}:{X0}:0,scale={T}:{T}",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
f = 0
while True:
    b = proc.stdout.read(T * T * 3)
    if len(b) < T * T * 3: break
    if f in quiero: quiero[f] = Image.frombuffer("RGB", (T, T), b)
    f += 1
fnt = ImageFont.load_default()
filas = []
for n, e in enumerate(ev):
    row = Image.new("RGB", (70 + NT * T, T), "black"); d = ImageDraw.Draw(row)
    d.text((2, 40), f"E{n}", fill="yellow", font=fnt); d.text((2, 60), f"p{e['pieza']}", fill="white", font=fnt)
    d.text((2, 80), f"{e['a']/1.1:.1f}s", fill="white", font=fnt); d.text((2, 100), f"+{e['pico']:.0f}", fill="white", font=fnt)
    for k, fr in enumerate(e["fr"]):
        im = quiero.get(fr)
        if im:
            row.paste(im, (70 + k * T, 0))
            if e["f0"] <= fr < e["f1"]: ImageDraw.Draw(row).rectangle([70 + k * T, 0, 70 + k * T + T - 1, 4], fill="red")
    filas.append(row)
for h in range(0, len(filas), 8):
    sh = Image.new("RGB", (filas[0].width, T * 8), "black")
    for r, row in enumerate(filas[h:h + 8]): sh.paste(row, (0, r * T))
    sh.save(f"qa7/{pref}_{h // 8:02d}.jpg", quality=80)
json.dump(ev, open(f"qa7/{pref}.json", "w"))
print(len(ev), "eventos en", (len(filas) + 7) // 8, "hojas")
