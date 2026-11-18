import json, numpy as np
P = json.load(open("plan2.json")); SEGS = P["segs"]
M = json.load(open("mirada6_base5.json"))
ini = []; k = 0
for s in SEGS: ini.append(k); k += s["n"]
def v(f):
    q = M[f][1] if f < len(M) else None
    return q
for i, s in enumerate(SEGS):
    f0 = ini[i]; n = s["n"]
    rows = [v(f) for f in range(f0, f0 + n)]
    ok = [r for r in rows if r]
    if not ok: print(i, "sin cara"); continue
    yaw = np.array([r[0] if r else np.nan for r in rows]); pit = np.array([r[1] if r else np.nan for r in rows])
    dn = np.array([(r[4] + r[5]) / 2 if r else np.nan for r in rows])
    my, mp_, md = np.nanmedian(yaw), np.nanmedian(pit), np.nanmedian(dn)
    print(f"{i:2d} n={n:3d} med yaw {my:6.1f} pit {mp_:6.1f} dn {md:.2f} | primeros 12 pit:", " ".join(f"{(p-mp_):+.0f}" if not np.isnan(p) else " x" for p in pit[:12]),
          "| dn:", " ".join(f"{d:.1f}" if not np.isnan(d) else "x" for d in dn[:12]))
