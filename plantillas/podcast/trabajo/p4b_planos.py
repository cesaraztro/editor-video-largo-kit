"""Podcast · plan de planos multicámara (cámaras, tamaños, movimiento) y de gráficos, en cuadros de salida.

Reglas de edición:
- Cámara = quien habla (cam1 invitado, cam2 anfitrión). Interjecciones cortas (< 1.4 s) no cambian de cámara.
- El corte por cambio de turno cae 0.12 s antes de la primera palabra del nuevo turno.
- Cada unión (donde se quitó algo) es un corte obligatorio y SIEMPRE cambia cámara o tamaño: así no se nota el salto.
- Tres tamaños por cámara: A abierto 1.0 (dos personas), M medio 1.12, C cerrado 1.42 (la diferencia debe notarse para que la unión no parezca salto).
- Planos largos (> 11 s) se parten en la pausa más cercana a la mitad: un cambio de tamaño o un plano de reacción.
- Acercamiento lento (+4 %) o alejamiento en planos de 5 s o más.
- Capítulo → plano abierto; rótulo y frase → cámara de quien habla en M (deja lugar para el texto).
Salida: planos.json
Uso:  $PY p4b_planos.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json
from pathlib import Path
import numpy as np

W = Path(__file__).parent
FPS = 30000 / 1001
CORTES = json.load(open(W / "cortes.json"))
G = json.load(open(W / "guion.json"))
PAL = [p for p in json.load(open(W / "palabras.json")) if p["h"] in (0, 1)]
SYNC = json.load(open(W / "sync.json")) if (W / "sync.json").exists() else None
CARAS = W / "caras"
_CV = {}


def movida(f, t0, d):
    """True si en ese tramo del archivo la cara no está (cámara apuntando a otro lado) o la cámara se mueve."""
    if not (CARAS / f"{Path(f).stem}.json").exists(): return False
    if f not in _CV:
        cj = json.load(open(CARAS / f"{Path(f).stem}.json"))
        x, _, l = cj["caja"]; _CV[f] = (cj["vision"], (x + l / 2) / 1920)
    vis, cx0 = _CV[f]
    qs = [q for q in vis if t0 <= q[0] <= t0 + d]
    alguna = [q for q in qs if q[1] is not None]                        # Vision da una sola cara: a veces la del otro
    ok = [q for q in alguna if abs(q[1] - cx0) < 0.2]                    # la cara principal de esa cámara
    if len(qs) < 3: return False
    if len(alguna) < 0.6 * len(qs): return True                          # nadie en cuadro: la cámara apunta a otro lado
    if len(ok) < 3: return len(ok) < 0.15 * len(alguna)
    cx = np.array([q[1] for q in ok])
    return float(np.percentile(cx, 90) - np.percentile(cx, 10)) > 0.12  # la cámara se movió (no solo la cabeza)
CAM_DE = {1: "cam1", 0: "cam2"}            # hablante → cámara (1 invitado, 0 anfitrión)
ZOOM = {"A": 1.0, "M": 1.12, "C": 1.42}
JUNTOS = 22      # s: como máximo cada cuánto vuelve el plano abierto donde salen los dos
INTRO_N = round(7 * FPS); BARRIDO = 22; FINAL_N = round(20 * FPS)
MIN_TURNO, MIN_PLANO, LARGO = 1.4, 1.2, 11.0


# ───────────── tramos → cuadros de salida (redondeo acumulado: el audio nunca se desfasa) ─────────────
def armar_segs(lista, tipo, o0):
    segs, acum, o = [], 0.0, o0
    for a, b in lista:
        acum += b - a
        fin = o0 + round(acum * FPS); n = fin - o
        segs.append({"tipo": tipo, "a": a, "b": a + n / FPS, "n": n, "o": o}); o = fin
    return segs, o


segs_c, fin_c = armar_segs(CORTES["cold"], "cold", 0)
o_ep = fin_c + INTRO_N - BARRIDO
segs_e, fin_e = armar_segs(CORTES["ep"], "ep", o_ep)
SEGS = segs_c + segs_e
TOTAL = fin_e + FINAL_N


def mic_a_o(t, tipo="ep"):
    """tiempo de micrófono → cuadro de salida (si cae en algo quitado, el siguiente tramo)."""
    for s in SEGS:
        if s["tipo"] != tipo: continue
        if t < s["a"]: return s["o"]
        if t < s["b"]: return s["o"] + int(round((t - s["a"]) * FPS))
    return SEGS[-1]["o"] + SEGS[-1]["n"]


def o_a_mic(o):
    for s in SEGS:
        if s["o"] <= o < s["o"] + s["n"]: return s["a"] + (o - s["o"]) / FPS, s
    return None, None


# ───────────── cobertura de cada cámara (sync.json) ─────────────
def archivo(cam, t0, t1):
    """archivo de la cámara que cubre [t0, t1] de micrófono, o None."""
    if SYNC is None: return {"f": "?", "a": 0.0, "b": 1.0}
    for r in SYNC[cam]:
        if r["puntos"] >= 2 and r["mic0"] + 0.05 <= t0 and t1 <= r["mic1"] - 0.05: return r
    return None


# ───────────── 1. cortes de turno dentro de cada tramo ─────────────
def turnos(s):
    """[(cuadro_relativo, hablante)] dentro del tramo s."""
    ws = [p for p in PAL if s["a"] - 0.05 <= p["s"] < s["b"]]
    if not ws: return []
    runs = []                                  # [hablante, inicio, fin]
    for p in ws:
        if runs and runs[-1][0] == p["h"] and p["s"] - runs[-1][2] < 1.5: runs[-1][2] = p["e"]
        else: runs.append([p["h"], p["s"], p["e"]])
    cambio = True                              # interjecciones cortas: se absorben
    while cambio and len(runs) > 1:
        cambio = False
        for i, r in enumerate(runs):
            if r[2] - r[1] < MIN_TURNO:
                if i > 0: runs[i - 1][2] = max(runs[i - 1][2], r[2])
                else: runs[1][1] = r[1]
                runs.pop(i); cambio = True; break
        k = 1                                  # juntar vecinos iguales
        while k < len(runs):
            if runs[k][0] == runs[k - 1][0]: runs[k - 1][2] = runs[k][2]; runs.pop(k)
            else: k += 1
    out = [(0, runs[0][0])]
    for h, a, _ in runs[1:]:
        f = int(round((a - 0.12 - s["a"]) * FPS))
        if f > 0: out.append((f, h))
    return out


def construir(segs):
    planos = []
    for s in segs:
        ts = turnos(s) or [(0, planos[-1]["h"] if planos else 0)]
        ts = [t for k, t in enumerate(ts) if k == 0 or t[0] <= s["n"] - MIN_PLANO * FPS]
        # una unión a < 0.6 s de un cambio de turno: el turno nuevo arranca en la unión
        if len(ts) > 1 and ts[1][0] < 0.6 * FPS: ts = [(0, ts[1][1])] + ts[2:]
        for k, (f, h) in enumerate(ts):
            f1 = ts[k + 1][0] if k + 1 < len(ts) else s["n"]
            if f1 - f <= 0: continue
            planos.append({"o": s["o"] + f, "n": f1 - f, "h": h, "union": k == 0, "tipo": "habla"})
    # planos demasiado cortos que NO empiezan en unión: se juntan con el anterior
    k = 1
    while k < len(planos):
        p = planos[k]
        if p["n"] < MIN_PLANO * FPS and not p["union"]:
            planos[k - 1]["n"] += p["n"]; planos.pop(k)
        else: k += 1
    return planos


def pausa_media(o0, n):
    """cuadro de salida del hueco entre palabras más cercano a la mitad del plano."""
    m0, s = o_a_mic(o0)
    if s is None: return None
    m1 = m0 + n / FPS
    ws = [p for p in PAL if m0 + 2.5 < p["s"] < m1 - 2.5]
    if len(ws) < 2: return None
    mid = (m0 + m1) / 2
    cands = [(abs((ws[i]["e"] + ws[i + 1]["s"]) / 2 - mid) - 2 * min(0.4, ws[i + 1]["s"] - ws[i]["e"]), ws[i + 1]["s"] - 0.06)
             for i in range(len(ws) - 1)]
    t = min(cands)[1]
    return o0 + int(round((t - m0) * FPS))


def partir(planos):
    out, n_reac = [], 0
    cola = list(planos)
    while cola:
        p = cola.pop(0)
        if p["n"] <= LARGO * FPS or p["tipo"] != "habla":
            out.append(p); continue
        c = pausa_media(p["o"], p["n"])
        if c is None or c - p["o"] < 2.5 * FPS or p["o"] + p["n"] - c < 2.5 * FPS:
            out.append(p); continue
        a = dict(p, n=c - p["o"]); b = dict(p, o=c, n=p["o"] + p["n"] - c, union=False)
        dur_reac = int(2.6 * FPS)
        m_c, _ = o_a_mic(c)
        oyente_calla = m_c is not None and not any(q["h"] != p["h"] and m_c < q["e"] and q["s"] < m_c + 2.6 for q in PAL)
        if p["n"] > 15 * FPS and b["n"] > dur_reac + 2.5 * FPS and oyente_calla and n_reac % 2 == 0:
            r = dict(p, o=c, n=dur_reac, union=False, tipo="reaccion", h=1 - p["h"])
            b = dict(b, o=c + dur_reac, n=b["n"] - dur_reac)
            out.append(a); cola[:0] = [r, b]
        else:
            out.append(a); cola[:0] = [b]
        n_reac += 1
    return out


# ───────────── gráficos (en cuadros de salida) ─────────────
def graficos():
    gs = []
    for num, (t, tit) in enumerate(G["capitulos"], 1):
        gs.append({"comp": "Capitulo", "o": mic_a_o(t), "n": round(4 * FPS), "props": {"num": num, "titulo": tit}})
    for t, quien, nom, cargo in G["rotulos"]:
        gs.append({"comp": "Rotulo", "o": mic_a_o(t), "n": round(6 * FPS), "quien": quien,
                   "props": {"nombre": nom, "cargo": cargo, "lado": "izq" if quien == "invitado" else "der"}})
    for t, d, quien, txt in G["frases"]:
        gs.append({"comp": "Frase", "o": mic_a_o(t), "n": round(d * FPS), "quien": quien,
                   "props": {"texto": txt, "lado": "der" if quien == "invitado" else "izq"}})
    for t, d, tit, sub, extra in G["ctas"]:
        gs.append({"comp": "CTA", "o": mic_a_o(t), "n": round(d * FPS), "props": {"titulo": tit, "sub": sub, "extra": extra}})
    gs.append({"comp": "Intro", "o": fin_c, "n": INTRO_N, "props": G["intro"]})
    gs.append({"comp": "Final", "o": fin_e - 12, "n": FINAL_N + 12,
               "props": {"titulo": kit.MARCA["cierre"], "web": kit.MARCA["web"], "comunidad": kit.MARCA["comunidad"],
                         "videos": kit.MARCA["pantalla_final"]}})
    return gs


def broll(planos):
    """donde ninguna cámara grabó: B-roll (una toma por entrada de guion.broll) con subtítulos encima."""
    if "sin_camara" not in G: return planos
    o0, o1 = mic_a_o(G["sin_camara"][0]), mic_a_o(G["sin_camara"][1])
    out = []
    for p in planos:
        a, b = p["o"], p["o"] + p["n"]
        if b <= o0 or a >= o1: out.append(p); continue
        if a < o0: out.append(dict(p, n=o0 - a))
        if b > o1: out.append(dict(p, o=o1, n=b - o1, union=True))
    marcas = sorted({min(max(mic_a_o(t), o0), o1): k for k, (t, _) in enumerate(G["broll"])}.items())
    for j, (o, k) in enumerate(marcas):
        fin = marcas[j + 1][0] if j + 1 < len(marcas) else o1
        if fin - o < 1.5 * FPS: continue
        out.append({"o": o, "n": fin - o, "h": -1, "union": True, "tipo": "broll", "bq": k, "q": G["broll"][k][1]})
    out.sort(key=lambda p: p["o"])
    for x, y in zip(out, out[1:]):                       # sin huecos: cada plano llega hasta el siguiente
        if y["o"] > x["o"] + x["n"] and x["o"] + x["n"] >= o0 - 1 and y["o"] <= o1: x["n"] = y["o"] - x["o"]
    return out


def forzar(planos, gs):
    """rótulo/frase: cámara de quien habla y tamaño M; capítulo: plano abierto."""
    for g in gs:
        if g["comp"] in ("Rotulo", "Frase"):
            h = 1 if g["quien"] == "invitado" else 0
            for p in planos:
                if p["tipo"] == "broll": continue
                if p["o"] < g["o"] + g["n"] and g["o"] < p["o"] + p["n"]:
                    if p["tipo"] == "reaccion": p["tipo"] = "habla"
                    p["h"] = h; p["forzar"] = "M"
        elif g["comp"] == "Capitulo":
            for p in planos:
                if p["o"] <= g["o"] < p["o"] + p["n"]: p["forzar"] = p.get("forzar") or "A"


def tamanos(planos):
    ult_A = -1e9                                       # último plano abierto (los dos en cuadro), cualquier cámara
    prev, k_mov, k_cer = None, 0, 0
    for p in planos:
        m, s = o_a_mic(p["o"])
        if p["tipo"] == "broll":
            p.update(cam=None, tam="B", z0=1.0, z1=1.05); prev = p; continue
        cam = CAM_DE[p["h"]]
        def mala(c):
            r = archivo(c, m, m + p["n"] / FPS)
            return r is None or (r["f"] != "?" and movida(r["f"], (m - r["a"]) / r["b"], p["n"] / FPS))
        if m is not None and mala(cam) and not mala(CAM_DE[1 - p["h"]]):   # sin cobertura o cámara moviéndose
            cam = CAM_DE[1 - p["h"]]; p["cambio"] = "cobertura"
        p["cam"] = cam
        if p.get("forzar"): t = p["forzar"]
        elif p["tipo"] == "reaccion": t = "M"
        elif s is not None and s["tipo"] == "cold": t = "C" if not prev or prev["tam"] != "C" or prev["cam"] != cam else "A"
        elif prev is None or prev["cam"] != cam:
            t = "A"                                                       # v2: cambia quien habla → los dos en cuadro
        elif prev["tam"] == "A":                                          # misma cámara después del abierto: se cierra en quien habla
            k_cer += 1
            t = "C"
        else:
            t = "A" if prev["tam"] == "C" else "C"                        # vuelve a los dos (de M a A sería casi un salto: M → C)
        if prev and prev["cam"] == cam and prev["tam"] == t:            # nunca el mismo encuadre dos veces seguidas
            t = {"M": "C", "C": "A", "A": "C"}[t]
        if t == "A": ult_A = p["o"]
        p["tam"] = t
        z = ZOOM[t]
        if t == "A" and p["n"] >= 4 * FPS and p["tipo"] == "habla" and not (s is not None and s["tipo"] == "cold"):
            p["z0"], p["z1"] = 1.0, round(1.0 + min(0.12, 0.012 * p["n"] / FPS), 3)   # zoom lento hacia quien habla
        elif p["n"] >= 5 * FPS and p["tipo"] == "habla":
            k_mov += 1
            p["z0"], p["z1"] = (z, z * 1.04) if k_mov % 3 else (z * 1.04, z)
        else:
            p["z0"] = p["z1"] = z
        if m is not None:
            r = archivo(cam, m, m + p["n"] / FPS)
            p["mic"] = round(m, 4)
            if r and r["f"] != "?":
                p["f"] = r["f"]; p["t_cam"] = round((m - r["a"]) / r["b"], 4)
        prev = p
    return planos


if __name__ == "__main__":
    gs = graficos()
    planos = []
    for grupo in ("cold", "ep"):
        planos += partir(construir([s for s in SEGS if s["tipo"] == grupo]))
    planos = broll(planos)
    forzar(planos, gs)
    tamanos(planos)
    ALT = {"M": "C", "C": "M", "A": "C"}               # plano < 1.5 s pegado a otro de la misma cámara: mismo encuadre que su vecino
    for i in range(1, len(planos) - 1):                # (un salto mínimo se nota menos que dos cambios de zoom en medio segundo)
        p, a, b = planos[i], planos[i - 1], planos[i + 1]
        if p["tipo"] == "broll" or p["n"] >= 1.5 * FPS or p.get("forzar"): continue
        if a.get("cam") == p["cam"]: p.update(tam=a["tam"], z0=a["z1"], z1=a["z1"])
        elif b.get("cam") == p["cam"]: p.update(tam=b["tam"], z0=b["z0"], z1=b["z0"])
        else: continue
        p["corto"] = True
        if b.get("cam") == p["cam"] and b["tam"] == p["tam"] and a.get("cam") == p["cam"]:
            t = ALT[b["tam"]]; k = ZOOM[t] / ZOOM[b["tam"]]
            b.update(tam=t, z0=round(b["z0"] * k, 4), z1=round(b["z1"] * k, 4))
    for p in planos:                                   # v2: texto lateral sobre una cámara donde la cara está pegada al borde:
        if p.get("forzar") == "M" and p.get("f"):      #     el M todavía muestra al otro y el texto lo taparía → C
            cj = json.load(open(CARAS / f"{Path(p['f']).stem}.json")); cx0 = (cj["caja"][0] + cj["caja"][2] / 2) / 1920
            if cx0 < 0.25 or cx0 > 0.75:
                ant = planos[planos.index(p) - 1]           # dos cerrados seguidos: el segundo más cerrado (si no, sería salto)
                z = 1.68 if ant.get("tam") == "C" and ant.get("cam") == p["cam"] and ant["z1"] < 1.5 else ZOOM["C"]
                p.update(tam="C", z0=z, z1=z, forzar="C")
    for a, b in zip(planos, planos[1:]):               # v2: un encuadre igual al anterior en la misma cámara (salto) → se cambia
        if b["tipo"] == "broll" or b.get("corto") or not a.get("cam") or a["cam"] != b["cam"] or a["tam"] != b["tam"]: continue
        if abs(b["z0"] / a["z1"] - 1) >= 0.12: continue
        t = {"A": "C", "M": "C", "C": "A"}[b["tam"]]
        b.update(tam=t, z0=ZOOM[t], z1=ZOOM[t])
    for a, b in zip(planos, planos[1:]):               # M ↔ A en la misma cámara (12 %): casi un salto → el no forzado pasa a C
        if b["tipo"] == "broll" or not a.get("cam") or a["cam"] != b["cam"] or abs(b["z0"] / a["z1"] - 1) >= 0.12: continue
        x = b if not b.get("forzar") and not b.get("corto") else (a if not a.get("forzar") and not a.get("corto") else None)
        if x is not None and x["tam"] in ("A", "M"): x.update(tam="C", z0=ZOOM["C"], z1=ZOOM["C"])
    for a, b in zip(planos, planos[1:]):               # C ↔ C que quedó igual: el segundo más cerrado
        if b["tipo"] == "broll" or b.get("corto") or not a.get("cam") or a["cam"] != b["cam"] or abs(b["z0"] / a["z1"] - 1) >= 0.12: continue
        if b["tam"] == "C": b.update(z0=1.68, z1=1.68)
    i = 1                                             # pedacito sin cámara (< 1 s, p. ej. ninguna cámara grabó): lo absorbe el B-roll de al lado
    while SYNC and i < len(planos) - 1:
        p = planos[i]
        if p["tipo"] != "broll" and "f" not in p and p["n"] < FPS:
            q = planos[i + 1] if planos[i + 1]["tipo"] == "broll" else (planos[i - 1] if planos[i - 1]["tipo"] == "broll" else None)
            if q is not None:
                if q is planos[i + 1]: q["o"] = p["o"]
                q["n"] += p["n"]; del planos[i]; continue
        i += 1
    for g in gs:                                       # lado del capítulo según la cámara en pantalla
        if g["comp"] == "Capitulo":
            p = next((p for p in planos if p["o"] <= g["o"] < p["o"] + p["n"]), None)
            g["props"]["lado"] = "der" if p and p["cam"] == "cam1" else "izq"
    caps = [[0, "Introducción"]] + [[round((mic_a_o(t) / FPS)), tit] for t, tit in G["capitulos"]]
    json.dump({"fps": FPS, "total": TOTAL, "segs": SEGS, "planos": planos, "graficos": gs, "capitulos_yt": caps,
               "bloques": {"cold": [0, fin_c], "intro": [fin_c, fin_c + INTRO_N], "ep": [o_ep, fin_e], "final": [fin_e, TOTAL]}},
              open(W / "planos.json", "w"), indent=0)
    P_EP = o_ep
    n = np.array([p["n"] for p in planos]) / FPS
    from collections import Counter
    print(f"{len(planos)} planos · total {TOTAL / FPS / 60:.2f} min · duración p10/50/90 {np.percentile(n, [10, 50, 90]).round(1)} s · "
          f"< 1.5 s: {(n < 1.5).sum()} · reacciones {sum(p['tipo'] == 'reaccion' for p in planos)}")
    print("cámara/tamaño:", dict(Counter(f"{p['cam']}-{p['tam']}" for p in planos)))
    mal = sum(1 for a, b in zip(planos, planos[1:]) if a["cam"] == b["cam"] and a["tam"] == b["tam"] and a["cam"])
    hue = sum(1 for a, b in zip(planos, planos[1:]) if b["o"] != a["o"] + a["n"] and b["o"] != P_EP)
    print("huecos/encimados entre planos:", hue, "· B-roll:", sum(p["tipo"] == "broll" for p in planos))
    print("encuadres repetidos seguidos:", mal, "· sin archivo:", sum("f" not in p and p["tipo"] != "broll" for p in planos) if SYNC else "(sin sync todavía)")
