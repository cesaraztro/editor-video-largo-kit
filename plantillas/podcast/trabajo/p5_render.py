"""Podcast · render a partir de planos.json.

  piezas  → cada plano: recorte + zoom (y acercamiento lento) desde su archivo de cámara, cuadros exactos → base.mp4
  audio   → voz por tramos con micro-fundidos (numpy, al cuadro exacto) + música en avance/intro/cierre + efectos → −14 LUFS
  graficos→ Remotion (ProRes 4444 con alfa)
  final   → base + gráficos + logo → video.mp4
Uso:  $PY p5_render.py [piezas|audio|graficos|final|todo]
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import hashlib, json, subprocess, sys, wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

W = Path(__file__).parent
EP = W.parent
CR = EP / "crudos"
GR = EP / "graficos"
OUT = EP / "render"; OUT.mkdir(exist_ok=True)
PZ = OUT / "piezas"; PZ.mkdir(exist_ok=True)
P = json.load(open(W / "planos.json"))
FPS = P["fps"]; FPS_S = "30000/1001"
SR = 48000
MUSICA = kit.MUSICA / kit.ep("musica")
SFX = kit.SFX
ENC = ["-c:v", "h264_videotoolbox", "-b:v", "32M", "-pix_fmt", "yuv420p", "-r", FPS_S]
FUENTES = OUT / "fuentes"
# look serio: altas luces contenidas (ventanal), un poco más de contraste y viñeta leve
GRADE = "curves=all='0/0 0.25/0.22 0.6/0.6 0.85/0.8 1/0.92',eq=saturation=1.04:contrast=1.03,vignette=angle=PI/5"
MIRA = kit.ep("mira", {"cam1": 0.40, "cam2": 0.60})       # dónde queda la cara en el ancho del encuadre (aire hacia el otro)
# la luz cae al atardecer (luz.json, de p2c_luz.py): gamma por plano hacia el brillo del inicio de cada cámara, 85 % y con tope
LUZ = {k: np.array(v) for k, v in json.load(open(W / "luz.json")).items()} if (W / "luz.json").exists() else {}
LUZ_META = kit.ep("luz_meta")


def gamma_luz(cam, f, t):
    v = LUZ.get(f)
    if v is None or not len(v): return 1.0
    y = float(np.median(v[(v[:, 0] >= t - 1.5) & (v[:, 0] <= t + 1.5), 1])) if ((v[:, 0] >= t - 1.5) & (v[:, 0] <= t + 1.5)).any() else float(np.interp(t, v[:, 0], v[:, 1]))
    if abs(y - LUZ_META[cam]) <= 4: return 1.0
    g = np.log(max(y, 20) / 255) / np.log(LUZ_META[cam] / 255)
    return float(np.clip(1 + 0.85 * (g - 1), 0.84, 1.75))


# color de la cara (color.json, de p2d_color.py): balance de blancos + exposición por plano contra la cara de referencia de cada cámara
COLOR = {k: np.array([[np.nan if x is None else x for x in r] for r in v], float)
         for k, v in json.load(open(W / "color.json")).items()} if (W / "color.json").exists() else {}
REF_ARCH = {c: fs[0] for c, fs in kit.ep("camaras").items()}
Y3 = np.array([0.299, 0.587, 0.114])


def _cara_rgb(f, t0, t1):
    v = COLOR.get(f)
    if v is None: return None
    m = (v[:, 0] >= t0) & (v[:, 0] <= t1) & np.isfinite(v[:, 1])
    return np.median(v[m, 1:4], 0) if m.sum() >= 2 else None


REF = {c: _cara_rgb(f, 0, 600) for c, f in REF_ARCH.items()}


_CURVA = {}


def _suave(x, k):
    """mediana móvil de ±k muestras ignorando NaN; huecos rellenados por interpolación."""
    n = len(x); out = np.full(n, np.nan)
    for i in range(n):
        w = x[max(0, i - k): i + k + 1]; w = w[np.isfinite(w)]
        if len(w) >= 3: out[i] = np.median(w)
    ok = np.isfinite(out)
    if ok.sum() < 2: return None
    out = np.interp(np.arange(n), np.flatnonzero(ok), out[ok])
    m = 4; return np.convolve(np.pad(out, m, mode="edge"), np.ones(2 * m + 1) / (2 * m + 1), "valid")   # ± 2 s más, sin escalones


def curva(cam, f):
    """v2: corrección CONTINUA por archivo (cada 0.5 s): dos planos seguidos de la misma toma reciben la misma corrección en el corte."""
    if (cam, f) in _CURVA: return _CURVA[(cam, f)]
    v, ref = COLOR.get(f), REF.get(cam); r = None
    if v is not None and ref is not None:
        ch = [_suave(v[:, 1 + c], 12) for c in range(3)]            # ± 6 s
        if all(c is not None for c in ch):
            rgb = np.stack(ch, 1); yr = float(ref @ Y3); yc = rgb @ Y3
            lento = np.stack([_suave(v[:, 1 + c], 40) for c in range(3)], 1)   # el tono cambia despacio: ± 20 s
            wb = (ref / yr) / (lento / (lento @ Y3)[:, None]); wb = 1 + 0.8 * (wb - 1); wb = wb / (wb @ Y3)[:, None]; wb = np.clip(wb, 0.8, 1.25)
            qw = np.clip((yc - 195) / 15, 0, 1)                         # sol en la cara (gradual): más gamma, contraste y un toque cálido
            wb = wb * (1 + qw[:, None] * np.array([0.03, -0.015, -0.05]))
            y = (rgb * wb) @ Y3
            g = np.log(np.maximum(y, 25) / 255) / np.log(yr / 255)
            g = np.clip(1 + 0.85 * (g - 1), 0.8 - 0.12 * qw, 1.8)
            r = (v[:, 0], wb, g, 1 + 0.08 * qw)
    _CURVA[(cam, f)] = r
    return r


def ajuste(cam, f, t0, d):
    """(filtro ffmpeg, clave): balance de blancos (constante en el plano) + gamma que sigue la curva continua del archivo."""
    c = curva(cam, f)
    if c is None:                                       # sin cara: solo brillo del cuadro (luz.json)
        g0, g1 = round(gamma_luz(cam, f, t0), 2), round(gamma_luz(cam, f, t0 + d), 2)
        if max(abs(g0 - 1), abs(g1 - 1)) <= 0.02: return "", ""
        return f"eq=gamma='{g0}+{g1 - g0:.3f}*min(t/{d:.3f},1)':eval=frame", f"_luz{g0}_{g1}"
    ts, wbs, gs, cs = c
    wb = np.array([np.interp(t0 + d / 2, ts, wbs[:, k]) for k in range(3)]).round(3)
    g0, g1 = round(float(np.interp(t0, ts, gs)), 3), round(float(np.interp(t0 + d, ts, gs)), 3)
    con = round(float(np.interp(t0 + d / 2, ts, cs)), 3)
    fil = [f"colorchannelmixer=rr={wb[0]}:gg={wb[1]}:bb={wb[2]}",
           f"eq=gamma='{g0}+{g1 - g0:.4f}*min(t/{d:.3f},1)':contrast={con}:saturation={con}:eval=frame"]
    return ",".join(fil), f"_cv{wb[0]}_{wb[1]}_{wb[2]}_{g0}_{g1}_{con}"


def run(cmd):
    subprocess.run(cmd, check=True)


_CARAS = {}


def cara(cam, f, t0=None, d=None):
    """posición de la cara (cx, cy, w, h normalizados): mediana dentro del plano; si no hay, la del archivo."""
    if f not in _CARAS: _CARAS[f] = json.load(open(W / "caras" / f"{Path(f).stem}.json"))
    c = _CARAS[f]
    if t0 is not None:
        cx0 = (c["caja"][0] + c["caja"][2] / 2) / 1920              # solo la cara principal de esa cámara
        qs = [q[1:5] for q in c["vision"] if q[1] is not None and abs(q[1] - cx0) < 0.2 and t0 <= q[0] <= t0 + d]
        if len(qs) >= 3: return [float(v) for v in np.median(np.array(qs), 0)]
    return c["cara"]


BR = OUT / "broll"; BR.mkdir(exist_ok=True)


def bajar_broll():
    import urllib.request, urllib.parse
    key = kit.pexels_key()
    cred = json.load(open(BR / "creditos.json")) if (BR / "creditos.json").exists() else {}
    usados = {v["id"] for v in cred.values()}
    for p in P["planos"]:
        if p["tipo"] != "broll" or (BR / f"{p['bq']:02d}.mp4").exists(): continue
        q = urllib.parse.urlencode({"query": p["q"], "orientation": "landscape", "size": "medium", "per_page": 20})
        r = json.load(urllib.request.urlopen(urllib.request.Request(f"https://api.pexels.com/videos/search?{q}",
                                                                    headers={"Authorization": key, "User-Agent": "editor-video-largo"})))
        for v in r.get("videos", []):
            if v["id"] in usados or v["duration"] < p["n"] / FPS + 1.5: continue
            fs = sorted([f for f in v["video_files"] if f.get("width") and 1920 <= f["width"] <= 2560 and f["height"] < f["width"]],
                        key=lambda f: f["width"])
            if not fs: continue
            (BR / f"{p['bq']:02d}.mp4").write_bytes(urllib.request.urlopen(urllib.request.Request(fs[0]["link"], headers={"User-Agent": "Mozilla/5.0"})).read())
            usados.add(v["id"]); cred[str(p["bq"])] = {"q": p["q"], "id": v["id"], "autor": v["user"]["name"], "url": v["url"]}
            print("B-roll", p["bq"], p["q"], "→", v["id"]); break
        else: print("B-roll SIN RESULTADO:", p["q"])
    json.dump(cred, open(BR / "creditos.json", "w"), ensure_ascii=False, indent=1)


BR_INICIO = {8: 3.0}


def pieza_broll(p):
    n = p["n"]; d = n / FPS
    ss = BR_INICIO.get(p["bq"], 0.5)                  # algunos clips arrancan con un paneo sobre pared vacía
    f = PZ / (f"b{p['bq']:02d}_{p['o']}_{n}" + (f"_s{ss}" if ss != 0.5 else "") + ".mp4")
    if f.exists(): return f
    Z = f"(1+0.05*t/{d:.3f})"
    vf = (f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
          f"scale=w='trunc(1920*{Z}/2)*2':h='trunc(1080*{Z}/2)*2':eval=frame:flags=lanczos,crop=1920:1080:x='(iw-1920)/2':y='(ih-1080)/2',"
          f"eq=saturation=0.86:contrast=1.04:brightness=-0.02")
    tmp = f.with_suffix(".tmp.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-i", str(BR / f"{p['bq']:02d}.mp4"), "-an",
         "-vf", f"{vf},fps={FPS_S},format=yuv420p", "-frames:v", str(n), *ENC, str(tmp)])
    tmp.rename(f)
    return f


def pieza(i):
    p = P["planos"][i]; n = p["n"]
    if p["tipo"] == "broll": return pieza_broll(p)
    z0, z1 = p["z0"], p["z1"]; zmin = min(z0, z1)
    cx, cy, _, _ = cara(p["cam"], p["f"], p["t_cam"], n / FPS)
    cw, ch = int(1920 / zmin) // 2 * 2, int(1080 / zmin) // 2 * 2
    x0 = int(np.clip(cx * 1920 - MIRA[p["cam"]] * cw, 0, 1920 - cw)) // 2 * 2
    y0 = int(np.clip(cy * 1080 - 0.40 * ch, 0, 1080 - ch)) // 2 * 2
    px = float(np.clip((cx * 1920 - x0) / cw, 0, 1)); py = float(np.clip((cy * 1080 - y0) / ch, 0, 1))
    d = n / FPS
    fil_cc, k_cc = ajuste(p["cam"], p["f"], p["t_cam"], d)
    clave = f"g2_{i:04d}_{p['cam']}_{p['f']}_{p['t_cam']:.4f}_{n}_{z0:.3f}_{z1:.3f}_{x0}_{y0}" + k_cc
    f = PZ / f"p{hashlib.md5(clave.encode()).hexdigest()[:10]}.mp4"
    if f.exists(): return f
    if z0 == z1:
        vf = f"crop={cw}:{ch}:{x0}:{y0},scale=1920:1080:flags=lanczos" + (",unsharp=5:5:0.5" if zmin > 1 else "")
    else:
        k = max(z0, z1) / zmin
        Z = f"(1+{k - 1:.4f}*t/{d:.3f})" if z1 > z0 else f"({k:.4f}-{k - 1:.4f}*t/{d:.3f})"
        vf = (f"crop={cw}:{ch}:{x0}:{y0},scale=w='trunc(1920*{Z}/2)*2':h='trunc(1080*{Z}/2)*2':eval=frame:flags=lanczos,"
              f"crop=1920:1080:x='(iw-1920)*{px:.3f}':y='(ih-1080)*{py:.3f}',unsharp=5:5:0.45")
    if fil_cc: vf += "," + fil_cc
    vf += "," + GRADE
    tmp = f.with_suffix(".tmp.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['t_cam']:.4f}", "-i", str(CR / p["cam"] / p["f"]), "-an",
         "-vf", f"{vf},fps={FPS_S},format=yuv420p", "-frames:v", str(n), *ENC, str(tmp)])
    tmp.rename(f)
    return f


def negro(n, nombre):
    f = PZ / f"{nombre}_{n}.mp4"
    if not f.exists():
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x201E1F:s=1920x1080:r={FPS_S}", "-frames:v", str(n), *ENC, str(f)])
    return f


def piezas():
    planos = P["planos"]
    falta = [k for k, p in enumerate(planos) if "f" not in p and p["tipo"] != "broll"]
    bajar_broll()
    assert not falta, f"{len(falta)} planos sin archivo de cámara (¿sync?)"
    with ThreadPoolExecutor(5) as ex:
        fs = list(ex.map(pieza, range(len(planos))))
    b = P["bloques"]
    orden, o = [], 0
    for k, p in enumerate(planos):
        if p["o"] > o: orden.append(negro(p["o"] - o, "hueco"))
        orden.append(fs[k]); o = p["o"] + p["n"]
    if P["total"] > o: orden.append(negro(P["total"] - o, "final"))
    (OUT / "lista.txt").write_text("".join(f"file '{f}'\n" for f in orden))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "lista.txt"), "-c", "copy", str(OUT / "base.mp4")])
    print("base.mp4 listo ·", len(planos), "planos")


# ───────────────────────────── audio ─────────────────────────────
def leer_wav(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def audio():
    x = leer_wav(W / "mezcla48.wav")
    tot = int(round(P["total"] / FPS * SR)) + SR
    y = np.zeros(tot, np.float32)
    for s in P["segs"]:
        i0 = int(round(s["o"] / FPS * SR)); n = int(round((s["o"] + s["n"]) / FPS * SR)) - i0
        a = int(round(s["a"] * SR)); seg = x[a:a + n].copy()
        fd = int((0.04 if s["tipo"] == "cold" else 0.008) * SR)
        r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fd))
        seg[:fd] *= r; seg[-fd:] *= r[::-1]
        y[i0:i0 + len(seg)] += seg
    with wave.open(str(OUT / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    b = {k: (v[0] / FPS, v[1] / FPS) for k, v in P["bloques"].items()}
    T = P["total"] / FPS
    ci, cf = b["intro"]; ef = b["ep"][0]; fi = b["final"][0]
    # música: cama baja en el avance → entra fuerte en el intro → se va bajo la voz; y otra vez en la pantalla final
    m1 = ef + 3.0
    # v2: la cama del avance sigue hasta que el invitado termina su última frase; el intro entra justo después (no encima de su voz)
    # y la música baja ANTES de que el anfitrión empiece a hablar.
    i0 = ci; bj = ef - 1.4 - i0
    mus = [
        (0.0, ci + 0.4, f"volume=0.10,afade=t=in:d=2,afade=t=out:st={ci - 0.05:.3f}:d=0.4", 0.0),
        (i0, m1, f"volume='if(lt(t,{bj:.3f}),0.55,0.55-0.49*min(1,(t-{bj:.3f})/1.2))':eval=frame,"
                 f"afade=t=in:d=0.25,afade=t=out:st={m1 - i0 - 0.6:.3f}:d=0.6", 25.2),
        (fi - 1.0, T, f"volume=0.45,afade=t=in:d=1.5,afade=t=out:st={T - fi - 2.5:.3f}:d=2.5", 20.0),
    ]
    sfx = [("impact-bass-1.mp3", ci + 0.05, 0.35), ("whoosh-cinematic.mp3", ef - 0.25, 0.40)]
    for g in P["graficos"]:
        if g["comp"] == "Capitulo": sfx.append(("whoosh-short.mp3", g["o"] / FPS, 0.14))
    ins = ["-i", str(OUT / "voz.wav")]
    fc = ["[0:a]aformat=channel_layouts=stereo[voz]"]
    k = 1
    for a, bb, filtro, desde in mus:
        ins += ["-ss", f"{desde:.2f}", "-i", str(MUSICA)]
        fc.append(f"[{k}:a]aformat=sample_rates={SR}:channel_layouts=stereo,atrim=duration={bb - a:.3f},asetpts=PTS-STARTPTS,"
                  f"{filtro},adelay={int(a * 1000)}:all=1[m{k}]"); k += 1
    for nombre, t, vol in sfx:
        ins += ["-i", str(SFX / nombre)]
        fc.append(f"[{k}:a]aformat=sample_rates={SR}:channel_layouts=stereo,volume={vol},adelay={int(max(t, 0) * 1000)}:all=1[m{k}]"); k += 1
    fc.append("[voz]" + "".join(f"[m{j}]" for j in range(1, k)) + f"amix=inputs={k}:normalize=0:duration=first[mx]")
    fcp = OUT / "audio_fc.txt"
    fcp.write_text(";".join(fc + ["[mx]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[a]"]))
    r = subprocess.run(["ffmpeg", "-hide_banner", "-y", *ins, "-/filter_complex", str(fcp), "-map", "[a]", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = r.stderr[r.stderr.rfind("{"): r.stderr.rfind("}") + 1]; m = json.loads(js)
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample={SR}")
    fcp.write_text(";".join(fc + [f"[mx]{ln}[a]"]))
    run(["ffmpeg", "-v", "error", "-y", *ins, "-/filter_complex", str(fcp), "-map", "[a]", "-t", f"{T:.4f}",
         "-c:a", "pcm_s24le", str(OUT / "audio.wav")])
    print("audio.wav listo · medido", m["input_i"], "LUFS →", m["output_i"])


# ───────────────────────────── gráficos ─────────────────────────────
def lista_graficos():
    (GR / "out").mkdir(exist_ok=True)
    gs = []
    for g in P["graficos"]:
        props = dict(g["props"], duracion=round(g["n"] / FPS, 3))
        h = hashlib.md5(json.dumps([g["comp"], props], sort_keys=True).encode()).hexdigest()[:8]
        gs.append({"comp": g["comp"], "props": props, "out": str(GR / "out" / f"{g['comp']}_{h}.mov"), "o": g["o"], "n": g["n"]})
    gs.append({"comp": "Mosca", "props": {}, "out": str(GR / "out" / "mosca.png")})
    return gs


def graficos():
    gs = lista_graficos()
    (GR / "lista.json").write_text(json.dumps(gs, ensure_ascii=False))
    subprocess.run(["node", "render.mjs", "lista.json"], cwd=GR, check=True)


def final(base=None, salida=None, t_ini=0.0, t_fin=None):
    """compone base + gráficos + logo. Con t_ini/t_fin arma solo ese tramo (avance)."""
    base = base or OUT / "base.mp4"; salida = salida or OUT / "video.mp4"
    gs = lista_graficos(); mosca = gs.pop()
    b = {k: (v[0] / FPS, v[1] / FPS) for k, v in P["bloques"].items()}
    T = t_fin or P["total"] / FPS
    D = T - t_ini
    ins = ["-i", str(base), "-ss", f"{t_ini:.4f}", "-t", f"{D:.4f}", "-i", str(OUT / "audio.wav"), "-loop", "1", "-i", mosca["out"]]
    fc, prev, k = [], "[0:v]", 3
    sin_logo = [(b["intro"][0] - 0.05, b["ep"][0] + 0.3), (b["final"][0] - 0.5, P["total"] / FPS + 1)]
    sin_logo += [(g["o"] / FPS, (g["o"] + g["n"]) / FPS) for g in gs if g["comp"] == "Capitulo" and g["props"].get("lado") == "der"]
    en = "+".join(f"between(t,{a - t_ini:.3f},{c - t_ini:.3f})" for a, c in sin_logo)
    fc.append(f"[2:v]format=rgba,trim=duration={D:.3f}[lg]")
    fc.append(f"{prev}[lg]overlay=0:0:enable='not({en})'[v0]"); prev = "[v0]"
    orden = sorted(gs, key=lambda g: g["comp"] in ("Intro", "Final"))
    for j, g in enumerate(orden):
        t0 = g["o"] / FPS - t_ini
        if t0 < -0.01 or t0 > D: continue
        ins += ["-i", g["out"]]
        fc.append(f"[{k}:v]format=yuva420p,setpts=PTS-STARTPTS+{t0:.4f}/TB[g{j}]")
        fc.append(f"{prev}[g{j}]overlay=0:0:eof_action=pass:enable='between(t,{t0:.3f},{t0 + g['n'] / FPS + 0.2:.3f})'[v{j + 1}]")
        prev = f"[v{j + 1}]"; k += 1
    if (OUT / "broll_subs.ass").exists() and t_ini == 0:  # subtítulos solo en el tramo de B-roll
        fc.append(f"{prev}subtitles=filename={OUT / 'broll_subs.ass'}:fontsdir={FUENTES}[vs]"); prev = "[vs]"
    fc.append(f"{prev}format=yuv420p[vout]")
    fcp = OUT / "video_fc.txt"; fcp.write_text(";\n".join(fc))
    run(["ffmpeg", "-v", "error", "-stats", "-y", *ins, "-/filter_complex", str(fcp), "-map", "[vout]", "-map", "1:a",
         "-c:v", "h264_videotoolbox", "-b:v", "22M", "-maxrate", "30M", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", FPS_S,
         "-af", "alimiter=limit=0.79:attack=2:release=50:level=0", "-c:a", "aac", "-b:a", "320k", "-t", f"{D:.4f}", "-movflags", "+faststart", str(salida)])
    print(salida.name, "listo")


def avance(minutos):
    """intro + los primeros minutos del episodio, con lo que ya está descargado."""
    i0 = P["bloques"]["intro"][0]; lim = P["bloques"]["ep"][0] + int(minutos * 60 * FPS)
    sub = [k for k, p in enumerate(P["planos"]) if p["o"] >= P["bloques"]["ep"][0] and p["o"] + p["n"] <= lim]
    assert all("f" in P["planos"][k] for k in sub), "faltan planos sin archivo en el tramo del avance"
    with ThreadPoolExecutor(5) as ex:
        fs = list(ex.map(pieza, sub))
    fin = P["planos"][sub[-1]]["o"] + P["planos"][sub[-1]]["n"]
    orden = [negro(P["bloques"]["ep"][0] - i0, "hueco")] + fs
    (OUT / "lista_avance.txt").write_text("".join(f"file '{f}'\n" for f in orden))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "lista_avance.txt"), "-c", "copy",
         str(OUT / "base_avance.mp4")])
    final(OUT / "base_avance.mp4", OUT / "avance.mp4", i0 / FPS, fin / FPS)


if __name__ == "__main__":
    paso = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if paso in ("piezas", "todo"): piezas()
    if paso in ("audio", "todo"): audio()
    if paso in ("graficos", "todo"): graficos()
    if paso in ("final", "todo"): final()
    if paso == "avance": avance(float(sys.argv[2]))
