"""QA · hojas de uniones: 6 cuadros antes y 6 después de cada corte (planos.json), 10 cortes por hoja.
Uso:  $PY qa_uniones.py <video.mp4> <t_inicio_del_video_en_la_línea_de_tiempo_s> [solo_uniones]
      -> qa/uniones/hoja_NN.jpg   (cuadros de 160×90; la marca roja separa antes/después)
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np

W = Path(__file__).parent
P = json.load(open(W / "planos.json"))
FPS = P["fps"]
video, t0 = sys.argv[1], float(sys.argv[2])
solo_uniones = len(sys.argv) > 3
o0 = round(t0 * FPS)
cortes = [p["o"] for p in P["planos"][1:] if (p.get("union") or not solo_uniones)]
D = W / "qa" / "uniones"; D.mkdir(parents=True, exist_ok=True)
for f in D.glob("hoja_*.jpg"): f.unlink()
AN, AL = 160, 90
filas = []
for o in cortes:
    a = o - o0 - 6
    if a < 0: continue
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-ss", f"{a / FPS:.4f}", "-i", video, "-frames:v", "12", "-vf", f"scale={AN}:{AL}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    n = len(raw) // (AN * AL * 3)
    if n < 12: break
    fr = np.frombuffer(raw[: 12 * AN * AL * 3], np.uint8).reshape(12, AL, AN, 3).copy()
    fr[5, :, -3:] = [230, 40, 40]
    filas.append(np.concatenate(list(fr), 1))
for k in range(0, len(filas), 10):
    hoja = np.concatenate(filas[k:k + 10], 0)
    subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{hoja.shape[1]}x{hoja.shape[0]}",
                    "-i", "-", str(D / f"hoja_{k // 10:02d}.jpg")], input=hoja.tobytes())
print(f"{len(filas)} cortes en {(len(filas) + 9) // 10} hojas → {D}")
