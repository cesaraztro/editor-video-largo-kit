"""Hoja de revisión: recorte de la cara en el instante medio (y extremos) de cada evento. Uso: hoja6.py video.mp4 eventos.json salida.jpg"""
import json, subprocess, sys
from PIL import Image, ImageDraw
ev = json.load(open(sys.argv[2])); caras = []
for i, e in enumerate(ev):
    for j, tm in enumerate([e[0], (e[0] + e[1]) / 2, e[1]]):
        p = f"qa6/tmp/h6_{i}_{j}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tm:.3f}", "-i", sys.argv[1], "-frames:v", "1",
                        "-vf", "scale=640:360", p], check=True)
        caras.append((i, j, tm, p))
C = 3; w, h = 320, 180
im = Image.new("RGB", (C * w, len(ev) * h), "black"); d = ImageDraw.Draw(im)
for i, j, tm, p in caras:
    im.paste(Image.open(p).resize((w, h)), (j * w, i * h)); d.text((j * w + 4, i * h + 4), f"#{i} {tm:.2f}", fill="yellow")
im.save(sys.argv[3], quality=80); print("ok", len(ev))
