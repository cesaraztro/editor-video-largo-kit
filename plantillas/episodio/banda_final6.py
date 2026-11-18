"""QA final v6: franja inferior del video terminado, solo cuadros donde se ve al presentador (sin corte de B-roll). Uso: banda_final6.py video plan.json fps prefijo"""
import json, subprocess, sys
from PIL import Image, ImageDraw
VEL = 1.10; FPS = float(sys.argv[3]); cortes = json.load(open(sys.argv[2]))["cortes"]
cw, chh = 640, 80
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-vf", f"fps={FPS},crop=1920:240:0:840,scale={cw}:{chh}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
items = []; k = 0
while True:
    a = p.stdout.read(cw * chh * 3)
    if len(a) < cw * chh * 3: break
    t = (k + 0.5) / FPS; k += 1; ts = t * VEL
    if not any(a0 + 0.05 <= ts < b0 - 0.05 for a0, b0 in cortes): items.append((t, Image.frombytes("RGB", (cw, chh), a)))
C, F = 2, 26
for s in range(0, len(items), C * F):
    lote = items[s:s + C * F]; h = Image.new("RGB", (C * cw, F * (chh + 13)), "black"); d = ImageDraw.Draw(h)
    for n, (t, im) in enumerate(lote):
        x, y = (n % C) * cw, (n // C) * (chh + 13); h.paste(im, (x, y + 13)); d.text((x + 3, y), f"{int(t // 60)}:{t % 60:05.2f}", fill="yellow")
    h.save(f"{sys.argv[4]}_{s // (C * F):02d}.jpg", quality=88)
print(len(items), "cuadros")
