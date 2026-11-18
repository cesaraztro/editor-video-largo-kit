"""v6: celular asomando por abajo: píxeles claros, poco saturados y sin tono piel, dentro del ancho del cuerpo del presentador,
en la franja inferior. Uso: borde6.py video.mp4 matte.mp4 salida.json [franja=0.30] [ss] [t]"""
import json, subprocess, sys
import numpy as np, cv2
W, H = 640, 360
FR = float(sys.argv[4]) if len(sys.argv) > 4 else 0.30
ext = (["-ss", sys.argv[5], "-t", sys.argv[6]] if len(sys.argv) > 6 else [])
lee = lambda p, f: subprocess.Popen(["ffmpeg", "-v", "error", *ext, "-i", p, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", f, "-"], stdout=subprocess.PIPE)
pv, pm = lee(sys.argv[1], "rgb24"), lee(sys.argv[2], "gray")
y0 = int(H * (1 - FR)); out = []; k = 0
while True:
    a = pv.stdout.read(W * H * 3); m = pm.stdout.read(W * H)
    if len(a) < W * H * 3 or len(m) < W * H: break
    x = np.frombuffer(a, np.uint8).reshape(H, W, 3)[y0:].astype(np.float32) / 255
    mk = np.frombuffer(m, np.uint8).reshape(H, W)[y0:] > 128
    cols = np.nonzero(mk.sum(0) > mk.shape[0] * 0.5)[0]          # columnas donde está el cuerpo
    cuerpo = np.zeros_like(mk)
    if len(cols): cuerpo[:, cols.min() + 8:cols.max() - 8] = True
    mx, mn = x.max(2), x.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    piel = (r > g * 1.04) & (g > b * 1.02) & (sat > 0.14)
    cel = (cuerpo & (mx > 0.40) & (sat < 0.38) & ~piel).astype(np.uint8)
    cel = cv2.morphologyEx(cel, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(cel, connectivity=8)
    if n > 1:
        i = 1 + int(st[1:, cv2.CC_STAT_AREA].argmax()); xx, yy, ww, hh, ar = (int(q) for q in st[i])
        out.append([k, ar, [xx, yy + y0, xx + ww, yy + y0 + hh]])
    else: out.append([k, 0, None])
    k += 1
json.dump(out, open(sys.argv[3], "w")); print("listo", k)
