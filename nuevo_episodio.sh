#!/usr/bin/env bash
# Crea la carpeta de un episodio nuevo a partir de la plantilla.
#   ./nuevo_episodio.sh episodio <carpeta>   episodio a cámara (una cámara + micrófono)
#   ./nuevo_episodio.sh podcast  <carpeta>   podcast multicámara con invitado
# Ejemplo: ./nuevo_episodio.sh podcast ~/Movies/mis-episodios/podcast-03
set -euo pipefail
KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIPO="${1:-}"; DEST="${2:-}"
if [ -z "$TIPO" ] || [ -z "$DEST" ]; then sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; exit 2; fi
[ -e "$DEST" ] && { echo "Ya existe $DEST; elige otra carpeta."; exit 1; }
case "$TIPO" in
  episodio)
    mkdir -p "$DEST/trabajo"
    cp -R "$KIT/plantillas/episodio/." "$DEST/trabajo/"
    cp "$KIT/ejemplos/episodio/"*.json "$DEST/trabajo/"
    T="$DEST/trabajo" ;;
  podcast)
    mkdir -p "$DEST"
    cp -R "$KIT/plantillas/podcast/." "$DEST/"
    mkdir -p "$DEST/crudos" "$DEST/render"
    cp "$KIT/ejemplos/podcast/"*.json "$DEST/trabajo/"
    if [ -d "$KIT/plantillas/podcast/graficos/node_modules" ]; then :; else
      echo "Instalando los gráficos (npm install, una sola vez por episodio)…"
      (cd "$DEST/graficos" && npm install --silent) || echo "  ! npm install falló; córrelo a mano en $DEST/graficos"
    fi
    T="$DEST/trabajo" ;;
  *) echo "Tipo desconocido: $TIPO (usa episodio o podcast)"; exit 2 ;;
esac
cp "$KIT/comun/kit.py" "$T/"
echo "$KIT" > "$T/.kit"
echo "Listo: $DEST"
echo "1) Pon tus archivos (ver README) y edita $T/episodio.json"
echo "2) Usa el Python del kit: PY=\"$KIT/.venv/bin/python\""
