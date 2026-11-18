"""v4 del episodio: la cara del presentador siempre visible.

En vez de tapar toda la pantalla, el cuadro se desliza a la derecha y entra un panel lateral con el contenido
(tarjetas animadas, B-roll en ventana, contadores, tu web). Solo las miradas fuertes al celular
se cubren con un corte de B-roll a pantalla completa, corto. Logo oficial siempre arriba a la derecha.

Uso:  python plan2.py && python -c "import render2 as r; r.base()" && python graficos4.py && python render4.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, re, subprocess, textwrap
from pathlib import Path
import numpy as np
from PIL import ImageFont
from armar import W, D, FUENTES, NAVY, ORO
from render2 import SEGS, DUR, C, OFF, MIC, WHOOSH, FPS, ENC, run, salida

F8, F6, F4 = (str(FUENTES / f"poppins-{n}.ttf") for n in (800, 600, 400))
G = W / "marca"; T = W / "tarjetas4"; T.mkdir(exist_ok=True)
VEL = 1.10          # velocidad final (1.10× se aprobó en el episodio original)
FIN = 2.2           # cierre con logo después de la última palabra
TOT = DUR + FIN
DESPLAZA, PANEL_W = 330, 1100
RAMPA = 0.45
FORZADOS = kit.ep("forzados", [])   # tramos que siempre se tapan [[a, b], ...] en tiempo de salida (antes de la velocidad)
X0 = 90             # margen izquierdo del contenido del panel
ANCHO = 620         # ancho útil del contenido

PAL = [w for sg in json.load(open(W / "mic16k.json"))["segments"] for w in sg.get("words", [])]


def dice(w, desde, hasta):
    """Tiempo de salida en que el presentador dice w (buscado entre dos tiempos de salida)."""
    for x in PAL:
        t = salida(x["start"])
        if t is not None and desde <= t <= hasta and w in x["word"].lower():
            return t


def largo(s, fuente, tam):
    return ImageFont.truetype(fuente, tam).getlength(s)


def envolver(s, fuente, tam, ancho=ANCHO):
    out, cur = [], ""
    for p in s.split():
        prueba = (cur + " " + p).strip()
        if cur and largo(prueba, fuente, tam) > ancho: out.append(cur); cur = p
        else: cur = prueba
    return out + [cur]


# ---------------------------------------------------------------- 1) qué va en cada momento
def miradas_fuertes():
    f = json.load(open(W / "mirada16.json"))
    fl = np.array([1 if (q[1] and (q[1][0] > 20 or q[1][1] > 6)) else 0 for q in f])
    fl = np.array([int(np.median(fl[max(0, k - 1):k + 2])) for k in range(len(fl))])
    mira = lambda tm: bool(fl[min(max(int(round((tm - OFF) * 10)), 0), len(fl) - 1)])
    ven = []
    for sg in SEGS:
        k = sg["a"]
        while k < sg["b"]:
            if mira(k):
                k0 = k
                while k < sg["b"] and mira(k): k += 0.1
                if k - k0 >= 0.25: ven.append([sg["t"] + k0 - sg["a"] - 0.2, sg["t"] + k - sg["a"] + 0.2])
            k += 0.1
    out = []
    for a, b in ven:
        if out and a - out[-1][1] < 0.8: out[-1][1] = b
        else: out.append([a, b])
    out = [[a, max(b, a + 1.0)] for a, b in out if a > 3]
    for a, b in FORZADOS:                              # revisados a ojo: el celular en la mano y el detector no lo marca
        out = [v for v in out if v[1] < a or v[0] > b] + [[a, b]]
    out.sort()
    return [[round(a, 3), round(min(b, DUR - 0.5), 3)] for a, b in out]


def contenidos():
    cta = next(s["t"] for s in SEGS if s["cap"] == "cta")
    out, da = [], kit.ep("datos", None)   # tarjeta "quién soy": entra en la palabra datos.desde y sale en datos.hasta
    if da:
        (w0, a0, b0), (w1, a1, b1) = da["desde"], da["hasta"]
        out.append({"a": dice(w0, a0, b0) - 0.15, "b": dice(w1, a1, b1) + 1.1, "tipo": "datos"})
    for k, c in enumerate(C):
        if c["a"] >= cta - 0.5 or (out and out[0]["a"] - 0.5 < c["a"] < out[0]["b"]): continue
        if "broll" in c:
            if not (W / "broll" / f"{k:02d}.mp4").exists(): continue
            out.append({"a": c["a"], "b": min(c["b"], c["a"] + 4.0), "tipo": "ventana", "k": k})
        elif c["card"] != "final":
            out.append({**c, "tipo": c["card"]})
    out.append({"a": cta - 0.1, "b": DUR + 0.6, "tipo": "web"})
    out.sort(key=lambda c: c["a"])
    for i in range(1, len(out)):                      # sin solapes entre contenidos
        out[i]["a"] = max(out[i]["a"], out[i - 1]["b"])
    return [c for c in out if c["b"] - c["a"] > 1.2]


def paneles(cs):
    sp = []
    for c in cs:
        if sp and c["a"] - sp[-1][1] < 2.6: sp[-1][1] = c["b"]
        else: sp.append([c["a"], c["b"]])
    return sp


def S(sp):
    """Expresión ffmpeg: 0 = cuadro normal, 1 = cuadro a la derecha con panel (curva suave)."""
    return "+".join(f"(1-cos(PI*min(clip((t-{a:.3f})/{RAMPA},0,1),clip(({b:.3f}-t)/{RAMPA},0,1))))/2" for a, b in sp)


# ---------------------------------------------------------------- 2) textos animados
_n = [0]


def texto(s, fuente, tam, color, x, y, t0, t1, sube=26, expansion=False):
    _n[0] += 1
    a = f"if(between(t,{t0:.3f},{t1:.3f}),min(1,(t-{t0:.3f})/0.35)*min(1,({t1:.3f}-t)/0.25),0)"
    yy = f"{y}+{sube}*pow(1-min(1,max(0,(t-{t0:.3f})/0.4)),2)"
    if expansion:
        fuente_txt = f"text='{s}'"
    else:
        p = T / f"t{_n[0]:03d}.txt"; p.write_text(s); fuente_txt = f"textfile='{p}':expansion=none"
    return (f"drawtext=fontfile='{fuente}':{fuente_txt}:fontsize={tam}:fontcolor={color}:alpha='{a}':"
            f"x={x}:y='{yy}':enable='between(t,{t0:.3f},{t1:.3f})'")


def barra(x, y, w, h, color, t0, t1):
    # barra que crece de izquierda a derecha
    return f"drawbox=x={x}:y={y}:w={w}:h={h}:color={color}:t=fill:enable='between(t,{t0 + 0.15:.3f},{t1:.3f})'"


def bloque(lineas, fuente, tam, color, y, t0, t1, paso=0.12):
    out = []
    for n, l in enumerate(lineas):
        out.append(texto(l, fuente, tam, color, X0, y + n * int(tam * 1.22), t0 + n * paso, t1))
    return out, y + len(lineas) * int(tam * 1.22)


def tarjeta(c, t0, t1):
    tipo, vf = c["tipo"], []
    if tipo == "capitulo":
        l2 = envolver(c["t2"], F8, 60)
        h = 50 + 30 + len(l2) * 73; y = 540 - h // 2
        vf.append(texto(c["t1"], F8, 40, ORO, X0, y, t0, t1))
        vf.append(barra(X0, y + 62, 80, 6, ORO, t0, t1))
        vf += bloque(l2, F8, 60, "white", y + 92, t0 + 0.2, t1)[0]
    elif tipo == "frase":
        l1, l2 = envolver(c["t1"], F6, 48), envolver(c["t2"], F8, 60)
        h = len(l1) * 58 + 30 + len(l2) * 73; y = 540 - h // 2
        a, y2 = bloque(l1, F6, 48, "white", y, t0, t1)
        b, _ = bloque(l2, F8, 60, ORO, y2 + 30, t0 + 0.6, t1)
        vf += a + b
    elif tipo == "lista":
        desde = c["a"] - 2
        ta, tb = dice("objetivo", desde, desde + 14), dice("tarea", desde, desde + 16)
        y = 330
        vf.append(texto(c["t1"], F8, 40, ORO, X0, y, t0, t1)); vf.append(barra(X0, y + 62, 80, 6, ORO, t0, t1))
        a, y2 = bloque(envolver(c["t2"], F6, 46), F6, 46, "white", y + 100, max(t0 + 0.4, (ta or 0) - 0.4), t1)
        b, _ = bloque(envolver(c["t3"], F6, 46), F6, 46, "white", y2 + 40, max(t0 + 1.0, (tb or 0) - 0.5), t1)
        vf += a + b
    elif tipo == "recap":
        filas = kit.ep("recap")          # [[ETIQUETA, descripción, palabra que la dispara], ...]
        vf.append(texto("RECAPITULANDO", F8, 40, ORO, X0, 250, t0, t1)); vf.append(barra(X0, 312, 80, 6, ORO, t0, t1))
        for n, (et, de, w) in enumerate(filas):
            t = dice(w, c["a"] - 1, c["b"]) or (t0 + 0.5 + 3 * n)
            y = 370 + n * 170
            vf.append(texto(f"0{n + 1}", F8, 30, ORO + "@0.7", X0, y + 8, t - 0.2, t1))
            vf.append(texto(et, F8, 56, "white", X0 + 70, y, t - 0.2, t1))
            vf += bloque(envolver(de, F4, 34, ANCHO - 70), F4, 34, "white@0.85", y + 74, t - 0.05, t1)[0]
    elif tipo == "datos":
        vf.append(texto(kit.MARCA["nombre"].upper(), F8, 46, ORO, X0, 200, t0, t1))
        vf.append(texto(kit.MARCA["rol"], F6, 32, "white", X0, 262, t0 + 0.15, t1))
        vf.append(barra(X0, 318, 80, 6, ORO, t0, t1))
        filas = kit.ep("datos")["contadores"]   # [[palabra que lo dispara, signo, número, etiqueta], ...] — solo cifras reales
        for n, (w, signo, num, et) in enumerate(filas):
            t = dice(w, t0, t1) or (t0 + 2 + 3 * n)
            y = 360 + n * 125
            cnt = f"{signo}%{{eif\\:clip(floor((t-{t - 0.1:.3f})*9)+1\\,1\\,{num})\\:d}}"
            vf.append(texto(cnt, F8, 100, "white", X0, y, t - 0.1, t1, expansion=True))
            vf.append(texto(et, F6, 38, ORO, X0 + 170, y + 40, t + 0.05, t1))
        chips = kit.ep("datos")["chips"]        # [[palabra que lo dispara, etiqueta], ...]
        x, y = X0, 760
        for w, et in chips:
            t = dice(w, t0, t1) or t1 - 3
            ancho = int(largo(et, F6, 28)) + 44
            if x + ancho > X0 + ANCHO: x, y = X0, y + 70
            en = f"between(t,{t - 0.1:.3f},{t1:.3f})"
            vf.append(f"drawbox=x={x}:y={y}:w={ancho}:h=54:color={ORO}@0.18:t=fill:enable='{en}'")
            vf.append(f"drawbox=x={x}:y={y}:w={ancho}:h=54:color={ORO}@0.9:t=2:enable='{en}'")
            vf.append(texto(et, F6, 28, "white", x + 22, y + 9, t - 0.1, t1, sube=0))
            x += ancho + 16
    elif tipo == "web":
        vf.append(texto(kit.MARCA["cta_titulo"].upper(), F8, 42, ORO, X0, 150, t0, t1))
        vf.append(texto(kit.MARCA["cta_sub"], F6, 30, "white", X0, 210, t0 + 0.15, t1))
        vf.append(texto(kit.MARCA["web"], F8, 54, "white", X0, 780, t0 + 0.6, t1))
        vf.append(barra(X0, 856, 80, 6, ORO, t0 + 0.6, t1))
    return vf


# ---------------------------------------------------------------- 3) clips (ventana, web, cortes)
_dur = {}


def duracion(p):
    if p not in _dur:
        e = subprocess.run(["ffmpeg", "-i", str(p)], capture_output=True, text=True).stderr
        h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e).groups(); _dur[p] = int(h) * 3600 + int(m) * 60 + float(s)
    return _dur[p]


def ventana(n, src, ss, d):
    out = T / f"win{n:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.2f}", "-i", str(src), "-i", str(G / "win_mask.png"), "-i", str(G / "win_borde.png"),
         "-t", f"{d:.3f}", "-an", "-filter_complex",
         f"[0:v]fps={FPS},scale=w='trunc(700*(1+0.08*t/{d:.2f})/2)*2':h=-2:eval=frame,scale=630:354:force_original_aspect_ratio=increase,"
         f"crop=630:354,eq=contrast=1.04:saturation=0.95,format=rgba[v];[v][1:v]alphamerge[m];"
         f"color=c={NAVY}:s=630x354:r={FPS}[bg];[bg][m]overlay=shortest=1[o];[o][2:v]overlay,format=yuv420p",
         *ENC, str(out)])
    return out


def web(d):
    out = T / "web.mp4"; src = G / "web_scroll.mp4"; f = d / duracion(src)
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-i", str(G / "barra.png"), "-i", str(G / "web_mask.png"), "-i", str(G / "web_borde.png"),
         "-t", f"{d:.3f}", "-an", "-filter_complex",
         f"[0:v]setpts=PTS*{f:.4f},fps={FPS},scale=640:400:flags=lanczos,pad=640:434:0:34:color={NAVY},format=rgba[w];"
         f"[w][1:v]overlay=0:0[wb];[wb][2:v]alphamerge[m];color=c={NAVY}:s=640x434:r={FPS}[bg];[bg][m]overlay=shortest=1[o];"
         f"[o][3:v]overlay,tpad=stop_mode=clone:stop_duration=10,format=yuv420p", *ENC, str(out)])
    return out


def corte(n, src, ss, d, w=1920):
    out = T / f"full{n:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.2f}", "-i", str(src), "-t", f"{d:.3f}", "-an", "-vf",
         f"fps={FPS},scale=w='trunc(1920*(1+0.06*t/{d:.2f})/2)*2':h=-2:eval=frame:flags=bicubic,"
         f"scale={w}:1080:force_original_aspect_ratio=increase,crop={w}:1080,eq=contrast=1.04:saturation=0.92,format=yuv420p",
         *ENC, str(out)])
    return out


# ---------------------------------------------------------------- 4) audio
def audio(golpes):
    n = len(SEGS); fc = ["[0:a]asplit=" + str(n) + "".join(f"[s{i}]" for i in range(n))]
    for i, s in enumerate(SEGS):
        d = s["b"] - s["a"]; fo = 0.12 if i == n - 1 else 0.025
        fc.append(f"[s{i}]atrim={s['a']:.6f}:{s['b']:.6f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={d - fo:.4f}:d={fo}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,highpass=f=80,"
              f"acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=1,deesser=i=0.3,apad=whole_dur={TOT:.4f}[voz]")
    fc.append(f"[1:a]aformat=sample_rates=48000:channel_layouts=mono,asplit={len(golpes)}" + "".join(f"[w{i}]" for i in range(len(golpes))))
    for i, (t, v) in enumerate(golpes):
        fc.append(f"[w{i}]volume={v},adelay={int(max(t - 0.2, 0) * 1000)}[wd{i}]")
    fc.append("[voz]" + "".join(f"[wd{i}]" for i in range(len(golpes))) + f"amix=inputs={len(golpes) + 1}:normalize=0:duration=first[aout]")
    (T / "audio_fc.txt").write_text(";".join(fc))
    run(["ffmpeg", "-v", "error", "-y", "-i", str(MIC), "-i", str(WHOOSH), "-/filter_complex", str(T / "audio_fc.txt"),
         "-map", "[aout]", "-ar", "48000", "-c:a", "pcm_s16le", str(W / "audio4.wav")])


# ---------------------------------------------------------------- 5) todo junto
def capitulos():
    nombres = {"leccion1": "LECCIÓN 1 · PLATAFORMA", "leccion2": "LECCIÓN 2 · AGENTES", "guia": "LECCIÓN 2 · AGENTES",
               "leccion3": "LECCIÓN 3 · EQUIPO", "cierre": "RECAPITULANDO"}
    out = []
    for s in SEGS:
        et = nombres.get(s["cap"])
        if out and out[-1][2] == et: out[-1][1] = s["t"] + s["b"] - s["a"]
        elif et: out.append([s["t"], s["t"] + s["b"] - s["a"], et])
    return out


def final():
    cs, cortes = contenidos(), miradas_fuertes()
    sp = paneles(cs); expr = S(sp)
    plan = {"paneles": sp, "contenidos": cs, "cortes": cortes}
    json.dump(plan, open(W / "plan4.json", "w"), ensure_ascii=False, indent=1)
    en_panel = sum(b - a for a, b in sp); en_corte = sum(b - a for a, b in cortes)
    print(f"{len(sp)} paneles ({en_panel:.0f} s) · {len(cs)} contenidos · {len(cortes)} cortes ({en_corte:.0f} s) de {DUR:.0f} s")

    ins = ["-i", str(W / "base.mp4"), "-i", str(W / "audio4.wav"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "panel.png"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "logo_250_sombra.png"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "logo_980.png")]
    fc = [f"[0:v]tpad=stop_mode=clone:stop_duration={FIN + 0.2},trim=duration={TOT:.4f},setpts=PTS-STARTPTS[b0]",
          f"color=c={NAVY}:s=1920x1080:r={FPS}:d={TOT:.4f}[bg]",
          f"[bg][b0]overlay=x='{DESPLAZA}*({expr})':y=0:eval=frame[v1]",
          f"[2:v]format=rgba[pn];[v1][pn]overlay=x='-{PANEL_W}+{PANEL_W}*({expr})':y=0:eval=frame[v2]"]
    prev, nin = "[v2]", 5

    # textos de cada contenido + clips (ventanas y web)
    vf = []; usado = {}
    for c in cs:
        p = next((a, b) for a, b in sp if a - 0.01 <= c["a"] and c["b"] <= b + 0.01)
        t0 = max(c["a"], p[0] + 0.3) if c["a"] - p[0] < 0.3 else c["a"] + 0.12
        t1 = min(c["b"], p[1] - 0.35) if p[1] - c["b"] < 0.35 else c["b"] - 0.12
        c["_t0"], c["_t1"] = t0, t1
        if c["tipo"] in ("ventana", "web"):
            if c["tipo"] == "ventana":
                src = W / "broll" / f"{c['k']:02d}.mp4"
                f = ventana(len(usado), src, 0.5, t1 - t0); usado[c["k"]] = 0.5 + (t1 - t0) + 0.3; x, y = X0, 363
            else:
                f = web(TOT - t0); x, y = 80, 290
            ins += ["-i", str(f)]
            fc.append(f"[{nin}:v]format=yuva420p,fade=t=in:st=0:d=0.3:alpha=1,"
                      + (f"fade=t=out:st={t1 - t0 - 0.25:.3f}:d=0.25:alpha=1," if c["tipo"] == "ventana" else "")
                      + f"setpts=PTS-STARTPTS+{t0:.3f}/TB[c{nin}]")
            fc.append(f"{prev}[c{nin}]overlay=x='{x}-50*pow(1-min(1,max(0,(t-{t0:.3f})/0.45)),2)':y={y}:eval=frame:"
                      f"eof_action=pass:enable='between(t,{t0:.3f},{t1 if c['tipo'] == 'ventana' else TOT:.3f})'[o{nin}]")
            prev = f"[o{nin}]"; nin += 1
        vf += tarjeta(c, t0, t1 if c["tipo"] != "web" else TOT - 0.05)
    # cortes a pantalla completa sobre miradas fuertes: B-roll del contenido más cercano, sin repetir tramo
    fuentes = [(c["a"], c["k"]) for c in cs if c["tipo"] == "ventana"] + [(cv["a"], k) for k, cv in enumerate(C)
               if "broll" in cv and (W / "broll" / f"{k:02d}.mp4").exists()]
    en_cortes = set()
    for n, (a, b) in enumerate(cortes):
        en_ventana = {c["k"] for c in cs if c["tipo"] == "ventana" and c["a"] < b + 1 and c["b"] > a - 1}
        libres = [q for q in fuentes if q[1] not in en_ventana and q[1] not in en_cortes] or [q for q in fuentes if q[1] not in en_ventana]
        k = min(libres, key=lambda q: abs(q[0] - a))[1]; en_cortes.add(k); src = W / "broll" / f"{k:02d}.mp4"
        ss = usado.get(k, 0.5)
        if ss + (b - a) > duracion(src) - 0.2: ss = 0.5
        usado[k] = ss + (b - a) + 0.2
        # dentro de un panel solo se tapa el lado derecho (la cara); el panel y su texto siguen a la vista
        dentro = any(a < pb and b > pa for pa, pb in sp)
        f = corte(n, src, ss, b - a, 1160 if dentro else 1920); ins += ["-i", str(f)]
        fc.append(f"[{nin}:v]format=yuva420p,fade=t=in:st=0:d=0.08:alpha=1,fade=t=out:st={b - a - 0.08:.3f}:d=0.08:alpha=1,"
                  f"setpts=PTS-STARTPTS+{a:.3f}/TB[c{nin}]")
        fc.append(f"{prev}[c{nin}]overlay=x={760 if dentro else 0}:eof_action=pass:enable='between(t,{a:.3f},{b:.3f})'[o{nin}]")
        prev = f"[o{nin}]"; nin += 1
    # capítulo fijo arriba a la izquierda
    for a, b, et in capitulos():
        w = int(largo(et, F6, 22)) + 48; en = f"between(t,{a + 0.2:.3f},{b:.3f})"
        vf.append(f"drawbox=x=60:y=50:w={w}:h=46:color={NAVY}@0.85:t=fill:enable='{en}'")
        vf.append(f"drawbox=x=60:y=50:w=6:h=46:color={ORO}:t=fill:enable='{en}'")
        vf.append(texto(et, F6, 22, "white", 84, 60, a + 0.2, b, sube=0))
    fc.append(f"{prev}" + ",".join(vf) + "[tx]")
    # logo oficial siempre (arriba a la derecha) y cierre con el logo grande
    fc.append(f"[3:v]format=rgba,colorchannelmixer=aa=0.95[lg]")
    fc.append(f"[tx][lg]overlay=x=W-w-44:y=46:enable='lt(t,{DUR + 0.1:.3f})'[v3]")
    fc.append(f"color=c={NAVY}:s=1920x1080:r={FPS}:d={TOT:.4f},format=rgba,"
              f"fade=t=in:st={DUR - 0.1:.3f}:d=0.4:alpha=1[fin]")
    fc.append(f"[v3][fin]overlay=enable='gte(t,{DUR - 0.1:.3f})'[v4]")
    fc.append(f"[4:v]format=rgba,fade=t=in:st={DUR + 0.15:.3f}:d=0.5:alpha=1[lg2]")
    fc.append(f"[v4][lg2]overlay=x=(W-w)/2:y='440+30*pow(1-min(1,max(0,(t-{DUR + 0.15:.3f})/0.6)),2)':eval=frame:"
              f"enable='gte(t,{DUR + 0.1:.3f})',"
              + texto(kit.MARCA["web"], F6, 44, ORO, "(w-text_w)/2", 600, DUR + 0.6, TOT + 1) + ","
              + texto(kit.MARCA["eslogan"], F4, 30, "white@0.85", "(w-text_w)/2", 670, DUR + 0.8, TOT + 1)
              + ",scale=out_range=tv,format=yuv420p[vout]")
    (T / "video_fc.txt").write_text(";\n".join(fc))

    golpes = [(a, 0.14) for a, b in sp] + [(DUR - 0.1, 0.2)]
    golpes += [(c["a"], 0.2) for c in cs if c["tipo"] in ("capitulo", "recap")]
    audio(sorted(golpes))
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(T / "video_fc.txt"), "-map", "[vout]", "-map", "1:a",
         "-t", f"{TOT:.3f}", "-c:v", "h264_videotoolbox", "-b:v", "16M", "-c:a", "pcm_s16le", str(D / "episodio_v4_lento.mov")])
    run(["ffmpeg", "-v", "error", "-y", "-i", str(D / "episodio_v4_lento.mov"), "-filter_complex",
         f"[0:v]setpts=PTS/{VEL},fps={FPS}[v];[0:a]atempo={VEL},loudnorm=I=-14:TP=-1.5:LRA=9[a]", "-map", "[v]", "-map", "[a]",
         "-c:v", "h264_videotoolbox", "-b:v", "14M", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
         str(D / "episodio_v4.mp4")])
    print("LISTO", D / "episodio_v4.mp4", f"{TOT / VEL / 60:.2f} min")


if __name__ == "__main__":
    final()
