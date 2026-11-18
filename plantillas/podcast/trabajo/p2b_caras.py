"""Podcast · caras de cada archivo de cámara.

1) Apple Vision (_motor/bin/caras, ~10 fps): caja de la cara en todo el archivo (detecta también en plano abierto).
2) Recorte fijo alrededor de la cara (las cámaras no se mueven) → MediaPipe FaceLandmarker → apertura de boca (jawOpen)
   para saber quién habla.
Uso:  $PY p2b_caras.py <cam> <archivo.MP4>   ->  caras/<archivo>.json
      {"fps":10, "vision":[[t,cx,cy,w,h]|[t,null..]], "caja":[x,y,lado] (px), "boca":[[t, jawOpen|null]]}
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, sys
from pathlib import Path
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

W = Path(__file__).parent
MOTOR = kit.MOTOR
FPS, LADO = 10, 384
cam, src = sys.argv[1], Path(sys.argv[2])
(W / "caras").mkdir(exist_ok=True)
vj = W / "caras" / f"{src.stem}.vision.json"
est = Path(str(src) + ".bloques")
if est.exists():                     # archivo a medio bajar: solo el tramo inicial continuo (copia sin recodificar)
    import re
    hechos, k = set(json.load(open(est))), 0
    while k in hechos: k += 1
    e = subprocess.run(["ffmpeg", "-i", str(src)], capture_output=True, text=True).stderr
    h_, m_, s_ = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e).groups()
    util = k * 32 * 1024 * 1024 / src.stat().st_size * (int(h_) * 3600 + int(m_) * 60 + float(s_)) - 3
    parcial = W / "caras" / f"{src.stem}.parcial.mp4"
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-i", str(src), "-t", f"{util:.2f}", "-c", "copy", "-an", str(parcial)])
    src = parcial; vj.unlink(missing_ok=True)
if not vj.exists():
    subprocess.run([str(MOTOR / "bin/caras"), str(src), str(vj)], check=True)
vis = json.load(open(vj))["cuadros"]
ok = np.array([x[1:5] for x in vis if x[1] is not None])
cx, cy, fw, fh = np.median(ok, 0)
lado = int(min(1080, 3.2 * fh * 1080)) // 2 * 2
x0 = int(np.clip(cx * 1920 - lado / 2, 0, 1920 - lado)) // 2 * 2
y0 = int(np.clip(cy * 1080 - lado / 2, 0, 1080 - lado)) // 2 * 2

opts = FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MOTOR / "modelos/face_landmarker.task")),
                             running_mode=RunningMode.VIDEO, num_faces=1, output_face_blendshapes=True,
                             min_face_detection_confidence=0.3, min_face_presence_confidence=0.3)
lm = FaceLandmarker.create_from_options(opts)
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={FPS},crop={lado}:{lado}:{x0}:{y0},scale={LADO}:{LADO}",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
boca, i, n = [], 0, LADO * LADO * 3
while True:
    buf = proc.stdout.read(n)
    if len(buf) < n: break
    r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(buf, np.uint8).reshape(LADO, LADO, 3)),
                            int(i * 1000 / FPS))
    j = None
    if r.face_blendshapes:
        bs = {b.category_name: b.score for b in r.face_blendshapes[0]}
        j = round(float(bs.get("jawOpen", 0)), 4)
    boca.append([round(i / FPS, 2), j]); i += 1
proc.wait()
nombre = src.stem.replace(".parcial", "")
json.dump({"fps": FPS, "parcial": est.exists(), "vision": vis, "caja": [x0, y0, lado], "cara": [float(cx), float(cy), float(fw), float(fh)], "boca": boca},
          open(W / "caras" / f"{nombre}.json", "w"))
bk = [b for _, b in boca if b is not None]
print(f"{src.name}: vision {len(ok) * 100 // len(vis)} % · cara cx {cx:.3f} cy {cy:.3f} alto {fh:.3f} · boca {len(bk) * 100 // max(len(boca), 1)} % "
      f"(media {np.mean(bk) if bk else 0:.3f})")
