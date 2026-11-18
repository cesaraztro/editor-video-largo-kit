"""Podcast · subtítulos .srt y copy.md (títulos, descripción, capítulos) desde planos.json.
Uso:  $PY p6_entrega.py   -> render/subtitulos.srt, render/copy.md
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json
from pathlib import Path

W = Path(__file__).parent
OUT = W.parent / "render"
P = json.load(open(W / "planos.json"))
G = json.load(open(W / "guion.json"))
FPS = P["fps"]
PAL = json.load(open(W / "palabras.json"))
for _p in PAL: _p["w"] = kit.corregir(_p["w"])   # nombres que Whisper escribe mal (config.json → correcciones)


def a_salida(t, tipo):
    for s in P["segs"]:
        if s["tipo"] == tipo and s["a"] <= t < s["b"]: return (s["o"] + (t - s["a"]) * FPS) / FPS
    return None


def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt():
    ws = []
    for tipo in ("cold", "ep"):
        for p in PAL:
            a, b = a_salida(p["s"], tipo), a_salida(max(p["s"], p["e"] - 0.01), tipo)
            if a is None: continue
            ws.append((a, b if b is not None and b > a else a + 0.25, p["w"].strip()))
    ws.sort()
    cues, cur = [], []
    for w in ws:
        if cur:
            txt = " ".join(x[2] for x in cur)
            corta = (len(txt) + len(w[2]) > 84 or w[0] - cur[-1][1] > 0.8 or w[1] - cur[0][0] > 5.0
                     or (txt[-1] in ".?!" and len(txt) > 30))
            if corta: cues.append(cur); cur = []
        cur.append(w)
    if cur: cues.append(cur)
    out = []
    for i, c in enumerate(cues, 1):
        txt = " ".join(x[2] for x in c)
        if len(txt) > 42:                                   # dos líneas, partidas cerca de la mitad
            sp = [k for k, ch in enumerate(txt) if ch == " "]
            k = min(sp, key=lambda k: abs(k - len(txt) / 2)); txt = txt[:k] + "\n" + txt[k + 1:]
        fin = min(c[-1][1] + 0.15, cues[i][0][0] - 0.02) if i < len(cues) else c[-1][1] + 0.15
        out.append(f"{i}\n{ts(c[0][0])} --> {ts(fin)}\n{txt}\n")
    (OUT / "subtitulos.srt").write_text("\n".join(out), encoding="utf8")
    ass_broll(cues)
    return len(out)


def ass_broll(cues):
    """subtítulos quemados solo donde no hubo cámaras (va sobre el B-roll)."""
    br = [p for p in P["planos"] if p["tipo"] == "broll"]
    if not br: return
    a0, a1 = br[0]["o"] / FPS, (br[-1]["o"] + br[-1]["n"]) / FPS
    t = lambda x: f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
    ev = []
    for i, c in enumerate(cues):
        ini, fin = c[0][0], c[-1][1] + 0.15
        if i + 1 < len(cues): fin = min(fin, cues[i + 1][0][0] - 0.02)
        if fin <= a0 or ini >= a1: continue
        txt = " ".join(x[2] for x in c)
        if len(txt) > 42:
            sp = [k for k, ch in enumerate(txt) if ch == " "]
            k = min(sp, key=lambda k: abs(k - len(txt) / 2)); txt = txt[:k] + "\\N" + txt[k + 1:]
        ev.append(f"Dialogue: 0,{t(max(ini, a0))},{t(min(fin, a1))},S,,0,0,0,,{{\\fad(80,80)}}{txt}")
    cab = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: S,Manrope ExtraBold,62,&H00EBF0F3,&H00EBF0F3,&H401F1E20,&H401F1E20,1,0,0,0,100,100,0,0,3,14,0,2,200,200,96,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    (OUT / "broll_subs.ass").write_text(cab + "\n".join(ev) + "\n", encoding="utf8")


def mmss(s):
    s = int(s); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def copy():
    """Borrador del copy de YouTube. Los textos salen de guion.json (titulos_alt, descripcion, links_invitado,
    etiquetas, hashtags) y de config.json → marca. Revísalo y ajústalo a mano antes de publicar."""
    M = kit.MARCA
    caps = "\n".join(f"{mmss(t)} {tit}" for t, tit in P["capitulos_yt"])
    titulos = "\n".join(f"{n}. {x}" for n, x in enumerate([G["titulo"], *G.get("titulos_alt", [])], 1))
    links = "\n".join(G.get("links_invitado", ["[PENDIENTE: links del invitado]"]))
    extra = "\n".join(x for x in (f"🚀 {M['comunidad']}: {M['comunidad_url']}" if M.get("comunidad_url") else "",
                                    f"🌐 {M['web']}" if M.get("web") else "") if x)
    etiquetas = ", ".join(G.get("etiquetas", [M["nombre"], M["empresa"], "podcast"]))
    texto = f"""# {G['titulo']} · copy para YouTube

## Opciones de título
{titulos}

## Descripción
{G.get('descripcion', '[PENDIENTE: gancho de 1–2 líneas + de qué hablan en el episodio]')}

{links}

{extra}

## Capítulos
{caps}

## Etiquetas
{etiquetas}

{" ".join(G.get("hashtags", ["#Podcast"]))}
"""
    (OUT / "copy.md").write_text(texto, encoding="utf8")


if __name__ == "__main__":
    n = srt(); copy()
    print(f"subtitulos.srt: {n} líneas · copy.md con {len(P['capitulos_yt'])} capítulos")
