"""v7: cuadros con la cabeza hacia abajo (pitch relativo a la pieza) en toda la base5 → eventos7.json (tiempo de salida lento)."""
import json, numpy as np
P = json.load(open("plan2.json")); SEGS = P["segs"]; FPS = 30000 / 1001
M = json.load(open("mirada6_base5.json")); plan = json.load(open("plan5.json"))
cortes = plan["cortes"]
ini = []; k = 0
for s in SEGS: ini.append(k); k += s["n"]
TH = float(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 9
ev = []
for i, s in enumerate(SEGS):
    f0, n = ini[i], s["n"]
    pit = np.array([M[f][1][1] if M[f][1] else np.nan for f in range(f0, f0 + n)])
    dn = np.array([(M[f][1][4] + M[f][1][5]) / 2 if M[f][1] else np.nan for f in range(f0, f0 + n)])
    base = np.nanpercentile(pit, 30)
    mal = (pit - base > TH)
    # cuadros sin cara pegados a cuadros malos también cuentan
    for j in range(n):
        if np.isnan(pit[j]) and ((j + 1 < n and mal[j + 1]) or (j > 0 and mal[j - 1])): mal[j] = True
    j = 0
    while j < n:
        if mal[j]:
            j0 = j
            while j < n and mal[j]: j += 1
            if j - j0 >= 2:
                a, b = (f0 + j0) / FPS, (f0 + j) / FPS
                cub = sum(max(0, min(b, cb) - max(a, ca)) for ca, cb in cortes) / (b - a)
                ev.append({"pieza": i, "f0": f0 + j0, "f1": f0 + j, "a": round(a, 3), "b": round(b, 3),
                           "pico": round(float(np.nanmax(pit[j0:j] - base)), 1), "cubierto": round(cub, 2),
                           "inicio": bool(j0 == 0 or (j0 <= 1 and np.isnan(pit[0])))})
        else: j += 1
json.dump(ev, open("qa7/eventos7.json", "w"), indent=0)
print(len(ev), "eventos;", sum(e["cubierto"] < 0.95 for e in ev), "sin cubrir del todo")
for e in ev:
    print(f"p{e['pieza']:2d} {e['a']:7.2f}-{e['b']:7.2f} ({e['b']-e['a']:.2f}s) pico +{e['pico']:4.1f} cub {e['cubierto']:.2f} {'INICIO' if e['inicio'] else ''}  salida {e['a']/1.1:6.1f}s")
