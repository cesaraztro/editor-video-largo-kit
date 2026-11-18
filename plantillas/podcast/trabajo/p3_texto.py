"""Podcast · paso 3: transcripción compacta con hablante por canal.

Entrada: mic16k.json (mlx_whisper con palabras) + energia.npz.
Salida: transcripcion.md  ->  "[mm:ss.s] A: texto"  (A = canal izquierdo, B = derecho)
        palabras.json     ->  [{w, s, e, h}]  (h = 0/1 hablante)
Uso:  $PY p3_texto.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json
from pathlib import Path
import numpy as np

W = Path(__file__).parent
# El WAV es una mezcla (los dos canales son iguales): el hablante sale de hablantes.json (cámaras: boca + nivel),
# que da un valor por cada 0.1 s (0 = A, 1 = B, -1 = desconocido). Sin ese archivo, todo queda como "?".
HAB = json.load(open(W / "hablantes.json"))["h"] if (W / "hablantes.json").exists() else None


def hablante(s, e):
    if HAB is None: return -1
    v = [HAB[i] for i in range(int(s * 10), max(int(e * 10), int(s * 10) + 1)) if i < len(HAB) and HAB[i] >= 0]
    return max(set(v), key=v.count) if v else -1


if __name__ == "__main__":
    js = json.load(open(W / "mic16k.json"))
    pal = []
    for sg in js["segments"]:
        for w in sg.get("words", []):
            pal.append({"w": w["word"].strip(), "s": round(w["start"], 2), "e": round(w["end"], 2), "h": hablante(w["start"], w["end"])})
    json.dump(pal, open(W / "palabras.json", "w"), ensure_ascii=False)
    # renglones: cambia de renglón al cambiar de hablante, tras pausa > 1 s o a las 40 palabras
    lineas, cur = [], None
    for p in pal:
        if cur and (p["h"] != cur["h"] or p["s"] - cur["e"] > 1.0 or len(cur["t"]) >= 40):
            lineas.append(cur); cur = None
        if not cur:
            cur = {"h": p["h"], "s": p["s"], "e": p["e"], "t": []}
        cur["t"].append(p["w"]); cur["e"] = p["e"]
    if cur: lineas.append(cur)
    f = lambda t: f"{int(t // 60):02d}:{t % 60:04.1f}"
    txt = "\n".join(f"[{f(l['s'])}–{f(l['e'])}] {[kit.HABLANTES[0], kit.HABLANTES[1], "?"][l["h"]]}: {' '.join(l['t'])}" for l in lineas)
    (W / "transcripcion.md").write_text(txt + "\n")
    tot = [sum(p["e"] - p["s"] for p in pal if p["h"] == h) / 60 for h in (0, 1, -1)]
    print(f"{len(pal)} palabras · {len(lineas)} renglones · habla A {tot[0]:.1f} · B {tot[1]:.1f} · ? {tot[2]:.1f} min")
