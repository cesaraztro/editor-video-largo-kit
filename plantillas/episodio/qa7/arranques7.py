"""Arranques de pieza con la cabeza abajo: desde el corte hasta que vuelve a cámara (pitch ≤ base+6 por 3 cuadros)."""
import json, numpy as np
P = json.load(open("plan2.json")); SEGS = P["segs"]; FPS = 30000 / 1001
M = json.load(open("mirada6_base5.json")); cortes = json.load(open("plan5.json"))["cortes"]
ini = []; k = 0
for s in SEGS: ini.append(k); k += s["n"]
out = []
for i, s in enumerate(SEGS):
    f0, n = ini[i], s["n"]
    pit = np.array([M[f][1][1] if M[f][1] else np.nan for f in range(f0, f0 + n)])
    base = np.nanpercentile(pit, 30); d = pit - base
    prim = next((x for x in d[:4] if not np.isnan(x)), 0)
    if prim < 10: continue
    j = 0
    while j < n - 3 and not all((not np.isnan(x)) and x <= 6 for x in d[j:j + 3]): j += 1
    a, b = f0 / FPS, (f0 + j) / FPS
    cub = [(ca, cb) for ca, cb in cortes if ca < b and cb > a]
    falta_ini = a < min([ca for ca, cb in cub], default=9e9) - 0.01
    falta_fin = b > max([cb for ca, cb in cub], default=-1) - 0.08     # el fade de salida dura 0.08
    out.append({"pieza": i, "a": round(a, 3), "b": round(b, 3), "dur": round(b - a, 2), "prim": round(float(prim), 1),
                "cortes": cub, "ok": bool(cub and not falta_ini and not falta_fin)})
    print(f"p{i:2d} {a:7.2f}->{b:7.2f} ({b-a:.2f}s) primer +{prim:4.1f}  salida {a/1.1:6.1f}s  cortes {[(round(x,2),round(y,2)) for x,y in cub]}  {'OK' if out[-1]['ok'] else 'VISIBLE'}")
json.dump(out, open("qa7/arranques7.json", "w"), indent=0)
