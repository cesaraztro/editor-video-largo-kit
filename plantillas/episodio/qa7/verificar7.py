"""Verifica el video FINAL: en cada cuadro donde se ve la cara del presentador (grande), ¿tiene la cabeza abajo?"""
import json, sys, numpy as np
VEL, FPS = 1.10, 30000 / 1001
P = json.load(open("plan2.json")); SEGS = P["segs"]
M = json.load(open(sys.argv[1]))
TH = float(sys.argv[2]) if len(sys.argv) > 2 else 10
# lo que queda bajo B-roll no se ve (y ahí las caras son de otra gente); el fundido de salida dura 0.08 s
CUB = [(a / VEL, (b - 0.08) / VEL) for a, b in json.load(open(sys.argv[3]))["cortes"]] if len(sys.argv) > 3 else []
def pieza(ts):
    for i, s in enumerate(SEGS):
        if s["t"] <= ts < s["t"] + s["b"] - s["a"]: return i
filas = {}
for t, q in M:
    if not q: continue
    h = q[-1] - q[-3]                       # alto de la cara (0..1)
    if h < 0.22: continue                   # caras chicas = gente del B-roll
    if any(a <= t <= b for a, b in CUB): continue
    i = pieza(t * VEL)
    if i is None: continue
    filas.setdefault(i, []).append((t, q[1], q))
ev = []
for i, fs in filas.items():
    pit = np.array([p for _, p, _ in fs]); base = np.percentile(pit, 30)
    mal = [(t, p - base, q) for t, p, q in fs if p - base > TH]
    # agrupar en tramos
    for t, d, q in mal:
        if ev and ev[-1]["pieza"] == i and t - ev[-1]["b"] < 0.1: ev[-1]["b"] = t; ev[-1]["pico"] = max(ev[-1]["pico"], d); ev[-1]["n"] += 1
        else: ev.append({"pieza": i, "a": t, "b": t, "pico": d, "n": 1, "box": q[-4:]})
ev = [e for e in ev if e["n"] >= 2]
for e in ev:
    ini = SEGS[e["pieza"]]["t"] / VEL
    print(f"p{e['pieza']:2d} final {e['a']:7.2f}-{e['b']:7.2f} ({e['n']} cuadros) pico +{e['pico']:.0f}  {'ARRANQUE' if e['a'] - ini < 1.0 else ''}")
json.dump(ev, open(sys.argv[1].replace(".json", "_eventos.json"), "w"))
print(len(ev), "tramos con la cabeza abajo visibles")
