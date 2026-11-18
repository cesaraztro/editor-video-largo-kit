"""Configuración compartida del kit (rutas, marca, hablantes y datos del episodio).

nuevo_episodio.sh copia este archivo a la carpeta trabajo/ de cada episodio y escribe ahí `.kit`
con la ruta del kit, así los scripts encuentran config.json y .env sin rutas fijas.
Los datos del episodio salen de trabajo/episodio.json.
"""
import json, os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
_k = AQUI / ".kit"
KIT = Path(_k.read_text().strip()) if _k.exists() else AQUI.parent
CONFIG = json.load(open(KIT / "config.json", encoding="utf8"))


def _ruta(v):
    p = Path(os.path.expanduser(v))
    return p if p.is_absolute() else (KIT / p).resolve()


R = CONFIG["rutas"]
MOTOR = _ruta(R["motor"])                    # _motor del editor-reels-kit: bin/matte, bin/caras, modelos, fuentes, .venv
FUENTES = MOTOR / "fuentes"
MODELOS = KIT / "modelos"                    # efficientdet_lite2.tflite (lo baja instalar.sh)
SFX = _ruta(R["sfx"])                        # tus efectos de sonido (whoosh-short.mp3, impact-bass-1.mp3, ...)
MUSICA = _ruta(R["musica"])                  # tus pistas con licencia
MARCA = CONFIG["marca"]
HABLANTES = CONFIG.get("hablantes", ["Anfitrión", "Invitado"])   # 0 = anfitrión, 1 = invitado
CORRECCIONES = CONFIG.get("correcciones", {})                     # cómo escribe Whisper → cómo debe quedar


def pexels_key():
    k = os.environ.get("PEXELS_API_KEY")
    if k: return k
    env = KIT / ".env"
    if env.exists():
        for l in env.read_text().splitlines():
            if l.startswith("PEXELS_API_KEY="): return l.split("=", 1)[1].strip()
    raise SystemExit("Falta PEXELS_API_KEY: ponla en el .env del kit (ver .env.example).")


_ep = AQUI / "episodio.json"
EP = json.load(open(_ep, encoding="utf8")) if _ep.exists() else {}


def ep(clave, defecto=None):
    """Dato del episodio (trabajo/episodio.json). Si falta y no hay valor por defecto, avisa."""
    if clave in EP: return EP[clave]
    if defecto is not None: return defecto
    raise SystemExit(f"Falta \"{clave}\" en episodio.json (o copia el ejemplo de ejemplos/).")


def espaciado(txt):
    return " ".join(txt.upper())


def corregir(palabra):
    for mal, bien in CORRECCIONES.items():
        palabra = palabra.replace(mal, bien)
    return palabra


def color(nombre, formato="ff"):
    """Color de config.json → marca.colores. formato "ff" → "0xRRGGBB" (ffmpeg) · "rgb" → (r, g, b) (PIL)."""
    h = MARCA.get("colores", {}).get(nombre, {"panel": "#0E1A33", "acento": "#D9B45A"}.get(nombre, "#FFFFFF")).lstrip("#")
    return "0x" + h.upper() if formato == "ff" else tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
