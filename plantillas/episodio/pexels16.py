"""Baja B-roll horizontal de Pexels para cada cobertura 'broll' de covers.json → broll/NN.mp4 (+ broll.json con créditos)."""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, urllib.request, urllib.parse
from pathlib import Path
W = Path(__file__).parent
KEY = kit.pexels_key()
C = json.load(open(W / "covers.json")); usados, info = set(), {}
for i, c in enumerate(C):
    if "broll" not in c: continue
    out = W / "broll" / f"{i:02d}.mp4"
    if out.exists(): continue
    q = urllib.parse.urlencode({"query": c["broll"], "orientation": "landscape", "size": "medium", "per_page": 15})
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.pexels.com/videos/search?{q}", headers={"Authorization": KEY, "User-Agent": "editor-video-largo"})))
    for v in r.get("videos", []):
        if v["id"] in usados or v["duration"] < (c["b"] - c["a"]) + 1: continue
        fs = sorted([f for f in v["video_files"] if f.get("width") and f["width"] >= 1920 and f["width"] <= 2560 and f["height"] < f["width"]], key=lambda f: f["width"])
        if not fs: continue
        out.write_bytes(urllib.request.urlopen(urllib.request.Request(fs[0]["link"], headers={"User-Agent": "Mozilla/5.0"})).read())
        usados.add(v["id"]); info[i] = {"q": c["broll"], "id": v["id"], "autor": v["user"]["name"], "url": v["url"]}
        print(i, c["broll"], "→", v["id"]); break
    else: print(i, c["broll"], "SIN RESULTADO")
prev = json.load(open(W / "broll.json")) if (W / "broll.json").exists() else {}
prev.update({str(k): v for k, v in info.items()}); json.dump(prev, open(W / "broll.json", "w"), ensure_ascii=False, indent=1)
