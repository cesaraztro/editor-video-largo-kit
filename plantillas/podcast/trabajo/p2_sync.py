"""Podcast · paso 2: sincroniza CADA archivo de cada cámara con los micrófonos.

Los archivos de una cámara pueden no ser continuos (la cámara se detuvo entre clips), así que cada uno se ubica solo:
correlación de envolventes contra el micrófono (global) + afinado a nivel de muestra en varios puntos del archivo,
y recta  t_mic = a + b·t_archivo  (b ≠ 1 = deriva del reloj de la cámara).
Salida: sync.json  {"cam1": [{"f", "a", "b", "dur", "mic0", "mic1", "corr"}...], "cam2": [...]}
Uso:  $PY p2_sync.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess
from pathlib import Path
import numpy as np

W = Path(__file__).parent
CR = W.parent / "crudos"
CAMS = kit.ep("camaras")
SR = 16000


def duracion(p):
    import re
    e = subprocess.run(["ffmpeg", "-i", str(p)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def wav16(p, t=None):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(p), *(["-t", f"{t:.2f}"] if t else []), "-vn", "-ac", "1",
                          "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=t is None).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def env(x, hop=160):
    n = len(x) // hop * hop
    e = np.log(np.sqrt(np.mean(x[:n].reshape(-1, hop) ** 2, 1)) + 1e-4)
    return (e - e.mean()) / (e.std() + 1e-9)


def xcorr_full(a, b):
    """k que maximiza Σ a[t]·b[t+k] (k puede ser negativo)."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.fft.rfft(b, n) * np.conj(np.fft.rfft(a, n)), n)
    k = int(np.argmax(c))
    return k if k < n // 2 else k - n


def afinar(q, m):
    """posición k en m donde mejor encaja q (m más largo) y su correlación normalizada."""
    L = len(q); n = 1 << int(np.ceil(np.log2(len(m) + L)))
    c = np.fft.irfft(np.fft.rfft(m, n) * np.conj(np.fft.rfft(q, n)), n)[: len(m) - L + 1]
    k = int(np.argmax(c))
    return k, float(c[k] / (np.linalg.norm(q) * np.linalg.norm(m[k:k + L]) + 1e-9))


if __name__ == "__main__":
    mic = wav16(W / "mic16k.wav"); emic = env(mic)
    out = json.load(open(W / "sync.json")) if (W / "sync.json").exists() else {}
    for cam, files in CAMS.items():
        res = []
        for f in files:
            p = CR / cam / f
            dur = duracion(p)
            est = Path(str(p) + ".bloques")            # archivo a medio bajar: solo el tramo inicial continuo
            parcial = est.exists()
            util = None
            if parcial:
                hechos, k = set(json.load(open(est))), 0
                while k in hechos: k += 1
                util = k * 32 * 1024 * 1024 / p.stat().st_size * dur - 2
                if util < 30: print(f"{cam}/{f}: todavía sin datos suficientes"); continue
            x = wav16(p, util)
            if not parcial: dur = len(x) / SR
            k0 = xcorr_full(env(x), emic) / 100.0             # t_mic ≈ t_archivo + k0
            pts = []
            for fr in np.linspace(0.05, 0.95, 7):
                tc = len(x) / SR * fr; L = 12 * SR
                q = x[int(tc * SR): int(tc * SR) + L]
                s0 = int((tc + k0 - 1.0) * SR)
                if s0 < 0 or len(q) < L or s0 + L + 2 * SR > len(mic): continue
                k, v = afinar(q, mic[s0: s0 + L + 2 * SR])
                if v > 0.1 and abs((s0 + k) / SR - tc - k0) < 0.15: pts.append((tc, (s0 + k) / SR, v))
            if len(pts) >= 2:
                tc, tm, v = map(np.array, zip(*pts))
                b, a = np.polyfit(tc, tm, 1)
                resid = float(np.abs(tm - (a + b * tc)).max() * 1000)
            else:
                a, b, v, resid = k0, 1.0, np.array([0.0]), -1
            r = {"f": f, "a": float(a), "b": float(b), "dur": dur, "util": len(x) / SR if parcial else dur, "mic0": float(a), "mic1": float(a + b * (len(x) / SR)),
                 "corr": float(v.mean()), "puntos": len(pts), "residuo_ms": resid}
            res.append(r)
            print(f"{cam}/{f}: dur {dur / 60:.2f} min · cubre mic {r['mic0']:.2f}→{r['mic1']:.2f} s · deriva {(b - 1) * 3.6e6:.0f} ms/h · "
                  f"residuo {resid:.1f} ms · corr {r['corr']:.2f} ({len(pts)} puntos)")
        out[cam] = res
    json.dump(out, open(W / "sync.json", "w"), indent=1)
