"""Podcast · paso 1: audio de los micrófonos (Audio 2_3.wav, estéreo float, un micrófono por canal).

- energia.npz: nivel en dB de cada canal cada 10 ms (para saber quién habla).
- mezcla48.wav: los dos micrófonos mezclados; el del que no habla baja ~12 dB (quita el eco cruzado y el ruido de sala).
- mic16k.wav: mezcla mono 16 kHz para Whisper y para sincronizar las cámaras.
Uso:  $PY p1_audio.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import subprocess, json
from pathlib import Path
import numpy as np

W = Path(__file__).parent
SRC = W.parent / "crudos" / kit.ep("audio")
SR, HOP = 48000, 480


def leer():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(SRC), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def db_env(x):
    n = len(x) // HOP * HOP
    return 20 * np.log10(np.sqrt(np.mean(x[:n].reshape(-1, HOP) ** 2, 1)) + 1e-9)


def suave(g, ataque=3, suelta=30):
    """Envolvente con ataque rápido y caída lenta (en bloques de 10 ms)."""
    out = np.empty_like(g); v = g[0]
    for i, x in enumerate(g):
        k = 1 / ataque if x > v else 1 / suelta
        v += (x - v) * k; out[i] = v
    return out


if __name__ == "__main__":
    x = leer()
    dur = len(x) / SR
    e = np.stack([db_env(x[:, 0]), db_env(x[:, 1])])
    piso = np.percentile(e, 10, axis=1); voz = np.percentile(e, 95, axis=1)
    print(f"duración {dur / 60:.2f} min · piso {piso.round(1)} dB · voz p95 {voz.round(1)} dB")
    # igualar niveles de los dos micrófonos antes de comparar
    gan = (voz.max() - voz)
    e2 = e + gan[:, None]
    # quién habla: el canal con más energía, solo si supera el piso por 12 dB
    thr = piso + gan + 12
    activo = (e2 > thr[:, None])
    dom = np.where(activo.any(0), np.argmax(e2, 0), -1)
    # ganancias por canal: 1 si es el dominante o ambos activos y parejos (< 6 dB), 0.25 si no
    parejo = np.abs(e2[0] - e2[1]) < 6
    g = np.zeros_like(e2)
    for c in (0, 1):
        g[c] = np.where((dom == c) | (activo[c] & parejo), 1.0, 0.25)
        g[c] = suave(g[c])
    np.savez_compressed(W / "energia.npz", db=e, gan=gan, piso=piso, dom=dom)
    rep = np.repeat(g, HOP, axis=1)[:, :len(x)]
    rep = np.pad(rep, ((0, 0), (0, len(x) - rep.shape[1])), constant_values=0.25)
    lin = 10 ** (gan / 20)
    mez = (x[:, 0] * rep[0] * lin[0] + x[:, 1] * rep[1] * lin[1])
    mez = mez / (np.max(np.abs(mez)) + 1e-9) * 0.7
    tmp = W / "mezcla48.f32"
    mez.astype(np.float32).tofile(tmp)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(tmp),
                    "-af", "highpass=f=70", "-c:a", "pcm_s24le", str(W / "mezcla48.wav")], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(W / "mezcla48.wav"), "-ar", "16000", "-c:a", "pcm_s16le",
                    str(W / "mic16k.wav")], check=True)
    tmp.unlink()
    hab = {"dur": dur, "ganancia_db": gan.round(2).tolist(),
           "tiempo_por_canal_min": [round(float((dom == c).sum()) / 100 / 60, 2) for c in (0, 1)]}
    json.dump(hab, open(W / "audio.json", "w"), indent=1)
    print("listo", hab)
