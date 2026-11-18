#!/usr/bin/env bash
# Instalador del Editor de Video Largo (macOS, Apple Silicon).
#   ./instalar.sh                 instala todo y copia la skill a ~/.claude/skills/editor-video-largo/
#   ./instalar.sh --sin-skill     instala todo menos la skill de Claude Code
#   ./instalar.sh --limpiar-voz   además instala DeepFilterNet (quita ruido del micrófono; pesa ~2 GB)
#   ./instalar.sh --ayuda
# Necesita el Editor de Reels ya instalado (usa su motor: silueta, caras, fuentes y efectos de sonido).
# Es seguro correrlo varias veces: solo hace lo que falta.
set -u
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIN_SKILL=0; DFN=0
for a in "$@"; do
  case "$a" in
    --sin-skill) SIN_SKILL=1 ;;
    --limpiar-voz) DFN=1 ;;
    -h|--ayuda|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción desconocida: $a (usa --ayuda)"; exit 2 ;;
  esac
done
if [ -t 1 ]; then V=$'\033[32m'; A=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'; B=$'\033[1m'; else V=""; A=""; R=""; N=""; B=""; fi
ok()    { echo "${V}  ✓${N} $*"; }
aviso() { echo "${A}  !${N} $*"; }
falla() { echo "${R}  ✗ $*${N}"; }
paso()  { echo; echo "${B}$*${N}"; }
LOG="$KIT/.instalar.log"; : > "$LOG"

echo "${B}Editor de Video Largo · instalación${N}"
echo "Carpeta del kit: $KIT"

paso "1/5 Requisitos"
[ "$(uname -s)" = "Darwin" ] || { falla "Necesitas macOS."; exit 1; }
ok "macOS $(sw_vers -productVersion 2>/dev/null)"
[ "$(uname -m)" = "arm64" ] || aviso "Tu Mac no es Apple Silicon: Whisper (mlx) no funcionará."
FALTA=0
for c in ffmpeg node npm uv python3; do
  if command -v "$c" >/dev/null 2>&1; then ok "$c"; else falla "Falta $c (brew install ${c/python3/python})"; FALTA=1; fi
done
[ "$FALTA" = 0 ] || { falla "Instala lo que falta y vuelve a correr ./instalar.sh"; exit 1; }

paso "2/5 Motor del Editor de Reels"
MOTOR="$(python3 -c 'import json,os,sys; k=sys.argv[1]; m=os.path.expanduser(json.load(open(k+"/config.json"))["rutas"]["motor"]); print(m if os.path.isabs(m) else os.path.normpath(os.path.join(k,m)))' "$KIT")"
echo "  config.json → rutas.motor = $MOTOR"
OKM=1
for f in bin/matte bin/caras mirada.py modelos/face_landmarker.task fuentes/poppins-800.ttf; do
  if [ -e "$MOTOR/$f" ]; then ok "$f"; else falla "No encuentro $MOTOR/$f"; OKM=0; fi
done
if [ "$OKM" = 0 ]; then
  falla "Instala primero el Editor de Reels (./instalar.sh en su carpeta) o corrige rutas.motor en config.json."
  exit 1
fi

paso "3/5 Entorno de Python (.venv)"
if [ ! -x "$KIT/.venv/bin/python" ]; then
  uv venv --python 3.12 "$KIT/.venv" >>"$LOG" 2>&1 || uv venv "$KIT/.venv" >>"$LOG" 2>&1
fi
if uv pip install --python "$KIT/.venv/bin/python" -r "$KIT/requirements.txt" >>"$LOG" 2>&1; then
  ok "mediapipe, numpy, pillow, opencv y mlx-whisper"
else
  falla "No se pudo instalar el entorno. Mira $LOG"; exit 1
fi
M="$KIT/modelos/efficientdet_lite2.tflite"
if [ ! -s "$M" ]; then
  curl -fsSL -o "$M" "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite2/float32/latest/efficientdet_lite2.tflite" \
    && ok "modelo efficientdet_lite2 (detecta el celular en la mano)" || aviso "No se pudo bajar efficientdet_lite2.tflite; celular6.py no funcionará."
else ok "modelo efficientdet_lite2"; fi
if [ "$DFN" = 1 ]; then
  if [ ! -x "$KIT/.dfn/bin/deepFilter" ]; then
    uv venv --python 3.11 "$KIT/.dfn" >>"$LOG" 2>&1 && uv pip install --python "$KIT/.dfn/bin/python" deepfilternet >>"$LOG" 2>&1 \
      && ok "DeepFilterNet en .dfn/" || aviso "No se pudo instalar DeepFilterNet (mira $LOG)."
  else ok "DeepFilterNet"; fi
fi

paso "4/5 Gráficos del podcast (Remotion)"
if (cd "$KIT/plantillas/podcast/graficos" && npm install --silent >>"$LOG" 2>&1); then ok "npm install"; else aviso "npm install falló (mira $LOG)"; fi

paso "5/5 Skill de Claude Code"
if [ "$SIN_SKILL" = 1 ]; then aviso "omitida (--sin-skill)"; else
  DEST="$HOME/.claude/skills/editor-video-largo"; mkdir -p "$DEST"
  sed "s|{{KIT}}|$KIT|g" "$KIT/skill/editor-video-largo/SKILL.md" > "$DEST/SKILL.md"
  ok "skill en $DEST"
fi
[ -f "$KIT/.env" ] || { cp "$KIT/.env.example" "$KIT/.env"; aviso "Creé .env: pon tu PEXELS_API_KEY ahí (gratis en pexels.com/api)."; }

echo; echo "${V}${B}Listo.${N} Cambia tu marca en config.json y crea un episodio con:"
echo "  ./nuevo_episodio.sh podcast ~/Movies/mis-episodios/podcast-01"
