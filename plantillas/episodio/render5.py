"""v5 del episodio (modo editor): sobre la v4 agrega

- cámara con movimiento (base5.py: acercamientos, alejamientos y golpes de zoom en la palabra clave);
- celular detectado cuadro por cuadro con Apple Vision (celular5.json): plano más cerrado y, si aún se ve, B-roll encima;
- profundidad sutil y palabras grandes DETRÁS del presentador (silueta Apple Vision, matte5.mp4);
- música de fondo por capítulo (pistas con licencia) que baja sola cuando hablas;
- diseño sonoro con los efectos con licencia de 04-recursos/sfx/pixabay; destello en los capítulos.

Uso:  python base5.py && bin/matte base5.mp4 matte5.mp4 && python render5.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json
from pathlib import Path
import render4 as r4
from render4 import (W, D, G, T, F8, F6, F4, NAVY, ORO, FPS, ENC, SEGS, DUR, C, MIC, run, salida, dice, largo,
                     contenidos, paneles, S, texto, tarjeta, ventana, web, corte, capitulos, miradas_fuertes, duracion)

VEL, FIN = r4.VEL, r4.FIN
TOT = DUR + FIN
DESPLAZA, PANEL_W, X0 = r4.DESPLAZA, r4.PANEL_W, r4.X0
SFX = kit.SFX
MUS = kit.MUSICA
# una pista por capítulo, de tu carpeta de música con licencia: [[capítulo, archivo], ...]
MUSICA = kit.ep("musica_capitulos")
MUSICA_DB = -15      # nivel de la cama musical antes de que baje con la voz
# palabras grandes detrás del presentador: (palabra que dice, texto, color); solo donde no hay panel ni corte
HEROES = [(w, txt, ORO if c == "oro" else "white") for w, txt, c in kit.ep("heroes")]   # [[palabra que dice, TEXTO, "blanco"|"oro"], ...]


def unir(vs, hueco=0.5):
    out = []
    for a, b in sorted(vs):
        if out and a - out[-1][1] < hueco: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out


def miradas(yaw, pitch):
    import numpy as np
    f = json.load(open(W / "mirada16.json"))
    fl = np.array([1 if (q[1] and (q[1][0] > yaw or q[1][1] > pitch)) else 0 for q in f])
    fl = np.array([int(np.median(fl[max(0, k - 1):k + 2])) for k in range(len(fl))])
    mira = lambda tm: bool(fl[min(max(int(round((tm - r4.OFF) * 10)), 0), len(fl) - 1)])
    ven = []
    for sg in SEGS:
        k = sg["a"]
        while k < sg["b"]:
            if mira(k):
                k0 = k
                while k < sg["b"] and mira(k): k += 0.1
                if k - k0 >= 0.25: ven.append([sg["t"] + k0 - sg["a"] - 0.2, sg["t"] + k - sg["a"] + 0.2])
            k += 0.1
    return ven


def cortes5():
    # dentro de un panel el B-roll solo tapa el lado derecho: ahí también se cubren las miradas leves
    sp = paneles(contenidos())
    leves = [[a, b] for a, b in miradas(12, 3) if any(a < pb - 0.3 and b > pa + 0.3 for pa, pb in sp)]
    # v7: arranques de pieza con la cabeza abajo (revisados cuadro por cuadro): se tapan desde antes del corte
    # hasta 0.35 s después de que el presentador ya mira a cámara, para que no se vea cuando levanta la cabeza
    arr = [[x["a"] - 0.15, x["b"] + 0.35] for x in json.load(open(W / "arranques7.json"))]
    v = miradas_fuertes() + leves + json.load(open(W / "celular5.json")) + r4.FORZADOS + arr
    v = [[max(a, 0.0), min(b, DUR - 0.3)] for a, b in v]
    v = [[0.0, max(b, 1.05)] if a < 0.5 else [a, b] for a, b in v]          # arranque en frío sobre B-roll
    return [[round(a, 3), round(max(b, a + 0.9), 3)] for a, b in unir(v)]


def heroes(sp, cortes):
    ocup = [[a - 0.5, b + 0.5] for a, b in sp] + [[a - 0.2, b + 0.2] for a, b in cortes]
    out, usados = [], set()
    for w, et, color in HEROES:
        for x in r4.PAL:
            t = salida(x["start"])
            if t is None or w not in x["word"].lower() or (w, et) in usados: continue
            a, b = t - 0.08, t + 1.9
            if any(a < q1 and b > q0 for q0, q1 in ocup) or any(a < h["b"] + 0.8 and b > h["a"] - 0.8 for h in out): continue
            out.append({"a": a, "b": b, "et": et, "color": color}); usados.add((w, et)); break
    return sorted(out, key=lambda h: h["a"])


def heroe_vf(h):
    tam = int(min(250, 1750 / (0.7 * len(h["et"]))))
    a, b = h["a"], h["b"]
    fs = f"{tam * 0.82:.0f}+{tam * 0.18:.0f}*min(1,(t-{a:.3f})/0.35)"
    al = f"if(between(t,{a:.3f},{b:.3f}),min(1,(t-{a:.3f})/0.2)*min(1,({b:.3f}-t)/0.3),0)"
    p = T / f"h_{a:.2f}.txt"; p.write_text(h["et"])
    return (f"drawtext=fontfile='{F8}':textfile='{p}':expansion=none:fontsize='{fs}':fontcolor={h['color']}:alpha='{al}':"
            f"shadowcolor={NAVY}@0.55:shadowx=0:shadowy=8:"
            f"x=(w-text_w)/2:y=300-text_h/2:enable='between(t,{a:.3f},{b:.3f})'")


def panel5():
    """Panel de la v4 con un filo dorado que viaja con él."""
    from PIL import Image, ImageDraw
    im = Image.open(G / "panel.png").convert("RGBA"); d = ImageDraw.Draw(im)
    for y in range(1080):
        a = int(200 * min(1, y / 260, (1080 - y) / 260))
        d.line([(756, y), (758, y)], fill=(217, 180, 90, a))
    im.save(G / "panel5.png")


def audio5(eventos):
    """Voz + efectos (sin música: la música entra después de acelerar, para que no cambie su tempo)."""
    n = len(SEGS); fc = ["[0:a]asplit=" + str(n) + "".join(f"[s{i}]" for i in range(n))]
    for i, s in enumerate(SEGS):
        d = s["b"] - s["a"]; fo = 0.12 if i == n - 1 else 0.025
        fc.append(f"[s{i}]atrim={s['a']:.6f}:{s['b']:.6f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={d - fo:.4f}:d={fo}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,highpass=f=80,"
              f"acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=1,deesser=i=0.3,apad=whole_dur={TOT:.4f}[voz]")
    archivos = sorted({e[1] for e in eventos}); ins = ["-i", str(MIC)]
    for f in archivos: ins += ["-i", str(SFX / f)]
    cuenta = {f: sum(1 for e in eventos if e[1] == f) for f in archivos}
    for j, f in enumerate(archivos):
        fc.append(f"[{j + 1}:a]aformat=sample_rates=48000:channel_layouts=mono,asplit={cuenta[f]}" + "".join(f"[f{j}_{k}]" for k in range(cuenta[f])))
    usado = {f: 0 for f in archivos}; mez = []
    for i, (t, f, db) in enumerate(sorted(eventos)):
        j = archivos.index(f); k = usado[f]; usado[f] += 1
        fc.append(f"[f{j}_{k}]volume={db}dB,adelay={int(max(t, 0) * 1000)}[e{i}]"); mez.append(f"[e{i}]")
    fc.append("[voz]" + "".join(mez) + f"amix=inputs={len(mez) + 1}:normalize=0:duration=first[aout]")
    (T / "audio5_fc.txt").write_text(";".join(fc))
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(T / "audio5_fc.txt"), "-map", "[aout]",
         "-ar", "48000", "-c:a", "pcm_s16le", str(W / "audio5.wav")])


def secciones_musica():
    ini = {}
    for s in SEGS:
        cap = {"intro": "gancho", "guia": "leccion2", "cta": "cierre"}.get(s["cap"], s["cap"])
        ini.setdefault(cap, s["t"])
    tiempos = [(0.0 if cap == "gancho" else ini[cap], f) for cap, f in MUSICA]
    return [(t0, (tiempos[i + 1][0] if i + 1 < len(tiempos) else TOT), f) for i, (t0, f) in enumerate(tiempos)]


# v6: encuadre 1.18× anclado arriba: el borde inferior queda al cuello del saco y el celular (mano izquierda) nunca entra
RECORTE = "scale=2266:1274:flags=lanczos,crop=1920:1080:173:0,"


def final():
    cs = contenidos(); sp = paneles(cs); expr = S(sp); cortes = cortes5(); hs = heroes(sp, cortes)
    json.dump({"paneles": sp, "contenidos": cs, "cortes": cortes, "heroes": hs}, open(W / "plan5.json", "w"), ensure_ascii=False, indent=1)
    print(f"{len(sp)} paneles ({sum(b - a for a, b in sp):.0f} s) · {len(cortes)} cortes ({sum(b - a for a, b in cortes):.0f} s) · "
          f"{len(hs)} palabras detrás · de {DUR:.0f} s")
    panel5()
    ins = ["-i", str(W / "base5.mp4"), "-i", str(W / "audio5.wav"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "panel5.png"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "logo_250_sombra.png"),
           "-loop", "1", "-t", f"{TOT:.3f}", "-i", str(G / "logo_980.png"),
           "-i", str(W / "matte5.mp4")]
    # profundidad sutil + palabras detrás del presentador: fondo (algo suave) → texto → presentador recortado encima
    fc = [f"[0:v]tpad=stop_mode=clone:stop_duration={FIN + 0.2},trim=duration={TOT:.4f},setpts=PTS-STARTPTS,{RECORTE}split=2[ba][bb]",
          f"[5:v]tpad=stop_mode=clone:stop_duration={FIN + 0.2},trim=duration={TOT:.4f},setpts=PTS-STARTPTS,{RECORTE}format=gray,gblur=sigma=2[mt]",
          f"[ba]scale=960:540,gblur=sigma=1.6,scale=1920:1080,eq=brightness=-0.05:saturation=0.92"
          + "".join("," + heroe_vf(h) for h in hs) + "[fondo]",
          "[bb]format=yuva420p[bbf];[bbf][mt]alphamerge[persona]",
          "[fondo][persona]overlay=format=auto,format=yuv420p[b0]",
          f"color=c={NAVY}:s=1920x1080:r={FPS}:d={TOT:.4f}[bg]",
          f"[bg][b0]overlay=x='{DESPLAZA}*({expr})':y=0:eval=frame[v1]",
          f"[2:v]format=rgba[pn];[v1][pn]overlay=x='-{PANEL_W}+{PANEL_W}*({expr})':y=0:eval=frame[v2]"]
    prev, nin = "[v2]", 6
    vf = []; usado = {}
    for c in cs:
        p = next((a, b) for a, b in sp if a - 0.01 <= c["a"] and c["b"] <= b + 0.01)
        t0 = max(c["a"], p[0] + 0.3) if c["a"] - p[0] < 0.3 else c["a"] + 0.12
        t1 = min(c["b"], p[1] - 0.35) if p[1] - c["b"] < 0.35 else c["b"] - 0.12
        c["_t0"], c["_t1"] = t0, t1
        if c["tipo"] in ("ventana", "web"):
            if c["tipo"] == "ventana":
                f = ventana(len(usado), W / "broll" / f"{c['k']:02d}.mp4", 0.5, t1 - t0)
                usado[c["k"]] = 0.5 + (t1 - t0) + 0.3; x, y = X0, 363
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
        dentro = any(a < pb and b > pa for pa, pb in sp)
        f = corte(n, src, ss, b - a, 1160 if dentro else 1920); ins += ["-i", str(f)]
        fi = "" if a < 0.05 else "fade=t=in:st=0:d=0.08:alpha=1,"
        fc.append(f"[{nin}:v]format=yuva420p,{fi}fade=t=out:st={b - a - 0.08:.3f}:d=0.08:alpha=1,"
                  f"setpts=PTS-STARTPTS+{a:.3f}/TB[c{nin}]")
        fc.append(f"{prev}[c{nin}]overlay=x={760 if dentro else 0}:eof_action=pass:enable='between(t,{a:.3f},{b:.3f})'[o{nin}]")
        prev = f"[o{nin}]"; nin += 1
    # arranque en frío: el título encima del primer B-roll
    vf.append(texto("DUEÑO DE NEGOCIOS", F8, 112, "white", "(w-text_w)/2", 470, 0.0, cortes[0][1] - 0.02, sube=30))
    # destello breve al entrar cada capítulo
    for c in cs:
        if c["tipo"] in ("capitulo", "recap"):
            vf.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.30:t=fill:enable='between(t,{c['a']:.3f},{c['a'] + 0.07:.3f})'")
            vf.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.12:t=fill:enable='between(t,{c['a'] + 0.07:.3f},{c['a'] + 0.14:.3f})'")
    for a, b, et in capitulos():
        w = int(largo(et, F6, 22)) + 48; en = f"between(t,{a + 0.2:.3f},{b:.3f})"
        vf.append(f"drawbox=x=60:y=50:w={w}:h=46:color={NAVY}@0.85:t=fill:enable='{en}'")
        vf.append(f"drawbox=x=60:y=50:w=6:h=46:color={ORO}:t=fill:enable='{en}'")
        vf.append(texto(et, F6, 22, "white", 84, 60, a + 0.2, b, sube=0))
    fc.append(f"{prev}" + ",".join(vf) + "[tx]")
    fc.append("[3:v]format=rgba,colorchannelmixer=aa=0.95[lg]")
    fc.append(f"[tx][lg]overlay=x=W-w-44:y=46:enable='lt(t,{DUR + 0.1:.3f})'[v3]")
    fc.append(f"color=c={NAVY}:s=1920x1080:r={FPS}:d={TOT:.4f},format=rgba,fade=t=in:st={DUR - 0.1:.3f}:d=0.4:alpha=1[fin]")
    fc.append(f"[v3][fin]overlay=enable='gte(t,{DUR - 0.1:.3f})'[v4]")
    fc.append(f"[4:v]format=rgba,fade=t=in:st={DUR + 0.15:.3f}:d=0.5:alpha=1[lg2]")
    fc.append(f"[v4][lg2]overlay=x=(W-w)/2:y='440+30*pow(1-min(1,max(0,(t-{DUR + 0.15:.3f})/0.6)),2)':eval=frame:"
              f"enable='gte(t,{DUR + 0.1:.3f})',"
              + texto(kit.MARCA["web"], F6, 44, ORO, "(w-text_w)/2", 600, DUR + 0.6, TOT + 1) + ","
              + texto(kit.MARCA["eslogan"], F4, 30, "white@0.85", "(w-text_w)/2", 670, DUR + 0.8, TOT + 1)
              + ",scale=out_range=tv,format=yuv420p[vout]")
    (T / "video5_fc.txt").write_text(";\n".join(fc))

    # diseño sonoro (efectos Pixabay con licencia comercial)
    ev = [(a - 0.12, "whoosh-short.mp3", -14) for a, b in sp]
    ev += [(c["a"] - 0.3, "whoosh-cinematic.mp3", -12) for c in cs if c["tipo"] in ("capitulo", "recap")]
    ev += [(h["a"], "impact-bass-1.mp3", -13) for h in hs]
    ev += [(c["a"] + 0.3, "click-soft.mp3", -18) for c in cs if c["tipo"] in ("frase", "lista")]
    ev += [(DUR + 0.1, "sparkle.mp3", -12)]
    for w in ("tres", "7", "4", "commerce", "comercializadoras", "joyerías", "despachos"):
        t = dice(w, 20, 40)
        if t: ev.append((t - 0.1, "pop.mp3" if w in ("tres", "7", "4") else "click-soft.mp3", -16))
    ev = sorted(ev); limpio = []
    for e in ev:                                    # no amontonar efectos
        if limpio and e[0] - limpio[-1][0] < 0.3:
            if e[2] > limpio[-1][2]: limpio[-1] = e
            continue
        limpio.append(e)
    audio5(limpio)
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(T / "video5_fc.txt"), "-map", "[vout]", "-map", "1:a",
         "-t", f"{TOT:.3f}", "-c:v", "h264_videotoolbox", "-b:v", "18M", "-c:a", "pcm_s16le", str(D / "episodio_v7_lento.mov")])
    acelerar()


def acelerar():
    """1.1× y la música por capítulo, que baja sola cuando el presentador habla."""
    secs = secciones_musica(); ins = ["-i", str(D / "episodio_v7_lento.mov")]
    fc = [f"[0:v]setpts=PTS/{VEL},fps={FPS}[v]", f"[0:a]atempo={VEL},asplit=2[voz][llave]"]
    for i, (t0, t1, f) in enumerate(secs):
        ins += ["-stream_loop", "-1", "-i", str(MUS / f)]
        a, b = t0 / VEL, t1 / VEL; dur = b - a + (1.5 if i + 1 < len(secs) else 0)
        fi = 0.4 if i == 0 else 1.5
        sube = f",volume=7dB:enable='gte(t,{DUR / VEL - a:.3f})'" if i + 1 == len(secs) else ""
        fc.append(f"[{i + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={dur:.3f},asetpts=PTS-STARTPTS,"
                  f"volume={MUSICA_DB}dB{sube},afade=t=in:d={fi},afade=t=out:st={dur - 1.6:.3f}:d=1.6,adelay={int(a * 1000)}:all=1[m{i}]")
    fc.append("".join(f"[m{i}]" for i in range(len(secs))) + f"amix=inputs={len(secs)}:normalize=0:duration=longest,"
              f"atrim=duration={TOT / VEL:.3f}[mus]")
    fc.append("[llave]aformat=channel_layouts=stereo[ll]")
    fc.append("[mus][ll]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=450:makeup=1[musd]")
    fc.append("[voz]aformat=channel_layouts=stereo[vz];[vz][musd]amix=inputs=2:normalize=0:duration=first,"
              "loudnorm=I=-14:TP=-1.5:LRA=9[a]")
    (T / "acelerar5_fc.txt").write_text(";\n".join(fc))
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(T / "acelerar5_fc.txt"), "-map", "[v]", "-map", "[a]",
         "-c:v", "h264_videotoolbox", "-b:v", "16M", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
         str(D / "episodio_v7.mp4")])
    print("LISTO", D / "episodio_v7.mp4", f"{TOT / VEL / 60:.2f} min")


if __name__ == "__main__":
    final()
