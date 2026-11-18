"""Pasa covers de una línea de tiempo anterior (lista + covers viejos) a la de plan2.json, vía tiempo de micrófono."""
import json, re, sys
lista, cov_viejo = sys.argv[1], sys.argv[2]
old = []; t = 0
for l in open(lista):
    a, b = map(float, re.search(r"_([\d.]+)_([\d.]+)\.mp4", l).groups()); old.append({"a": a, "b": b, "t": t}); t += b - a
P = json.load(open("plan2.json")); C = json.load(open(cov_viejo))
def m(x, segs):
    for s in segs:
        if s["t"] - 1e-6 <= x < s["t"] + s["b"] - s["a"] + 1e-6: return s["a"] + x - s["t"]
def o(mt):
    for s in P["segs"]:
        if s["a"] - 0.06 <= mt <= s["b"] + 0.06: return s["t"] + min(max(mt - s["a"], 0), s["b"] - s["a"])
    nx = [s for s in P["segs"] if s["a"] > mt]; return nx[0]["t"] if nx else P["dur"]
for k, c in enumerate(C):
    c["_k"] = k
    ma, mb = m(c["a"] + 0.01, old) - 0.01, m(min(c["b"], t) - 0.01, old) + 0.01
    c["a"], c["b"] = round(o(ma), 2), round(o(mb), 2)
C = [c for c in C if c["b"] - c["a"] > 0.8]
C[-1]["b"] = round(P["dur"], 2)
for x, y in zip(C, C[1:]):
    if y["a"] < x["b"]: y["a"] = x["b"]
    if 0 < y["a"] - x["b"] < 0.15: y["a"] = x["b"]
falt = []
for a, b in P["miradas"]:
    x = a
    while x <= b:
        if not any(c["a"] - 0.02 <= x <= c["b"] + 0.02 for c in C): falt.append(round(x, 1))
        x += 0.1
print("instantes de mirada sin cubrir:", falt)
json.dump(C, open("covers_remap.json", "w"), ensure_ascii=False, indent=1)
