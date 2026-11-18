"""v5: base con movimiento de cámara (acercamiento lento, alejamiento lento o golpe de zoom en la palabra clave).

Mismos cortes de plan2.json y cuadros exactos por pieza (el audio no se desfasa).
Salida: base5.mp4 + camara5.json (tipo de movimiento por pieza).
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from armar import W, CAM
from render2 import SEGS, OFF, FPS
CEL = json.load(open(W / "celular_visible5.json"))   # v5: piezas con el celular detectado → plano más cerrado

ENC = ["-c:v", "h264_videotoolbox", "-b:v", "18M", "-pix_fmt", "yuv420p"]
CLAVE = tuple(kit.ep("palabras_clave"))   # palabras que disparan el golpe de zoom
PAL = [w for sg in json.load(open(W / "mic16k.json"))["segments"] for w in sg.get("words", [])]
caras = [q for q in json.load(open(W / "caras.json"))["cuadros"] if q and q[1] is not None]


def pieza(i):
    s = SEGS[i]; n = s["n"]; d = n / (30000 / 1001)
    t0, t1 = s["a"] - OFF, s["b"] - OFF
    qs = [q for q in caras if t0 <= q[0] <= t1] or [min(caras, key=lambda q: abs(q[0] - t0))]
    fx, fy = float(np.median([q[1] for q in qs])), float(np.median([q[2] for q in qs]))
    fh = float(np.median([q[4] for q in qs]))
    z = max(1.18 if i % 2 == 0 else 1.36, 1080 / (2.6 * fh * 1080 / 0.64))
    for c0, c1, k in CEL:
        if c0 <= s["a"] < c1: z = max(z, 1080 / (k * fh * 1080 / 0.64))
    cw, ch = int(1920 / z) // 2 * 2, int(1080 / z) // 2 * 2
    cx = min(max(int(fx * 1920 - cw / 2), 0), 1920 - cw)
    cy = min(max(int(fy * 1080 - 0.36 * ch), 0), 1080 - ch)
    px = min(max((fx * 1920 - cx) / cw, 0), 1); py = min(max((fy * 1080 - cy) / ch, 0), 1)
    # movimiento: golpe de zoom en la palabra clave; si no hay, acercamiento / alejamiento lento alternados
    clave = next((w for w in PAL if s["a"] + 0.6 <= w["start"] <= s["b"] - 0.7
                  and w["word"].strip(" .,¿?¡!").lower() in CLAVE), None)
    if clave and i % 3 != 2:
        tp = clave["start"] - s["a"] - 0.04; tipo = f"golpe@{tp:.2f}"
        Z = f"if(gte(t,{tp:.3f}),1.13,1.0)"
    elif i % 2 == 0:
        tipo = "acerca"; Z = f"(1+0.07*t/{d:.3f})"
    else:
        tipo = "aleja"; Z = f"(1.07-0.07*t/{d:.3f})"
    f = W / "piezas5" / f"m{i:03d}_{s['a']:.3f}_n{n}_z{z:.3f}_{tipo}.mp4"
    if not f.exists():
        vf = (f"crop={cw}:{ch}:{cx}:{cy},scale=w='trunc(1920*{Z}/2)*2':h='trunc(1080*{Z}/2)*2':eval=frame:flags=lanczos,"
              f"crop=1920:1080:x='(iw-1920)*{px:.3f}':y='(ih-1080)*{py:.3f}',unsharp=5:5:0.5,fps={FPS},format=yuv420p")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", str(CAM), "-frames:v", str(n), "-an",
                        "-vf", vf, *ENC, str(f)], check=True)
    return f, tipo


if __name__ == "__main__":
    (W / "piezas5").mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(pieza, range(len(SEGS))))
    (W / "lista5.txt").write_text("".join(f"file '{f}'\n" for f, _ in res))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(W / "lista5.txt"), "-c", "copy",
                    str(W / "base5.mp4")], check=True)
    json.dump([t for _, t in res], open(W / "camara5.json", "w"))
    print("base5 listo ·", sum(t.startswith("golpe") for _, t in res), "golpes de zoom")
