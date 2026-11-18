"""v6: mirada cuadro por cuadro (todos los cuadros) con blendshapes de ojos. Uso: mirada6.py video.mp4 salida.json"""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent)); import kit   # kit.py vive en la carpeta del episodio
import json, subprocess, sys
from pathlib import Path
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode
M = kit.MOTOR
sys.path.insert(0, str(M))
from mirada import iris, MODELO
W, H, FPS = 960, 540, 30000 / 1001
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-vf", f"scale={W}:{H}",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
det = FaceLandmarker.create_from_options(FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(MODELO)), running_mode=RunningMode.VIDEO, num_faces=1,
    output_facial_transformation_matrixes=True, output_face_blendshapes=True))
CL = ["eyeLookDownLeft", "eyeLookDownRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookOutLeft", "eyeLookOutRight",
      "eyeLookInLeft", "eyeLookInRight", "eyeLookUpLeft", "eyeLookUpRight"]
filas, k = [], 0
while True:
    buf = proc.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(buf, np.uint8).reshape(H, W, 3))
    r = det.detect_for_video(img, int(k * 1000 / FPS)); t = round(k / FPS, 3); k += 1
    if not r.face_landmarks:
        filas.append([t, None]); continue
    lm = r.face_landmarks[0]; m = np.array(r.facial_transformation_matrixes[0])
    yaw = np.degrees(np.arctan2(-m[2, 0], np.hypot(m[2, 1], m[2, 2])))
    pitch = np.degrees(np.arctan2(m[2, 1], m[2, 2]))
    h1, v1 = iris(lm, 468, 33, 133, 159, 145); h2, v2 = iris(lm, 473, 362, 263, 386, 374)
    bs = {c.category_name: c.score for c in r.face_blendshapes[0]}
    xs=[p.x for p in lm]; ys=[p.y for p in lm]
    filas.append([t, [round(float(yaw), 2), round(float(pitch), 2), round(float((h1 + h2) / 2), 4),
                      round(float((v1 + v2) / 2), 4), *[round(float(bs[c]), 3) for c in CL], round(min(xs),4), round(min(ys),4), round(max(xs),4), round(max(ys),4)]])
Path(sys.argv[2]).write_text(json.dumps(filas))
print(len(filas), "cuadros")
