"""v2: cortes por silencio real (sin solapes ni piezas diminutas) + detección de miradas al celular → ventanas a cubrir."""
import json, numpy as np
from armar import leer, MIC, W
off = json.load(open(W / "sync.json"))["mic_menos_cam"]
x, sr = leer(MIC); hop = sr // 100
db = 20 * np.log10(np.sqrt(np.mean(x[:len(x) // hop * hop].reshape(-1, hop) ** 2, 1)) + 1e-9)
thr = max(np.percentile(db, 15) + 10, np.percentile(db, 90) - 28)
voz = db > thr
# quitar destellos < 0.12 s
i = 0
while i < len(voz):
    if voz[i]:
        j = i
        while j < len(voz) and voz[j]: j += 1
        if j - i < 12: voz[i:j] = False
        i = j
    else: i += 1
f = json.load(open(W / "mirada16.json"))
fl = np.array([1 if (q[1] and (q[1][0] > 8 or q[1][1] > -2)) else 0 for q in f])
fl = np.array([int(np.median(fl[max(0, k - 1):k + 2])) for k in range(len(fl))])
mira = lambda tm: bool(fl[min(max(int(round((tm - off) * 10)), 0), len(fl) - 1)])   # tm en tiempo de micrófono

# 1) juntar tramos del EDL contiguos (evita audio repetido en las uniones)
edl = json.load(open(W / "edl.json")); spans = []
for cap, s, e, txt in edl:
    if spans and spans[-1]["cap"] == cap and s - spans[-1]["e"] < 0.8:
        spans[-1]["e"] = e; spans[-1]["txt"] += " " + txt
    else: spans.append({"cap": cap, "s": s, "e": e, "txt": txt})
# 2) bordes en silencio real, sin colar sílabas de la palabra vecina que no se usa
_w = json.load(open(W / "mic16k.json")); PAL = [w for sg in _w["segments"] for w in sg.get("words", [])]
def minimo(t0, t1):
    k0, k1 = int(round(t0 * 100)), int(round(t1 * 100))
    return (k0 + int(np.argmin(db[k0:k1 + 1]))) / 100
def inicio(s):
    prev = [w for w in PAL if w["start"] < s - 0.1]
    pe = prev[-1]["end"] if prev else 0
    if s - pe < 0.5:                                        # palabra pegada: se corta en el punto más callado
        return minimo(s - 0.15, s + 0.08), True
    k = int(round(s * 100))
    while k > s * 100 - 40 and k / 100 > pe + 0.05 and voz[k - 1]: k -= 1
    return max(k / 100, pe + 0.05), False
def fin(e):
    nxt = [w for w in PAL if w["start"] >= e - 0.02]
    ns = nxt[0]["start"] if nxt else e + 9
    if ns - e < 0.5:
        return minimo(e - 0.12, e + 0.15), True
    k = int(round(e * 100))
    while k < e * 100 + 45 and k / 100 < ns - 0.05 and voz[k]: k += 1
    return min(k / 100, ns - 0.17), False
segs = []
for sp in spans:
    (a, ja), (b, jb) = inicio(sp["s"]), fin(sp["e"])
    # 3) dentro: quitar pausas >= 0.30 s (dejando 0.10 / 0.06), las miradas suelen caer ahí
    corte, k0, run = [], int(a * 100), None
    for k in range(int(a * 100), int(b * 100) + 1):
        q = not voz[k]
        if q and run is None: run = k
        if not q and run is not None:
            if k - run >= 30: corte.append((run, k))
            run = None
    trozos, ini = [], a
    for r0, r1 in corte:
        trozos.append([ini, r0 / 100 + 0.10]); ini = r1 / 100 - 0.06
    trozos.append([ini, b])
    # no dejar trozos < 0.7 s: se unen con el vecino (se conserva esa pausa)
    k = 0
    while k < len(trozos):
        if trozos[k][1] - trozos[k][0] < 0.7 and len(trozos) > 1:
            if k > 0: trozos[k - 1][1] = trozos[k][1]; trozos.pop(k); continue
            else: trozos[1][0] = trozos[0][0]; trozos.pop(0); continue
        k += 1
    for j, (u, v) in enumerate(trozos):
        # márgenes: 0.04 antes de la voz, 0.08 después; si mira el celular en el margen, se recorta al mínimo
        u2 = u if (j == 0 and ja) else u - 0.04
        v2 = v if (j == len(trozos) - 1 and jb) else v + 0.08
        if j == 0 and mira(u2) and not voz[int(u2 * 100)]: u2 = u - 0.02
        if j == len(trozos) - 1 and not jb and mira(v2): v2 = v + 0.05
        segs.append({"cap": sp["cap"], "a": round(u2, 3), "b": round(v2, 3), "txt": sp["txt"] if j == 0 else ""})
# colas: dejar que la última sílaba se apague (hasta 0.18 s, sin tocar la siguiente palabra);
# arranques: 0.05 s de aire si antes hay silencio
for sg in segs:
    nxt = [w["start"] for w in PAL if w["start"] >= sg["b"] - 0.02]
    tope = min(sg["b"] + 0.18, (nxt[0] - 0.03) if nxt else 9e9)
    k = int(round(sg["b"] * 100))
    while k / 100 < tope and db[k] > -50: k += 1
    sg["b"] = round(max(sg["b"], min(k / 100 + 0.02, tope)), 3)
    k = int(round(sg["a"] * 100)); k0 = k
    while k > k0 - 6 and db[k - 1] > -50: k -= 1          # no comerse el ataque de la primera sílaba
    sg["a"] = round(k / 100, 3)
    if all(db[k - 5:k] < -50):
        prev = [w["end"] for w in PAL if w["end"] <= sg["a"] + 0.02]
        sg["a"] = round(max(sg["a"] - 0.05, (prev[-1] + 0.02) if prev else 0), 3)
# recortes manuales tras revisar la transcripción (tropiezos, repeticiones, tomas descartadas)
for q0, q1, _ in json.load(open(W / "quitar.json")):
    nuevos = []
    for sg in segs:
        if q1 <= sg["a"] or q0 >= sg["b"]: nuevos.append(sg); continue
        if q0 > sg["a"] + 0.3: nuevos.append({**sg, "b": q0})
        if q1 < sg["b"] - 0.3: nuevos.append({**sg, "a": q1, "txt": ""})
    segs = nuevos
# sin solapes
for k in range(1, len(segs)):
    if segs[k]["a"] < segs[k - 1]["b"]: segs[k]["a"] = segs[k - 1]["b"]
# cada pieza dura un número exacto de cuadros: si no, el video pierde fracciones de cuadro y el audio se adelanta
FPS = 30000 / 1001
for k, sg in enumerate(segs):
    n = round((sg["b"] - sg["a"]) * FPS)
    if k + 1 < len(segs) and sg["a"] + n / FPS > segs[k + 1]["a"] + 1e-6: n -= 1
    sg["n"] = n; sg["b"] = round(sg["a"] + n / FPS, 6)
# 4) miradas que quedan dentro de lo que se ve → ventanas a cubrir (tiempo de salida)
t, ven = 0.0, []
for sg in segs:
    k = sg["a"]
    while k < sg["b"]:
        if mira(k):
            k0 = k
            while k < sg["b"] and mira(k): k += 0.1
            if k - k0 >= 0.15: ven.append([t + k0 - sg["a"], t + k - sg["a"]])
        k += 0.1
    sg["t"] = round(t, 6); t += sg["b"] - sg["a"]
print(f"umbral {thr:.1f} · {len(spans)} tramos · {len(segs)} piezas · {t/60:.2f} min · más corta {min(s['b']-s['a'] for s in segs):.2f}s · miradas {sum(b-a for a,b in ven):.1f}s en {len(ven)}")
json.dump({"segs": segs, "miradas": [[round(a, 2), round(b, 2)] for a, b in ven], "dur": t}, open(W / "plan2.json", "w"), ensure_ascii=False, indent=1)
