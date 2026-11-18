"""Hojas del video FINAL recortadas a la cara: por evento, cuadro por cuadro desde a-0.2 hasta b+0.2 (máx 14)."""
import json, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
FPS = 30000 / 1001; T = 130; NT = 14
video, evs, pref = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
cond = sys.argv[4] if len(sys.argv) > 4 else "True"
evs = [e for e in evs if eval(cond)]
quiero = {}
for e in evs:
    f0, f1 = round((e["a"] - 0.2) * FPS), round((e["b"] + 0.2) * FPS)
    paso = max(1, (f1 - f0 + NT - 1) // NT)
    e["fr"] = list(range(f0, f1 + 1, paso))[:NT]
    for f in e["fr"]: quiero[f] = None
W, H = 960, 540
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        stdout=subprocess.PIPE)
f = 0; last = max(quiero)
while f <= last:
    b = proc.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    if f in quiero: quiero[f] = Image.frombuffer("RGB", (W, H), b).copy()
    f += 1
proc.kill()
fnt = ImageFont.load_default(); filas = []
for n, e in enumerate(evs):
    x0, y0, x1, y1 = e["box"]; cx, cy = (x0 + x1) / 2 * W, (y0 + y1) / 2 * H; s = (y1 - y0) * H * 1.6
    row = Image.new("RGB", (80 + NT * T, T), "black"); d = ImageDraw.Draw(row)
    d.text((2, 30), f"F{n} p{e['pieza']}", fill="yellow", font=fnt)
    d.text((2, 50), f"{int(e['a']//60)}:{e['a']%60:05.2f}", fill="white", font=fnt); d.text((2, 70), f"+{e['pico']:.0f}", fill="white", font=fnt)
    for k, fr in enumerate(e["fr"]):
        im = quiero.get(fr)
        if im is None: continue
        im = im.crop((int(cx - s / 2), int(cy - s / 2), int(cx + s / 2), int(cy + s / 2))).resize((T, T))
        row.paste(im, (80 + k * T, 0))
        if e["a"] <= fr / FPS <= e["b"]: ImageDraw.Draw(row).rectangle([80 + k * T, 0, 80 + k * T + T - 1, 3], fill="red")
    filas.append(row)
for h in range(0, len(filas), 9):
    sh = Image.new("RGB", (filas[0].width, T * 9), "black")
    for r, row in enumerate(filas[h:h + 9]): sh.paste(row, (0, r * T))
    sh.save(f"qa7/{pref}_{h // 9:02d}.jpg", quality=82)
print(len(filas), "filas")
