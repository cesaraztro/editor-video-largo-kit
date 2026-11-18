"""v6: detector de objetos (COCO) en TODOS los cuadros: cuadro completo + mitad de abajo ampliada. Uso: celular6.py video.mp4 salida.json"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, sys
from pathlib import Path
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ObjectDetector, ObjectDetectorOptions, RunningMode
MOD = str(kit.MODELOS / "efficientdet_lite2.tflite")
W, H = 1920, 1080
det = ObjectDetector.create_from_options(ObjectDetectorOptions(base_options=BaseOptions(model_asset_path=MOD),
          score_threshold=0.08, max_results=10, category_allowlist=["cell phone", "remote", "book", "laptop"]))
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
filas, k = [], 0
while True:
    buf = proc.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    a = np.frombuffer(buf, np.uint8).reshape(H, W, 3); t = round(k * 1001 / 30000, 3); k += 1
    hs = []
    for (x0, y0, img) in [(0, 0, a), (0, 540, np.ascontiguousarray(a[540:, :, :]))]:
        r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=img))
        for d in r.detections:
            b = d.bounding_box; c = d.categories[0]
            hs.append([c.category_name, round(c.score, 2), b.origin_x + x0, b.origin_y + y0, b.width, b.height])
    filas.append([t, hs])
    if k % 1000 == 0: print(k, flush=True)
Path(sys.argv[2]).write_text(json.dumps(filas)); print("listo", k)
