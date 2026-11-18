"""v6: píxeles 'de celular' (claros y poco saturados, ni piel ni saco) dentro de la silueta del presentador, mitad de abajo. Uso: gris6.py base.mp4 matte.mp4 salida.json"""
import json, subprocess, sys
import numpy as np
import cv2
W, H = 480, 270
def lector(p, fmt, c):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-i", p, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", fmt, "-"], stdout=subprocess.PIPE), c
(pv, _), (pm, _) = lector(sys.argv[1], "rgb24", 3), lector(sys.argv[2], "gray", 1)
filas, k = [], 0
y0 = int(H * float(sys.argv[4]) if len(sys.argv) > 4 else H * 0.45)
while True:
    a = pv.stdout.read(W * H * 3); m = pm.stdout.read(W * H)
    if len(a) < W * H * 3 or len(m) < W * H: break
    rgb = np.frombuffer(a, np.uint8).reshape(H, W, 3)[y0:].astype(np.float32) / 255
    mk = np.frombuffer(m, np.uint8).reshape(H, W)[y0:] > 160
    mk = cv2.erode(mk.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=3) > 0
    mx, mn = rgb.max(2), rgb.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    piel = (r > g) & (g > b) & (sat > 0.18) & (sat < 0.65)
    gris = mk & (mx > 0.42) & ~piel & (sat < 0.35)
    n, lab, st, _ = cv2.connectedComponentsWithStats(gris.astype(np.uint8), connectivity=8)
    if n > 1:
        i = 1 + int(st[1:, cv2.CC_STAT_AREA].argmax()); mayor = int(st[i, cv2.CC_STAT_AREA])
        x, y, w, h = (int(v) for v in st[i, :4]); caja = [x, y + y0, x + w, y + y0 + h]
    else: mayor, caja = 0, None
    filas.append([round(k * 1001 / 30000, 3), mayor, caja]); k += 1
json.dump(filas, open(sys.argv[3], "w")); print("listo", k)
