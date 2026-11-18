"""Podcast · paso 4: cortes del contenido (tiempo de micrófono) y mapa al tiempo de salida.

- Episodio = guion.rango, menos guion.quitar; las pausas de más de 0.55 s se acortan a ~0.32 s, siempre en silencio real.
- Cold open = guion.cold_open, con bordes ajustados al silencio más cercano.
Salida: cortes.json  {"cold": [[a,b]...], "ep": [[a,b]...], "dur_cold", "dur_ep"}
Uso:  $PY p4_cortes.py
"""
import json, subprocess
from pathlib import Path
import numpy as np

W = Path(__file__).parent
G = json.load(open(W / "guion.json"))
SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(W / "mezcla48.wav"), "-f", "f32le", "-ac", "1", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32)
hop = SR // 100
db = 20 * np.log10(np.sqrt(np.mean(x[:len(x) // hop * hop].reshape(-1, hop) ** 2, 1)) + 1e-9)
thr = max(np.percentile(db, 15) + 10, np.percentile(db, 90) - 30)
voz = db > thr
# quitar destellos de < 0.08 s (clics, respiraciones cortas)
i = 0
while i < len(voz):
    if voz[i]:
        j = i
        while j < len(voz) and voz[j]: j += 1
        if j - i < 8: voz[i:j] = False
        i = j
    else: i += 1

def callado(t, r=0.12):
    """punto más callado en ±r s alrededor de t"""
    k0, k1 = int((t - r) * 100), int((t + r) * 100)
    return (k0 + int(np.argmin(db[k0:k1 + 1]))) / 100

def tramos(a, b):
    """parte [a,b] quitando lo que sobra de cada pausa larga"""
    out, ini, run = [], a, None
    for k in range(int(a * 100), int(b * 100)):
        if not voz[k] and run is None: run = k
        if voz[k] and run is not None:
            if k - run >= 55:
                out.append([ini, run / 100 + 0.18]); ini = k / 100 - 0.14
            run = None
    out.append([ini, b])
    i = 0                                              # un pedacito de < 1.2 s entre dos pausas acortadas = saltito: esa pausa se deja entera
    while len(out) > 1 and i < len(out):
        if out[i][1] - out[i][0] < 1.2:
            j = i + 1 if i + 1 < len(out) else i - 1
            a, b = min(out[i][0], out[j][0]), max(out[i][1], out[j][1])
            out[min(i, j)] = [a, b]; del out[max(i, j)]; i = max(min(i, j) - 1, 0); continue
        i += 1
    return out

# 1) episodio
ep = [[callado(G["rango"][0], 0.15), callado(G["rango"][1], 0.2)]]
for q0, q1, _ in G["quitar"]:
    nuevo = []
    for a, b in ep:
        if q1 <= a or q0 >= b: nuevo.append([a, b]); continue
        if q0 > a: nuevo.append([a, callado(q0, 0.06)])
        if q1 < b: nuevo.append([callado(q1, 0.06), b])
    ep = nuevo
ep = [t for a, b in ep for t in tramos(a, b)]
ep = [[round(a, 3), round(b, 3)] for a, b in ep if b - a > 0.25]
# 2) cold open
cold = [[round(callado(a, 0.1), 3), round(callado(b, 0.12), 3)] for a, b in G["cold_open"]]
d_ep = sum(b - a for a, b in ep); d_cold = sum(b - a for a, b in cold)
json.dump({"cold": cold, "ep": ep, "dur_cold": d_cold, "dur_ep": d_ep, "umbral_db": float(thr)}, open(W / "cortes.json", "w"), indent=0)
orig = G["rango"][1] - G["rango"][0]
print(f"umbral {thr:.1f} dB · {len(ep)} tramos · episodio {d_ep / 60:.2f} min (original {orig / 60:.2f}, −{(1 - d_ep / orig) * 100:.0f} %) · cold open {d_cold:.1f} s")
