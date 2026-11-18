"""Hojas de ojos: recorte de los ojos cada 0.5 s en los tramos a la vista (sin corte encima). Uso: ojos6.py base5.mp4 plan5.json"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, sys
from pathlib import Path
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
sys.path.insert(0, str(kit.MOTOR))
from mirada import MODELO
W, H, PASO = 1920, 1080, 0.5
cortes = json.load(open(sys.argv[2]))["cortes"]
det = FaceLandmarker.create_from_options(FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODELO)), num_faces=1))
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-vf", f"fps={1/PASO}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        stdout=subprocess.PIPE)
cw, ch = 200, 70; crops = []; k = 0
while True:
    buf = proc.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    t = k * PASO + PASO / 2; k += 1     # fps filter toma el cuadro central de cada intervalo
    if any(a <= t < b for a, b in cortes): continue
    a = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=a))
    if not r.face_landmarks:
        crops.append((t, Image.new("RGB", (cw, ch), "red"))); continue
    lm = r.face_landmarks[0]; xs = [lm[i].x * W for i in (33, 133, 362, 263, 159, 145, 386, 374, 70, 300)]
    ys = [lm[i].y * H for i in (33, 133, 362, 263, 159, 145, 386, 374, 70, 300)]
    x0, x1 = min(xs) - 20, max(xs) + 20; yc = (min(ys) + max(ys)) / 2 + 5; hh = (x1 - x0) * ch / cw
    im = Image.fromarray(a).crop((int(x0), int(yc - hh / 2), int(x1), int(yc + hh / 2))).resize((cw, ch))
    crops.append((t, im))
C, F = 8, 22; Path("qa6").mkdir(exist_ok=True)
for s in range(0, len(crops), C * F):
    lote = crops[s:s + C * F]; hoja = Image.new("RGB", (C * cw, F * (ch + 14)), "black"); d = ImageDraw.Draw(hoja)
    for n, (t, im) in enumerate(lote):
        x, y = (n % C) * cw, (n // C) * (ch + 14); hoja.paste(im, (x, y + 14)); d.text((x + 3, y + 1), f"{t:.1f}", fill="yellow")
    hoja.save(f"qa6/ojos_{s // (C * F):02d}.jpg", quality=85)
print(len(crops), "recortes")
