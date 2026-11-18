"""Podcast · quién habla, por el timbre (el WAV es una sola mezcla; el tono solo no los separa).

Huella por ventana de 1.2 s (cada 0.3 s): MFCC (media + desviación) de los cuadros con voz.
Centros iniciales con tramos conocidos (episodio.json → ref_anfitrion / ref_invitado),
después k-means de 2 grupos sobre todo el episodio, y suavizado (mediana de 1.5 s + turnos de al menos 0.9 s).
Salida: hablantes.json {"h": [0 anfitrión / 1 invitado / -1 silencio, cada 0.1 s]}
Uso:  $PY p3b_hablantes.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess
from pathlib import Path
import numpy as np

W = Path(__file__).parent
SR, NF = 16000, 512
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(W / "mic16k.wav"), "-f", "s16le", "-ac", "1", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
mel = lambda f: 2595 * np.log10(1 + f / 700)
imel = lambda m: 700 * (10 ** (m / 2595) - 1)
fr = np.fft.rfftfreq(NF, 1 / SR); pts = imel(np.linspace(mel(60), mel(7600), 42))
fb = np.zeros((40, len(fr)))
for i in range(40):
    a, b, c = pts[i], pts[i + 1], pts[i + 2]
    fb[i] = np.clip(np.minimum((fr - a) / (b - a), (c - fr) / (c - b)), 0, None)
n = np.arange(40); D = np.cos(np.pi / 40 * (n[:, None] + 0.5) * np.arange(20)[None, :])

# MFCC de todo el audio, cada 10 ms
frames = np.lib.stride_tricks.sliding_window_view(x, NF)[::160]
C, E = [], []
for i in range(0, len(frames), 20000):
    S = np.abs(np.fft.rfft(frames[i:i + 20000] * np.hanning(NF), axis=1)) ** 2
    E.append(10 * np.log10(S.sum(1) + 1e-12)); C.append((np.log(S @ fb.T + 1e-10) @ D)[:, 1:20])
C, E = np.vstack(C), np.concatenate(E)
voz = E > np.percentile(E, 35)

WIN, HOP = 120, 30
cent, feats = [], []
for s in range(0, len(C) - WIN, HOP):
    m = voz[s:s + WIN]
    if m.sum() < 30: continue
    c = C[s:s + WIN][m]
    cent.append((s + WIN / 2) / 100); feats.append(np.concatenate([c.mean(0), c.std(0)]))
cent, F = np.array(cent), np.array(feats)
mu, sd = F.mean(0), F.std(0) + 1e-6
Z = (F - mu) / sd
ref = lambda a, b: Z[(cent > a) & (cent < b)].mean(0)
c0 = np.vstack([Z[(cent > a) & (cent < b)] for a, b in kit.ep("ref_anfitrion")]).mean(0)   # tramos donde SOLO habla el anfitrión
c1 = np.vstack([Z[(cent > a) & (cent < b)] for a, b in kit.ep("ref_invitado")]).mean(0)    # tramos donde SOLO habla el invitado
for _ in range(15):                                           # k-means con los centros anclados al inicio
    d0, d1 = np.linalg.norm(Z - c0, axis=1), np.linalg.norm(Z - c1, axis=1)
    lab = (d1 < d0).astype(int)
    c0, c1 = Z[lab == 0].mean(0), Z[lab == 1].mean(0)
marg = d0 - d1                                                # > 0 → invitado
# a resolución de 0.1 s
dur = int(len(x) / SR * 10)
t = np.arange(dur) / 10
s_ = np.interp(t, cent, marg)
k = 15; s_ = np.array([np.median(s_[max(0, i - k // 2): i + k // 2 + 1]) for i in range(dur)])
h = (s_ > 0).astype(int)
# turnos mínimos de 0.9 s: un turno más corto toma el valor de sus vecinos
i = 0
while i < dur:
    j = i
    while j < dur and h[j] == h[i]: j += 1
    if j - i < 9 and i > 0 and j < dur: h[i:j] = h[i - 1]
    i = j
# silencio = -1 (por la energía del micrófono)
v10 = np.array([voz[int(q * 100): int(q * 100) + 10].mean() if int(q * 100) < len(voz) else 0 for q in t])
h = np.where(v10 > 0.2, h, -1)
json.dump({"h": h.tolist(), "nota": "0 = anfitrión, 1 = invitado, -1 = silencio (cada 0.1 s)"}, open(W / "hablantes.json", "w"))
for quien, a, b in kit.ep("verificar_hablantes", []):   # [["anfitrión"|"invitado", a, b], ...] para comprobar a mano
    nombre = f"{quien} {a}-{b}"
    seg = h[int(a * 10): int(b * 10)]; seg = seg[seg >= 0]
    print(f"{nombre}: {seg.mean() * 100:.0f} % invitado")
print(f"{kit.HABLANTES[0]} {(h == 0).sum() / 600:.1f} min · {kit.HABLANTES[1]} {(h == 1).sum() / 600:.1f} min")
