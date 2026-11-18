"""Extiende las coberturas a las ventanas de mirada nuevas; lo que no se pueda extender queda como B-roll nuevo (sin query)."""
import json
P = json.load(open("plan2.json")); V = json.load(open("ventanas3.json")); C = json.load(open("covers_remap.json"))
for c in C: c.pop("ma", None); c.pop("mb", None)
def huecos(a, b, C):
    out, t = [], a
    for c in sorted(C, key=lambda c: c["a"]):
        if c["b"] <= t or c["a"] >= b: continue
        if c["a"] > t: out.append([t, c["a"]])
        t = max(t, c["b"])
    if t < b: out.append([t, b])
    return [h for h in out if h[1] - h[0] > 0.05]
nuevos = []
for a, b in V:
    for h0, h1 in huecos(a, b, C):
        izq = [c for c in C if abs(c["b"] - h0) < 0.7]; der = [c for c in C if abs(c["a"] - h1) < 0.7]
        lim = lambda c: 9.0 if "card" in c else 7.5
        if izq and (h1 - izq[0]["a"]) <= lim(izq[0]): izq[0]["b"] = round(h1, 2); continue
        if der and (der[0]["b"] - h0) <= lim(der[0]): der[0]["a"] = round(h0, 2); continue
        if h1 - h0 < 2.2:
            c0 = (h0 + h1) / 2; h0, h1 = c0 - 1.1, c0 + 1.1
        n = {"a": round(h0, 2), "b": round(h1, 2), "broll": None}; C.append(n); nuevos.append(n)
C.sort(key=lambda c: c["a"])
# sin solapes: recorta el siguiente
for x, y in zip(C, C[1:]):
    if y["a"] < x["b"]: y["a"] = x["b"]
C = [c for c in C if c["b"] - c["a"] > 0.5]
C[-1]["b"] = round(P["dur"], 2)
json.dump(C, open("covers3.json", "w"), ensure_ascii=False, indent=1)
print(len(C), "coberturas", round(sum(c["b"] - c["a"] for c in C), 1), "s")
for c in C:
    if c.get("broll", 1) is None: print("NUEVO", c["a"], c["b"])
