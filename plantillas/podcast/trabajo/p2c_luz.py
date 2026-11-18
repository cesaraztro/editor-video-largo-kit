"""Podcast · luz de cada archivo de cámara (cae al atardecer): brillo medio (Y, 0–255) en cuadros clave.
Salida: luz.json {"MVI_xxxx.MP4": [[t, Y], ...]}.  Uso:  $PY p2c_luz.py
"""
import json, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
W = Path(__file__).parent; CR = W.parent / "crudos"

def luz(p):
    e = subprocess.run(["ffmpeg", "-skip_frame", "nokey", "-i", str(p), "-an", "-vf", "scale=96:54,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
                        "-fps_mode", "passthrough", "-f", "null", "-"], capture_output=True, text=True).stderr
    t = [float(x) for x in re.findall(r"pts_time:([\d.]+)", e)]; y = [float(x) for x in re.findall(r"YAVG=([\d.]+)", e)]
    return p.name, [[round(a, 2), round(b, 1)] for a, b in zip(t, y)]

if __name__ == "__main__":
    fs = sorted(CR.glob("cam*/MVI_*.MP4"))
    with ThreadPoolExecutor(6) as ex: out = dict(ex.map(luz, fs))
    json.dump(out, open(W / "luz.json", "w"))
    for k, v in out.items(): print(k, len(v), "muestras · Y", v[0][1] if v else None, "→", v[-1][1] if v else None)
