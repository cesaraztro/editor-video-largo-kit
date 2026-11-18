"""Podcast · quién habla = timbre (hablantes_timbre.json) corregido con la boca de cada cámara (caras/*.json + sync.json).

Cada 0.1 s con voz: la actividad de la boca (desviación de jawOpen en 1 s) del invitado (cam1) contra la del anfitrión (cam2).
Si en una ventana de 1.5 s la boca vota claro (≥ 60 % de muestras con diferencia > 0.008), manda la boca; si no, el timbre.
Después: turnos mínimos de 0.9 s. Escribe hablantes.json y vuelve a etiquetar palabras.json.
Uso:  $PY p3c_fusion.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, shutil
from pathlib import Path
import numpy as np

W = Path(__file__).parent
if not (W / "hablantes_timbre.json").exists(): shutil.copy(W / "hablantes.json", W / "hablantes_timbre.json")
h = np.array(json.load(open(W / "hablantes_timbre.json"))["h"])
S = json.load(open(W / "sync.json"))
N = len(h); ts = np.arange(N) / 10


def actividad(cam):
    out = np.full(N, np.nan)
    for r in S[cam]:
        p = W / "caras" / (Path(r["f"]).stem + ".json")
        if not p.exists() or r["puntos"] < 2: continue
        b = json.load(open(p))["boca"]
        j = np.array([x[1] if x[1] is not None else np.nan for x in b], float)
        a = np.array([np.nanstd(j[max(0, i - 5): i + 5]) if np.isfinite(j[max(0, i - 5): i + 5]).sum() >= 4 else np.nan
                      for i in range(len(j))])
        tm = r["a"] + r["b"] * np.array([x[0] for x in b])
        i0, i1 = int(np.ceil(tm[0] * 10)), int(tm[-1] * 10)
        i0, i1 = max(i0, 0), min(i1, N)
        ok = np.isfinite(a)
        out[i0:i1] = np.interp(ts[i0:i1], tm[ok], a[ok], left=np.nan, right=np.nan)
    return out


d = actividad("cam1") - actividad("cam2")              # > 0 → el invitado mueve más la boca
voto = np.where(np.isfinite(d) & (np.abs(d) > 0.008), (d > 0).astype(float), np.nan)
nuevo = h.copy(); cambios = 0
for i in range(N):
    if h[i] < 0: continue
    v = voto[max(0, i - 7): i + 8]; v = v[np.isfinite(v)]
    if len(v) >= 9:
        m = int(v.mean() > 0.5)
        if m != h[i]: cambios += 1
        nuevo[i] = m
i = 0                                                  # turnos mínimos de 0.9 s
while i < N:
    j = i
    while j < N and nuevo[j] == nuevo[i]: j += 1
    if nuevo[i] >= 0 and j - i < 9 and i > 0 and j < N and nuevo[i - 1] >= 0 and nuevo[i - 1] == nuevo[j]: nuevo[i:j] = nuevo[i - 1]
    i = j
json.dump({"h": nuevo.tolist(), "nota": "0 = anfitrión, 1 = invitado, -1 = silencio (cada 0.1 s) · timbre + boca"}, open(W / "hablantes.json", "w"))
pal = json.load(open(W / "palabras.json"))
for p in pal:
    seg = nuevo[int(p["s"] * 10): max(int(p["e"] * 10), int(p["s"] * 10) + 1)]; seg = seg[seg >= 0]
    p["h"] = int(np.bincount(seg).argmax()) if len(seg) else -1
json.dump(pal, open(W / "palabras.json", "w"), ensure_ascii=False)
cub = np.isfinite(d).sum() / max((h >= 0).sum(), 1) * 100
print(f"boca disponible en {cub:.0f} % del audio con voz · {cambios / 10:.0f} s corregidos · "
      f"{kit.HABLANTES[0]} {(nuevo == 0).sum() / 600:.1f} min · {kit.HABLANTES[1]} {(nuevo == 1).sum() / 600:.1f} min")
