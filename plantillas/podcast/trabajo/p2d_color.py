"""Podcast · color de la CARA y del cuadro en cada cuadro clave (cada 0.5 s) de cada archivo de cámara.
La luz de la ventana cambia (sol directo → atardecer): p5_render iguala cada plano contra la referencia de su cámara.
Salida: color.json {"MVI_xxxx.MP4": [[t, caraR, caraG, caraB | null.., cuadroR, cuadroG, cuadroB], ...]}
Uso:  $PY p2d_color.py
"""
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
W = Path(__file__).parent; CR = W.parent / "crudos"
AN, AL = 192, 108

def color(p):
    cj = json.load(open(W / "caras" / f"{p.stem}.json")); vis = cj["vision"]
    cx0 = (cj["caja"][0] + cj["caja"][2] / 2) / 1920          # cara principal de esa cámara (Vision a veces toma la del otro)
    luz = json.load(open(W / "luz.json"))[p.name]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-skip_frame", "nokey", "-i", str(p), "-an", "-vf", f"scale={AN}:{AL}",
                          "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, AL, AN, 3).astype(np.float32)
    out = []
    for k, im in enumerate(fr[: len(luz)]):
        t = luz[k][0]
        q = vis[min(int(round(t * 10)), len(vis) - 1)]
        cara = [None] * 3
        if q[1] is not None and abs(q[1] - cx0) < 0.2:
            cx, cy, w, h = q[1:5]
            x0, x1 = int((cx - 0.25 * w) * AN), int((cx + 0.25 * w) * AN)
            y0, y1 = int((cy - 0.2 * h) * AL), int((cy + 0.25 * h) * AL)
            if x1 - x0 >= 2 and y1 - y0 >= 2: cara = [round(float(v), 1) for v in im[max(y0, 0):y1, max(x0, 0):x1].reshape(-1, 3).mean(0)]
        out.append([t, *cara, *[round(float(v), 1) for v in im.reshape(-1, 3).mean(0)]])
    return p.name, out

if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex: res = dict(ex.map(color, sorted(CR.glob("cam*/MVI_*.MP4"))))
    json.dump(res, open(W / "color.json", "w"))
    for k, v in res.items():
        a = np.array([x[1:4] for x in v if x[1] is not None], float)
        print(k, len(v), "cuadros · cara RGB inicio", a[:200].mean(0).round(0), "final", a[-200:].mean(0).round(0))
