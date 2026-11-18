"""v2 del episodio: cortes de plan2.json + B-roll y tarjetas de covers.json sobre cada mirada al celular.

Uso:  python plan2.py && python pexels16.py && python render2.py
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, textwrap
from pathlib import Path
import numpy as np
from armar import W, D, CAM, MIC, FUENTES, NAVY, ORO

P = json.load(open(W / "plan2.json")); SEGS, DUR = P["segs"], P["dur"]
C = json.load(open(W / "covers.json"))
CEL = json.load(open(W / "celular_visible.json"))
OFF = json.load(open(W / "sync.json"))["mic_menos_cam"]
F8, F6, F4 = (str(FUENTES / f"poppins-{n}.ttf") for n in (800, 600, 400))
WHOOSH = kit.SFX / "whoosh-short.mp3"
ENC = ["-c:v", "h264_videotoolbox", "-b:v", "16M", "-pix_fmt", "yuv420p"]
FPS = "30000/1001"


def run(cmd):
    subprocess.run(cmd, check=True)


def base():
    pz = W / "piezas2"; pz.mkdir(exist_ok=True)
    caras = [q for q in json.load(open(W / "caras.json"))["cuadros"] if q and q[1] is not None]
    lista = []
    for i, s in enumerate(SEGS):
        t0, t1 = s["a"] - OFF, s["b"] - OFF
        qs = [q for q in caras if t0 <= q[0] <= t1] or [min(caras, key=lambda q: abs(q[0] - t0))]
        fx, fy = float(np.median([q[1] for q in qs])), float(np.median([q[2] for q in qs]))
        fh = float(np.median([q[4] for q in qs]))
        # el celular va en la mano izquierda a la altura de la cintura: el cuadro termina antes (cara + 2.6 alturas)
        z = max(1.18 if i % 2 == 0 else 1.36, 1080 / (2.6 * fh * 1080 / 0.64))
        for c0, c1, k in CEL:                                # revisado a ojo: aquí el celular entra al cuadro
            if c0 <= s["a"] < c1: z = max(z, 1080 / (k * fh * 1080 / 0.64))
        cw, ch = int(1920 / z) // 2 * 2, int(1080 / z) // 2 * 2
        cx = min(max(int(fx * 1920 - cw / 2), 0), 1920 - cw)
        cy = min(max(int(fy * 1080 - 0.36 * ch), 0), 1080 - ch)
        f = pz / f"q{i:03d}_{s['a']:.3f}_n{s['n']}_z{z:.3f}.mp4"
        if not f.exists():
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", str(CAM), "-frames:v", str(s["n"]), "-an",
                 "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale=1920:1080:flags=lanczos,unsharp=5:5:0.5,fps={FPS},format=yuv420p", *ENC, str(f)])
        lista.append(f"file '{f}'")
    (W / "lista2.txt").write_text("\n".join(lista) + "\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(W / "lista2.txt"), "-c", "copy", str(W / "base.mp4")])


def salida(m):
    """Tiempo del micrófono → tiempo del episodio."""
    for s in SEGS:
        if s["a"] <= m < s["b"]:
            return s["t"] + m - s["a"]


# ---------------------------------------------------------------- tarjetas
def txt(k, j, s):
    p = W / "tarjetas" / f"{k:02d}_{j}.txt"; p.write_text(s); return str(p)


def linea(k, j, s, fuente, tam, color, y, t0, x="(w-text_w)/2"):
    a = f"if(lt(t,{t0:.2f}),0,min(1,(t-{t0:.2f})/0.35))"
    yy = f"{y}+22*(1-min(1,max(0,(t-{t0:.2f})/0.35)))"
    return (f"drawtext=fontfile='{fuente}':textfile='{txt(k, j, s)}':expansion=none:fontsize={tam}:fontcolor={color}:"
            f"alpha='{a}':x={x}:y='{yy}'")


def bloque(k, j0, s, fuente, tam, color, y, t0, ancho):
    out = []
    for n, l in enumerate(textwrap.wrap(s, ancho)):
        out.append(linea(k, f"{j0}{n}", l, fuente, tam, color, y + n * int(tam * 1.3), t0))
    return out, y + len(textwrap.wrap(s, ancho)) * int(tam * 1.3)


def palabra(m_desde, m_hasta, w):
    """Tiempo de salida en que el presentador dice la palabra w entre dos tiempos de micrófono."""
    j = json.load(open(W / "mic16k.json"))
    for x in (x for sg in j["segments"] for x in sg.get("words", [])):
        if m_desde <= x["start"] <= m_hasta and w in x["word"].lower():
            return salida(x["start"])


def tarjeta(k, c):
    d = c["b"] - c["a"]; tipo = c["card"]
    vf = ["gblur=sigma=30", "eq=brightness=-0.10:saturation=0.5",
          f"drawbox=x=0:y=0:w=iw:h=ih:color={NAVY}@0.80:t=fill"]
    if tipo == "capitulo":
        vf.append(linea(k, "a", c["t1"], F8, 46, ORO, 400, 0.10))
        vf.append(f"drawbox=x=900:y=478:w=120:h=4:color={ORO}:t=fill:enable='gte(t,0.25)'")
        vf += bloque(k, "b", c["t2"], F6, 64, "white", 520, 0.35, 44)[0]
    elif tipo == "frase":
        l1, y = bloque(k, "a", c["t1"], F6, 58, "white", 380, 0.10, 46)
        l2, _ = bloque(k, "b", c["t2"], F8, 70, ORO, y + 20, 0.80, 40)
        vf += l1 + l2
    elif tipo == "lista":
        vf.append(linea(k, "a", c["t1"], F8, 50, ORO, 340, 0.10))
        desde = next(s["a"] for s in SEGS if s["t"] + s["b"] - s["a"] > c["a"])
        t2, t3 = palabra(desde, desde + 12, "objetivo"), palabra(desde, desde + 15, "tarea")
        vf.append(linea(k, "b", c["t2"], F6, 60, "white", 470, max(0.5, (t2 - c["a"] - 0.4) if t2 else 2.9)))
        vf.append(linea(k, "c", c["t3"], F6, 60, "white", 580, max(1.0, (t3 - c["a"] - 0.6) if t3 else 5.0)))
    elif tipo == "recap":
        m0 = SEGS[0]["a"]
        filas = kit.ep("recap")          # [[ETIQUETA, descripción, palabra que la dispara], ...]
        vf.append(linea(k, "a", "RECAPITULANDO", F8, 50, ORO, 300, 0.10))
        desde = next(s["a"] for s in SEGS if s["cap"] == "cierre")
        for n, (et, de, w) in enumerate(filas):
            t = palabra(desde, desde + 20, w)
            t0 = max(0.6, (t - c["a"] - 0.2) if t else 1.5 + 3.5 * n)
            vf.append(linea(k, f"r{n}e", et, F8, 56, ORO, 440 + n * 120, t0, x="340"))
            vf.append(linea(k, f"r{n}d", de, F6, 50, "white", 446 + n * 120, t0 + 0.15, x="800"))
    elif tipo == "final":
        vf.append(linea(k, "a", "PRÓXIMO VIDEO", F8, 46, ORO, 360, 0.10))
        l1, l2 = kit.ep("proximo_video", ["Título del próximo video", "segunda línea"])
        vf.append(linea(k, "b", l1, F6, 66, "white", 450, 0.35))
        vf.append(linea(k, "c", l2, F6, 66, "white", 540, 0.50))
        vf.append(linea(k, "d", "Suscríbete para no perdértelo", F4, 40, "white", 700, 1.2))
    vf.append(linea(k, "z", kit.espaciado(kit.MARCA["empresa"]), F8, 26, ORO + "@0.75", 975, 0.0))
    (W / "tarjetas" / f"{k:02d}.vf").write_text(",".join(vf))
    out = W / "tarjetas" / f"{k:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c['a']:.3f}", "-i", str(W / "base.mp4"), "-t", f"{d:.3f}",
         "-/filter:v", str(W / "tarjetas" / f"{k:02d}.vf"), "-an", *ENC, str(out)])
    return out


def broll(k, c):
    d = c["b"] - c["a"]; src = W / "broll" / f"{k:02d}.mp4"; out = W / "tarjetas" / f"{k:02d}.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", str(src), "-t", f"{d:.3f}", "-an", "-vf",
         f"fps={FPS},scale=w='trunc(1920*(1+0.05*t/{d:.2f})/2)*2':h=-2:eval=frame:flags=bicubic,"
         f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,eq=contrast=1.03:saturation=0.92,format=yuv420p",
         *ENC, str(out)])
    return out


def audio():
    n = len(SEGS); fc = ["[0:a]asplit=" + str(n) + "".join(f"[s{i}]" for i in range(n))]
    for i, s in enumerate(SEGS):
        d = s["b"] - s["a"]
        fc.append(f"[s{i}]atrim={s['a']:.6f}:{s['b']:.6f},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={d - 0.025:.3f}:d=0.025[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,highpass=f=80,"
              "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=1,deesser=i=0.3[voz]")
    golpes = [c["a"] for c in C if c.get("card") in ("capitulo", "recap", "final")]
    fc.append(f"[1:a]aformat=sample_rates=48000:channel_layouts=mono,volume=0.22,asplit={len(golpes)}" + "".join(f"[w{i}]" for i in range(len(golpes))))
    for i, t in enumerate(golpes):
        fc.append(f"[w{i}]adelay={int(max(t - 0.25, 0) * 1000)}[wd{i}]")
    fc.append("[voz]" + "".join(f"[wd{i}]" for i in range(len(golpes))) + f"amix=inputs={len(golpes) + 1}:normalize=0:duration=first,"
              "loudnorm=I=-14:TP=-1.5:LRA=9[aout]")
    (W / "audio2_fc.txt").write_text(";".join(fc))
    run(["ffmpeg", "-v", "error", "-y", "-i", str(MIC), "-i", str(WHOOSH), "-/filter_complex", str(W / "audio2_fc.txt"),
         "-map", "[aout]", "-ar", "48000", "-c:a", "pcm_s16le", str(W / "audio2.wav")])


def final():
    (W / "tarjetas").mkdir(exist_ok=True)
    clips = [(c, tarjeta(k, c) if "card" in c else broll(k, c)) for k, c in enumerate(C)]
    ins, fc, prev = ["-i", str(W / "base.mp4"), "-i", str(W / "audio2.wav")], [], "[0:v]"
    # rótulo con nombre al inicio de la presentación
    t0 = next(s["t"] for s in SEGS if s["cap"] == "intro") + 0.3; t1 = t0 + 4.2
    en = f"between(t,{t0:.2f},{t1:.2f})"
    (W / "tarjetas" / "lt_a.txt").write_text(kit.MARCA["nombre"]); (W / "tarjetas" / "lt_b.txt").write_text(kit.MARCA["rol"])
    fc.append(f"[0:v]drawbox=x=80:y=860:w=620:h=130:color={NAVY}@0.88:t=fill:enable='{en}',"
              f"drawbox=x=80:y=860:w=10:h=130:color={ORO}:t=fill:enable='{en}',"
              f"drawtext=fontfile='{F8}':textfile='{W / 'tarjetas' / 'lt_a.txt'}':fontcolor={ORO}:fontsize=40:x=118:y=876:enable='{en}',"
              f"drawtext=fontfile='{F6}':textfile='{W / 'tarjetas' / 'lt_b.txt'}':fontcolor=white:fontsize=29:x=118:y=936:enable='{en}'[b0]")
    prev = "[b0]"
    for k, (c, f) in enumerate(clips):
        d = c["b"] - c["a"]; fd = 0.18 if "card" in c else 0.08
        ins += ["-i", str(f)]
        fc.append(f"[{k + 2}:v]format=yuva420p,fade=t=in:st=0:d={fd}:alpha=1,fade=t=out:st={d - fd:.3f}:d={fd}:alpha=1,"
                  f"setpts=PTS-STARTPTS+{c['a']:.3f}/TB[c{k}]")
        fc.append(f"{prev}[c{k}]overlay=eof_action=pass:enable='between(t,{c['a']:.3f},{c['b']:.3f})'[v{k}]")
        prev = f"[v{k}]"
    fc[-1] = fc[-1].rsplit("[", 1)[0] + ",format=yuv420p[vout]"
    (W / "video2_fc.txt").write_text(";".join(fc))
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(W / "video2_fc.txt"), "-map", "[vout]", "-map", "1:a",
         "-c:v", "h264_videotoolbox", "-b:v", "14M", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
         str(D / "episodio_v2.mp4")])
    print("LISTO", D / "episodio_v2.mp4", f"{DUR / 60:.2f} min")


VEL = 1.10   # velocidad final (1.10× se aprobó en el episodio original)


def rapido():
    run(["ffmpeg", "-v", "error", "-y", "-i", str(D / "episodio_v2.mp4"), "-filter_complex",
         f"[0:v]setpts=PTS/{VEL},fps={FPS}[v];[0:a]atempo={VEL},loudnorm=I=-14:TP=-1.5:LRA=9[a]", "-map", "[v]", "-map", "[a]",
         "-c:v", "h264_videotoolbox", "-b:v", "14M", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(D / "episodio_v3.mp4")])
    print("LISTO", D / "episodio_v3.mp4", f"{DUR / VEL / 60:.2f} min")


if __name__ == "__main__":
    base(); audio(); final(); rapido()
