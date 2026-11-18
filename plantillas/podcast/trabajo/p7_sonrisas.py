"""Miniatura · busca sonrisas: cada cuadro clave de un archivo → MediaPipe (sonrisa, ojos abiertos) en la caja de la cara.
Uso: $PY p7_sonrisas.py <cam> <archivo.MP4>  -> sonrisas/<archivo>.json  [[t, sonrisa, parpadeo]]"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, sys
from pathlib import Path
import numpy as np, mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
W = Path(__file__).parent; MOTOR = kit.MOTOR
cam, f = sys.argv[1], sys.argv[2]
x0, y0, lado = json.load(open(W / "caras" / (Path(f).stem + ".json")))["caja"]
L = 384
opts = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MOTOR / "modelos/face_landmarker.task")),
                             running_mode=RunningMode.IMAGE, num_faces=1, output_face_blendshapes=True)
lm = FaceLandmarker.create_from_options(opts)
p = subprocess.Popen(["ffmpeg", "-v", "info", "-skip_frame", "nokey", "-i", str(W.parent / "crudos" / cam / f), "-vf",
                      f"crop={lado}:{lado}:{x0}:{y0},scale={L}:{L},showinfo", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
import threading, re
pts = []
def leer():
    for ln in p.stderr:
        m = re.search(rb"pts_time:([\d.]+)", ln)
        if m: pts.append(float(m.group(1)))
threading.Thread(target=leer, daemon=True).start()
out = []; i = 0
while True:
    b = p.stdout.read(L * L * 3)
    if len(b) < L * L * 3: break
    r = lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(b, np.uint8).reshape(L, L, 3).copy()))
    while len(pts) <= i: __import__("time").sleep(0.01)
    if r.face_blendshapes:
        bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
        out.append([round(pts[i], 2), round((bs["mouthSmileLeft"] + bs["mouthSmileRight"]) / 2, 3),
                    round((bs["eyeBlinkLeft"] + bs["eyeBlinkRight"]) / 2, 3)])
    i += 1
json.dump(out, open(W / "sonrisas" / (Path(f).stem + ".json"), "w"))
print(f, len(out), "cuadros")
