"""v6: celular = mancha clara y poco saturada que aparece donde normalmente está el saco (oscuro) en la parte baja.
Compara cada cuadro contra el percentil 20 de su propia pieza. Uso: celgris6.py base.mp4 salida.json"""
import json, subprocess, sys
import numpy as np, cv2
W, H = 320, 180; Y0 = int(H * 0.55); h = H - Y0
segs = json.load(open("plan2.json"))["segs"]
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
fr = []
while True:
    a = p.stdout.read(W * H * 3)
    if len(a) < W * H * 3: break
    fr.append(np.frombuffer(a, np.uint8).reshape(H, W, 3)[Y0:].copy())
fr = np.stack(fr); N = len(fr); print("cuadros", N, flush=True)
out = []; k0 = 0
for s in segs:
    k1 = min(k0 + s["n"], N); blk = fr[k0:k1].astype(np.float32) / 255
    v = blk.max(3); base = np.percentile(v, 20, axis=0)          # brillo "normal" de cada píxel en la pieza
    oscuro = base < 0.28
    for j in range(k1 - k0):
        x = blk[j]; mx, mn = x.max(2), x.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
        r, g, b = x[..., 0], x[..., 1], x[..., 2]
        piel = (r > g * 1.05) & (g > b) & (sat > 0.15)
        m = (oscuro & (mx > 0.38) & (mx - base > 0.18) & ~piel & (sat < 0.4)).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n > 1:
            i = 1 + int(st[1:, cv2.CC_STAT_AREA].argmax()); a = int(st[i, cv2.CC_STAT_AREA]); xx, yy, ww, hh = (int(q) for q in st[i, :4])
            out.append([round((k0 + j) * 1001 / 30000, 3), a, [xx, yy + Y0, xx + ww, yy + Y0 + hh]])
        else: out.append([round((k0 + j) * 1001 / 30000, 3), 0, None])
    k0 = k1
json.dump(out, open(sys.argv[2], "w")); print("listo", len(out))
