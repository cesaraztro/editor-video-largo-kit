# Editor de Video Largo

Edita videos largos horizontales (16:9) para YouTube con Claude Code. Es el hermano del **Editor de Reels** y usa su motor.

## Qué hace

**Episodio a cámara** (una cámara + micrófono aparte):
- **Cortes:** caen en el silencio real y quitan tropiezos y repeticiones.
- **Celular:** detecta cuando miras el celular para leer el guion y lo tapa con B-roll. Revisa cada arranque cuadro por cuadro.
- **Imagen:** la cámara se mueve sola, con golpes de zoom en tus palabras clave y palabras grandes **detrás** de ti (con tu silueta). Nada a pantalla completa tapa tu cara: las tarjetas, el B-roll y los datos entran en un panel lateral.
- **Música:** una pista por capítulo, que baja sola cuando hablas.
- **Acabado:** velocidad 1.10×, volumen −14 LUFS y revisión final automática.

**Podcast multicámara con invitado:**
- **Sincronía:** sincroniza todas las cámaras con los micrófonos.
- **Quién habla:** lo sabe por la voz y por el movimiento de la boca, y **la cámara siempre es la de quien habla**.
- **Planos:** los dos en cuadro la mayor parte del tiempo, con un zoom lento hacia quien habla.
- **Imagen:** igualación de luz y color por cámara durante todo el episodio.
- **Estructura:** resumen al inicio, intro de marca, rótulos con nombres, frases destacadas, capítulos, llamados a la acción y pantalla final, todo con gráficos de Remotion.
- **Entrega:** subtítulos `.srt`, capítulos de YouTube, borrador del copy e ideas de miniatura con los dos sonriendo.

## Requisitos

- Mac con Apple Silicon (M1 o más nuevo).
- **Editor de Reels instalado.** Este kit usa su motor (`_motor`): silueta con Apple Vision, caras, fuentes y efectos de sonido. Por defecto lo busca en la carpeta de al lado (`../editor-reels-kit`).
- `ffmpeg`, `node`, `uv` y `python3`. Instálalos con: `brew install ffmpeg node uv python`.
- Una key gratuita de Pexels para el B-roll.
- Claude Code.

## Instalación

```bash
cd editor-video-largo-kit
./instalar.sh                 # agrega --limpiar-voz para instalar DeepFilterNet (quita el ruido del micrófono)
```

El instalador:
- revisa los requisitos y el motor del Editor de Reels;
- crea el entorno de Python (`.venv`) y baja un modelo;
- instala los gráficos y copia la skill a `~/.claude/skills/editor-video-largo/`.

Pon tu `PEXELS_API_KEY` en `.env`.

## Configura tu marca

Edita `config.json`:
- `marca`: tu nombre, cargo, empresa, web, comunidad, CTA, texto de cierre, etiquetas de la pantalla final y colores del panel y del acento.
- `rutas`: dónde está el motor del Editor de Reels, los efectos de sonido y tu música con licencia.
- `hablantes`: los nombres para los reportes del podcast.
- `correcciones`: nombres que Whisper escribe mal, por ejemplo `{"Jose": "José"}`.

Para los gráficos del podcast, cambia también:
- el logo: `plantillas/podcast/graficos/src/logo.svg`;
- los colores y la fuente: `plantillas/podcast/graficos/src/paleta.ts`.

Para el episodio a cámara, pon tu logo en blanco (PNG) en `trabajo/marca/logo_blanco.png` de cada episodio.

## Cómo usarlo con Claude Code

1. Crea la carpeta del episodio **fuera de iCloud o Dropbox**, porque los archivos intermedios pesan mucho:
   ```bash
   ./nuevo_episodio.sh podcast ~/Movies/mis-episodios/podcast-01
   ./nuevo_episodio.sh episodio ~/Movies/mis-episodios/episodio-01
   ```
2. Copia tus archivos:
   - **Podcast:** en `crudos/` van el audio de los micrófonos y los archivos de cada cámara.
   - **Episodio:** la cámara va en la carpeta del episodio; el micrófono, en `trabajo/`.
3. Llena `trabajo/episodio.json`. Los ejemplos de `ejemplos/` explican cada campo.
4. Abre Claude Code en esa carpeta y dile: *"edita el podcast"* o *"edita el episodio"*. La skill sigue el proceso paso a paso, te muestra las hojas de revisión y te entrega el video, los subtítulos y el copy.

Nada se publica solo: tú revisas y subes a YouTube.

## Consejos de grabación

- **Si lees un guion,** después de cada frase levanta la vista, haz una pausa de un segundo mirando a la cámara y luego habla. Los cortes quedan limpios y no hace falta tapar con B-roll.
- **En el podcast,** cada persona con su micrófono y su cámara, y la cámara de cada quien encuadrada para que se vea también al otro (plano abierto).

## Estructura

```
config.json           tu marca y rutas
.env                  tu PEXELS_API_KEY (no se sube a ningún lado)
instalar.sh           instalador
nuevo_episodio.sh     crea la carpeta de un episodio desde la plantilla
comun/kit.py          lee config.json y episodio.json (se copia a cada episodio)
plantillas/episodio/  scripts del episodio a cámara (+ qa7/ revisión final)
plantillas/podcast/   scripts del podcast (trabajo/) y gráficos Remotion (graficos/)
ejemplos/             episodio.json, guion.json, edl.json, quitar.json y covers.json de ejemplo
skill/                la skill de Claude Code
```

## Licencias de terceros

El kit usa Remotion, ffmpeg, Whisper (mlx), MediaPipe, DeepFilterNet, Pexels y las fuentes del Editor de Reels. Cada uno tiene su propia licencia. Remotion exige una licencia de empresa a partir de 4 empleados. Usa solo música con licencia.

## Créditos

Creado por César Holguín · AztroTech. Ver `LICENSE`.
