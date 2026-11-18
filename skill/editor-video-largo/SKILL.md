---
name: editor-video-largo
description: Edita videos largos horizontales 16:9 para YouTube. Cubre dos casos. (1) Episodio a cámara, con una cámara y un micrófono aparte. (2) Podcast multicámara con invitado. Hace cortes en el silencio real, quita repeticiones, pone B-roll cuando miras el celular, tarjetas de marca, música por capítulo, subtítulos, capítulos y copy. Úsala cuando digan "edita el episodio", "el video de YouTube", "edita el podcast", "video largo" o compartan un video horizontal de más de 10 minutos.
---

# Editor de video largo (16:9)

El kit vive en `{{KIT}}`. Su configuración está en `config.json`: marca, rutas al motor del Editor de Reels, hablantes y correcciones de nombres. Cada episodio tiene su `trabajo/episodio.json`.

- **Python:** `PY="{{KIT}}/.venv/bin/python"`. El `python3` del sistema no trae numpy ni mediapipe.
- **Episodio nuevo:** `{{KIT}}/nuevo_episodio.sh episodio|podcast <carpeta>`. Trabaja fuera de iCloud o Dropbox (por ejemplo en `~/Movies/...`), porque los archivos intermedios pesan decenas de GB.
- **Nada se publica** sin el OK de la persona. El copy (`copy.md`) es un borrador.

---

## A · Episodio a cámara (una cámara + micrófono)

Carpeta: `<episodio>/MVI_XXXX.MP4` (cámara) y `<episodio>/trabajo/` (scripts, micrófono limpio y JSON).

1. **Audio.** Limpia el micrófono con DeepFilterNet: `{{KIT}}/.dfn/bin/deepFilter mic48.wav --atten-lim 32 -o trabajo/`. Esto deja `mic48_DeepFilterNet3.wav`. Después saca la versión para Whisper con `ffmpeg -i trabajo/mic48_DeepFilterNet3.wav -ac 1 -ar 16000 trabajo/mic16k.wav` y corre `$PY armar.py sync` para calcular el desfase entre cámara y micrófono (`sync.json`).
2. **Transcripción con palabras.** Corre `uvx --from mlx-whisper mlx_whisper mic16k.wav --model mlx-community/whisper-large-v3-turbo --language es --word-timestamps True --output-format json` y renombra el resultado a `mic16k.json`.
3. **Escribe a mano:**
   - `edl.json`: `[capítulo, inicio, fin, texto]`. Los capítulos son `gancho`, `intro`, `leccion1…3`, `cierre` y `cta`.
   - `quitar.json`: tropiezos, repeticiones y tomas descartadas, cada uno con su motivo.
4. **Mirada y piezas.** Corre `$PY mirada16.py ../MVI_XXXX.MP4 mirada16.json <motor>` y después `$PY plan2.py`. Cada corte cae en el punto más callado entre palabras, ninguna pieza dura menos de 0.7 s y cada una dura un número exacto de cuadros (si no, el audio se adelanta).
5. **Tarjetas y B-roll.** En `covers.json` van las tarjetas (`capitulo`, `frase`, `lista`, `recap`, `final`) y las búsquedas de B-roll en inglés. `$PY pexels16.py` baja el B-roll horizontal (necesita `PEXELS_API_KEY`).
6. **Base y gráficos.** Corre `$PY base5.py`, que arma la cámara con movimiento y golpes de zoom en `palabras_clave`. Luego `<motor>/bin/matte base5.mp4 matte5.mp4` saca la silueta y `$PY graficos4.py` hace los PNG de marca. Antes, pon tu logo en blanco en `trabajo/marca/logo_blanco.png`.
7. **Arranques con la cabeza abajo** (obligatorio, ver abajo). El resultado es `arranques7.json`.
8. **Render.** `$PY render5.py` compone todo:
   - panel lateral (nada a pantalla completa tapa la cara);
   - tarjetas, B-roll en ventana y palabras héroe detrás de la silueta;
   - logo, recorte 1.18× y velocidad 1.10×;
   - música por capítulo que baja sola con la voz.
9. **Verificación final** (abajo). Después mide el volumen (−14 LUFS, pico ≤ −1 dBTP) y entrega.

### Arranques con la cabeza abajo
Si lees el guion en el celular, empiezas a hablar mientras levantas la cabeza. Si el corte cae en la primera sílaba, se ven 0.1–1.0 s mirando hacia abajo.

1. **Revisa las uniones cuadro por cuadro.** `$PY qa7/cortes7.py` arma hojas con 6 cuadros antes y 6 después de cada corte. Revísalas todas a ojo.
2. **Mide el pitch por cuadro.** Corre `$PY mirada6.py base5.mp4 mirada6_base5.json` y luego `$PY qa7/arranques7.py`. Una pieza es arranque si empieza con un pitch ≥ +10° sobre su percentil 30. Termina cuando el pitch se mantiene ≤ +6° durante 3 cuadros.
3. **Tapa cada arranque.** `render5.py` lo cubre con B-roll desde 0.15 s antes del corte hasta **0.35 s después** de que la persona vuelve a mirar a cámara.
4. **Revisa a ojo los picos a mitad de frase** antes de taparlos. Casi siempre son movimientos normales de cabeza.

