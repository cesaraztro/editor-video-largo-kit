"""Arma el episodio de YouTube (16:9) a partir de la cámara (episodio.json → camara) + el micrófono limpio y la lista de cortes edl.json.

Uso:  python armar.py sync      → calcula el desfase cámara/micrófono (sync.json)
      python armar.py render    → corta, junta, pone audio limpio y textos → episodio.mp4
"""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

W = Path(__file__).parent
D = W.parent
CAM = D / kit.ep("camara")
MIC = W / kit.ep("microfono", "mic48_DeepFilterNet3.wav")
FUENTES = kit.FUENTES
NAVY, ORO = kit.color("panel"), kit.color("acento")   # config.json → marca.colores


def leer(p, sr_obj=None):
    w = wave.open(str(p)); sr = w.getframerate(); n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if w.getnchannels() > 1:
        x = x.reshape(-1, w.getnchannels()).mean(1)
    return x, sr


def sync():
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(CAM), "-vn", "-ac", "1", "-ar", "16000", str(W / "cam.wav")], check=True)
    cam, _ = leer(W / "cam.wav"); mic, _ = leer(W / "mic16k.wav")
    env = lambda x: np.abs(x[:len(x) // 160 * 160]).reshape(-1, 160).mean(1)
    a, b = env(cam[:16000 * 240]), env(mic)
    a = (a - a.mean()) / a.std(); b = (b - b.mean()) / b.std()
    c = np.correlate(b, a, mode="full"); k = int(np.argmax(c)) - (len(a) - 1)
    off = k / 100.0          # mic = cam + off
    # afinado a nivel de muestra
    best = (-1, 0)
    for d in range(-200, 201, 2):
        s = int((off * 16000) + d)
        c0 = 16000 * 60
        m = mic[c0 + s:c0 + s + 16000 * 10]; q = cam[c0:c0 + 16000 * 10]
        if len(m) < len(q):
            continue
        v = float(np.dot(q, m) / (np.linalg.norm(q) * np.linalg.norm(m) + 1e-9))
        if v > best[0]:
            best = (v, s)
    off = best[1] / 16000
    json.dump({"mic_menos_cam": off, "corr": best[0]}, open(W / "sync.json", "w"))
    print(f"mic = cam + {off:.4f} s (corr {best[0]:.3f})")


def piezas():
    x, sr = leer(MIC)
    hop = sr // 100
    db = 20 * np.log10(np.sqrt(np.mean(x[:len(x) // hop * hop].reshape(-1, hop) ** 2, 1)) + 1e-9)
    piso, voz = np.percentile(db, 15), np.percentile(db, 90)
    thr = max(piso + 10, voz - 28)
    nivel = lambda t: db[min(max(int(round(t * 100)), 0), len(db) - 1)]
    out = []
    for k, (cap, s, e, txt) in enumerate(json.load(open(W / "edl.json"))):
        t = s
        while t > s - 0.45 and nivel(t) > thr: t -= 0.01
        s2 = t - 0.06
        t = e
        while t < e + 0.6 and nivel(t) > thr: t += 0.01
        e2 = t + 0.1
        # pausas internas largas → se acortan (corte de salto, con zoom alterno)
        trozo, a, run = [], s2, None
        for i in range(int(s2 * 100), int(e2 * 100)):
            q = db[i] < thr
            if q and run is None: run = i
            if not q and run is not None:
                if (i - run) >= 55:
                    trozo.append((a, run / 100 + 0.14)); a = i / 100 - 0.12
                run = None
        trozo.append((a, e2))
        for j, (a, b) in enumerate(trozo):
            out.append({"cap": cap, "a": round(a, 3), "b": round(b, 3), "txt": txt if j == 0 else "", "item": k})
    return out, thr


def render():
    off = json.load(open(W / "sync.json"))["mic_menos_cam"]
    ps, thr = piezas()
    print(f"{len(ps)} piezas · umbral {thr:.1f} dB · {sum(p['b'] - p['a'] for p in ps) / 60:.2f} min")
    pz = W / "piezas"; pz.mkdir(exist_ok=True)
    caras = [q for q in json.load(open(W / "caras.json"))["cuadros"] if q and q[1] is not None]
    lista, t_out, marcas = [], 0.0, []
    for i, p in enumerate(ps):
        z = 1.10 if i % 2 == 0 else 1.22
        cw, ch = int(1920 / z) // 2 * 2, int(1080 / z) // 2 * 2
        t0, t1 = p["a"] - off, p["b"] - off
        qs = [q for q in caras if t0 <= q[0] <= t1] or [min(caras, key=lambda q: abs(q[0] - t0))]
        fx, fy = float(np.median([q[1] for q in qs])), float(np.median([q[2] for q in qs]))
        cx = min(max(int(fx * 1920 - cw / 2), 0), 1920 - cw)
        cy = min(max(int(fy * 1080 - 0.34 * ch), 0), 1080 - ch)
        dur = p["b"] - p["a"]
        f = pz / f"p{i:03d}.mp4"
        if not f.exists(): subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['a'] - off:.3f}", "-i", str(CAM), "-t", f"{dur:.3f}", "-an",
                        "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale=1920:1080:flags=lanczos,fps=30000/1001,format=yuv420p",
                        "-c:v", "h264_videotoolbox", "-b:v", "16M", str(f)], check=True)
        lista.append(f"file '{f}'")
        if p["txt"] and (i == 0 or ps[i - 1]["cap"] != p["cap"]):
            marcas.append((p["cap"], t_out))
        t_out += dur
    (W / "lista.txt").write_text("\n".join(lista) + "\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(W / "lista.txt"), "-c", "copy", str(W / "video_sin_audio.mp4")], check=True)
    # audio: mismos tramos del micrófono limpio, con microfundidos para que no truene
    fc = ["[0:a]asplit=" + str(len(ps)) + "".join(f"[s{i}]" for i in range(len(ps)))]
    for i, p in enumerate(ps):
        d = p["b"] - p["a"]
        fc.append(f"[s{i}]atrim={p['a']:.3f}:{p['b']:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={max(d - 0.015, 0):.3f}:d=0.015[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(ps))) + f"concat=n={len(ps)}:v=0:a=1,highpass=f=80,"
              "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150:makeup=1,deesser=i=0.3,"
              "loudnorm=I=-14:TP=-1.5:LRA=9[aout]")
    (W / "audio_fc.txt").write_text(";".join(fc))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(MIC), "-/filter_complex", str(W / "audio_fc.txt"), "-map", "[aout]",
                    "-ar", "48000", "-c:a", "pcm_s16le", str(W / "audio.wav")], check=True)
    # textos de marca
    titulos = {"intro": (kit.MARCA["nombre"], kit.MARCA["rol"]),
               "leccion1": ("LECCIÓN 1", "Una plataforma ordena todo tu negocio"),
               "leccion2": ("LECCIÓN 2", "Un agente trabaja con tu información"),
               "guia": ("GUÍA GRATIS", "Link en la descripción"),
               "leccion3": ("LECCIÓN 3", "La IA no reemplaza a tu equipo, lo potencia"),
               "cierre": ("RECAPITULANDO", "Plataforma · Agente · Equipo"),
               "cta": ("CONSULTORÍA 1 A 1", "Agenda en el link de la descripción")}
    f6, f4 = FUENTES / "poppins-800.ttf", FUENTES / "poppins-600.ttf"
    vf = []
    for cap, t0 in marcas:
        if cap not in titulos:
            continue
        t1 = t0 + 4.5
        a, b = (v.replace(",", r"\,").replace(":", r"\:").replace("'", "") for v in titulos[cap])
        en = f"between(t,{t0 + 0.3:.2f},{t1:.2f})"
        vf.append(f"drawbox=x=80:y=80:w=700:h=140:color={NAVY}@0.88:t=fill:enable='{en}'")
        vf.append(f"drawbox=x=80:y=80:w=10:h=140:color={ORO}:t=fill:enable='{en}'")
        vf.append(f"drawtext=fontfile='{f6}':text='{a}':fontcolor={ORO}:fontsize=40:x=118:y=98:enable='{en}'")
        vf.append(f"drawtext=fontfile='{f4}':text='{b}':fontcolor=white:fontsize=29:x=118:y=160:enable='{en}'")
    (W / "video_fc.txt").write_text(",".join(vf) if vf else "null")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(W / "video_sin_audio.mp4"), "-i", str(W / "audio.wav"),
                    "-/filter:v", str(W / "video_fc.txt"), "-map", "0:v", "-map", "1:a", "-c:v", "h264_videotoolbox", "-b:v", "14M",
                    "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(D / "episodio.mp4")], check=True)
    json.dump({"piezas": ps, "marcas": marcas}, open(W / "timeline.json", "w"), ensure_ascii=False, indent=1)
    print("LISTO", D / "episodio.mp4", f"{t_out / 60:.2f} min")


if __name__ == "__main__":
    {"sync": sync, "render": render}[sys.argv[1]]()