### Verificación final (sobre el video entregado)
1. Corre `$PY qa7/mirada7.py ../episodio_vN.mp4 qa7/final_vN.json` y luego `$PY qa7/verificar7.py qa7/final_vN.json 10 plan5.json`. Te lista los tramos con la cabeza abajo que siguen a la vista.
2. Corre `$PY qa7/hoja_final7.py …` para armar hojas recortadas a la cara. Revisa cada aviso y cada regreso del B-roll a la cámara.
3. `render5.py` sobrescribe `plan5.json`. Para verificar una versión vieja, usa el plan de esa versión.

**Consejo de grabación:** después de leer cada frase, levanta la vista, haz una pausa de un segundo mirando a la cámara y luego habla.

---

## B · Podcast multicámara con invitado

Carpeta: `<podcast>/crudos/` (audio de los micrófonos y archivos de cada cámara), `graficos/` (Remotion), `render/` y `trabajo/`. En `episodio.json`, `cam1` es la cámara del invitado y `cam2` la del anfitrión.

### Reglas de edición
- **Resumen al inicio.** Abre con un resumen de 30–60 s (`cold_open` en `guion.json`). Después vienen el intro de marca (7 s), el episodio y una pantalla final de 20 s.
- **Los dos en cuadro casi siempre (≈ 55 %).** Cada cambio de quien habla abre en el plano abierto de su cámara, con un zoom lento hacia esa persona (1.0 → 1.12). No uses pantalla dividida.
- **La cámara siempre es la de quien habla.** Ver a uno mientras habla el otro es un error grave.
- **La música nunca entra fuerte encima de una frase** y baja antes de que alguien hable. Nada de risers encima de la voz.
- **Pantalla final** con dos recuadros 16:9 con etiqueta (`marca.pantalla_final` en `config.json`). Los elementos se ponen en YouTube Studio.
- **Nombres:** escribe bien el nombre del invitado en todo; corrige lo que Whisper escribe mal en `config.json → correcciones`. Pide los links del invitado.

### Pipeline (`trabajo/p*.py`)
1. **Audio y sincronía.**
   - `p1_audio`: mezcla de micrófonos (un micrófono por canal).
   - `p2_sync`: sincroniza cada archivo de cámara con el micrófono. Revisa `puntos`: un archivo con 0 puntos se ubica a mano.
2. **Caras, luz y color.**
   - `p2b_caras`: caras con Apple Vision y apertura de boca. Pásale la ruta completa.
   - `p2c_luz` y `p2d_color`: luz y color de la cara cada 0.5 s.
3. **Texto y hablantes.**
   - `p3_texto`: transcripción con Whisper.
   - `p3b_hablantes` + `p3c_fusion`: quién habla, por timbre y por boca. Calibra con `ref_anfitrion` y `ref_invitado`, tramos donde solo habla esa persona.
4. **Cortes y planos.**
   - `p4_cortes`: corta los silencios. Un pedacito de menos de 1.2 s entre pausas no se corta.
   - `p4b_planos`: elige cámaras, tamaños de plano y gráficos.
5. **Render y entrega.**
   - `p5_render todo`: piezas con ffmpeg en caché, audio, gráficos de Remotion, loudnorm −14 y alimiter.
   - `p6_entrega`: subtítulos `.srt`, borrador de `copy.md` y subtítulos del B-roll.
6. **Revisión:** `qa_uniones.py video 0 si` arma hojas de 6 + 6 cuadros por unión. Revísalas todas.
7. **Miniaturas:**
   - `p7_sonrisas` sugiere los mejores cuadros sonriendo.
   - Recorta a cada persona con `<motor>/bin/matte`. Usa el cuadro 6, porque el 0 puede salir vacío.
   - Guarda los recortes como `graficos/public/anfitrion.png` e `invitado.png`.
   - Arma la miniatura en Remotion con `Miniatura3`: 2–4 palabras que complementen el título sin repetirlo.

### Lecciones
- **Vision da una sola cara por cuadro y a veces es la del otro.** Filtra siempre por la cara principal de esa cámara (`caja` ± 0.2) en la detección de movimiento, en el centro del zoom y en el color.
- **Cuándo una cámara "se movió" de verdad:** nadie en cuadro (< 60 % de cuadros con cara), o el centro de la cara principal varía > 0.12. Un umbral de 0.06 marca como movimiento el ir y venir normal de la cabeza.
- **Color:** usa una curva continua por archivo, no un ajuste por plano, para que dos planos seguidos de la misma toma no brinquen de luz. Calcula la gamma con la mediana ± 6 s y el balance con ± 20 s.
- **Uniones en la misma cámara:** M (1.12) ↔ A (1.0) se ve como un salto. Usa A ↔ C (1.42) y C ↔ C más cerrado (1.68).
- **Texto lateral:** si la cara está pegada al borde, el M todavía muestra al otro y el texto lo taparía. Ese texto va en C.
- **Sin cámaras:** donde ninguna cámara grabó, cubre con B-roll de Pexels y subtítulos grandes. Pon los créditos en `creditos_broll.md`.
- **Gotchas:**
  - En zsh, un glob sin coincidencias aborta todo el comando.
  - Para leer metadatos usa `ffmpeg -i`. `-v error` oculta la salida de metadata=print; usa `-v info`.
  - `-vsync` ya no existe; usa `-fps_mode passthrough`.
