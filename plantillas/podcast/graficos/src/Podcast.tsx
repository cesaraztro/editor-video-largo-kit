// Gráficos del podcast de YouTube (16:9, 1920×1080, 30 fps). Tipografía y colores de paleta.ts.
// Tono serio: movimientos con easing expo, sin rebotes, sin emojis. Todo con alfa salvo Intro/Final, que son opacos.
import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig, Easing, staticFile} from 'remotion';
import logo from './logo.svg';   // reemplázalo por el logo de tu marca (SVG)
import {C, Z, DEGRADADO} from './paleta';

const expo = Easing.bezier(0.16, 1, 0.3, 1);
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const BLANCO = 'brightness(0) invert(1)';

const useSalida = (frames = 12) => {
  const f = useCurrentFrame();
  const {durationInFrames: d} = useVideoConfig();
  return interpolate(f, [d - frames, d], [1, 0], {...cl, easing: Easing.in(Easing.cubic)});
};

// texto que sube desde una máscara
const Sube: React.FC<{children: React.ReactNode; delay?: number; dur?: number; style?: React.CSSProperties}> = ({children, delay = 0, dur = 20, style}) => {
  const f = useCurrentFrame();
  const p = interpolate(f - delay, [0, dur], [0, 1], {...cl, easing: expo});
  return <div style={{overflow: 'hidden', paddingBottom: '0.08em', ...style}}>
    <div style={{transform: `translateY(${(1 - p) * 110}%)`, opacity: p}}>{children}</div>
  </div>;
};

// fondo de marca: Darkest Hour con dos luces lentas (violeta y naranja) y viñeta
const Fondo: React.FC = () => {
  const f = useCurrentFrame();
  const a = interpolate(f, [0, 600], [0, 1]);
  return <AbsoluteFill style={{background: C.navy}}>
    <AbsoluteFill style={{background: `radial-gradient(900px 700px at ${18 + a * 8}% ${22 + a * 6}%, ${C.acento}55 0%, transparent 70%)`}} />
    <AbsoluteFill style={{background: `radial-gradient(800px 600px at ${86 - a * 6}% ${84 - a * 4}%, ${C.naranja}33 0%, transparent 70%)`}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.55) 100%)'}} />
  </AbsoluteFill>;
};

const Linea: React.FC<{p: number; w: number; alto?: number; style?: React.CSSProperties}> = ({p, w, alto = 3, style}) =>
  <div style={{width: w, height: alto, ...style}}><div style={{height: alto, width: `${p * 100}%`, background: DEGRADADO(90), borderRadius: alto}} /></div>;

// ───────────────────────── INTRO (opaca, termina con barrido que revela el video) ─────────────────────────
export const Intro: React.FC<{eyebrow: string; titulo: string; invitados: string}> = ({eyebrow, titulo, invitados}) => {
  const f = useCurrentFrame();
  const {durationInFrames: d} = useVideoConfig();
  const entra = interpolate(f, [0, 10], [0, 1], cl);
  const lin = interpolate(f, [6, 34], [0, 1], {...cl, easing: expo});
  const lg = interpolate(f, [14, 44], [0, 1], {...cl, easing: expo});
  const zoom = interpolate(f, [0, d], [1.0, 1.04]);
  // salida: barrido diagonal con el degradado de firma que deja ver el video
  const sx = interpolate(f, [d - 22, d - 2], [0, 1], {...cl, easing: Easing.inOut(Easing.cubic)});
  const corte = sx * 130;
  return <AbsoluteFill style={{opacity: entra}}>
    <AbsoluteFill style={{clipPath: `polygon(${corte}% 0, 130% 0, 130% 100%, ${corte - 30}% 100%)`}}>
      <Fondo />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', transform: `scale(${zoom})`}}>
        <div style={{opacity: lg, transform: `translateY(${(1 - lg) * 18}px)`, filter: `blur(${(1 - lg) * 8}px)`}}>
          <Img src={logo} style={{width: 640, filter: BLANCO}} />
        </div>
        <Linea p={lin} w={520} style={{margin: '44px 0 40px', display: 'flex', justifyContent: 'center'}} />
        <Sube delay={30} style={{textAlign: 'center'}}>
          <div style={{fontFamily: Z, fontWeight: 600, fontSize: 26, letterSpacing: 10, color: C.oro, textTransform: 'uppercase'}}>{eyebrow}</div>
        </Sube>
        <Sube delay={38} dur={24} style={{textAlign: 'center', maxWidth: 1500, marginTop: 22}}>
          <div style={{fontFamily: Z, fontWeight: 800, fontSize: 78, lineHeight: 1.08, color: C.paper, letterSpacing: -1}}>{titulo}</div>
        </Sube>
        {invitados ? <Sube delay={50} style={{textAlign: 'center', marginTop: 26}}>
          <div style={{fontFamily: Z, fontWeight: 500, fontSize: 32, color: `${C.paper}CC`}}>{invitados}</div>
        </Sube> : null}
      </AbsoluteFill>
    </AbsoluteFill>
    {/* borde luminoso del barrido */}
    {sx > 0 && sx < 1 ? <div style={{position: 'absolute', top: '-10%', bottom: '-10%', width: 26, left: `${corte - 15}%`,
      transform: 'skewX(-17deg)', background: DEGRADADO(180), boxShadow: `0 0 60px ${C.naranja}`}} /> : null}
  </AbsoluteFill>;
};

// ───────────────────────── RÓTULO (nombre y cargo) ─────────────────────────
export const Rotulo: React.FC<{nombre: string; cargo: string; lado?: 'izq' | 'der'}> = ({nombre, cargo, lado = 'izq'}) => {
  const f = useCurrentFrame();
  const s = useSalida(14);
  const barra = interpolate(f, [0, 16], [0, 1], {...cl, easing: expo});
  const caja = interpolate(f, [4, 26], [0, 1], {...cl, easing: expo});
  const pos: React.CSSProperties = lado === 'izq' ? {left: 110} : {right: 110};
  return <AbsoluteFill style={{opacity: s}}>
    <AbsoluteFill style={{background: 'linear-gradient(0deg, rgba(32,30,31,.55) 0%, rgba(32,30,31,0) 34%)', opacity: caja}} />
    <AbsoluteFill style={{background: `radial-gradient(1000px 420px at ${lado === 'izq' ? '8%' : '92%'} 92%, rgba(32,30,31,.7) 0%, rgba(32,30,31,0) 70%)`, opacity: caja}} />
    <div style={{position: 'absolute', bottom: 120, ...pos, display: 'flex', alignItems: 'stretch', flexDirection: lado === 'izq' ? 'row' : 'row-reverse'}}>
      <div style={{width: 6, background: DEGRADADO(180), borderRadius: 3, transform: `scaleY(${barra})`, transformOrigin: 'bottom'}} />
      <div style={{padding: lado === 'izq' ? '6px 0 6px 26px' : '6px 26px 6px 0', textAlign: lado === 'izq' ? 'left' : 'right'}}>
        <Sube delay={6}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 50, color: C.paper, letterSpacing: -0.5,
          textShadow: '0 3px 20px rgba(0,0,0,.5)'}}>{nombre}</div></Sube>
        <Sube delay={12}><div style={{fontFamily: Z, fontWeight: 600, fontSize: 27, color: C.oro, letterSpacing: 2.5, textTransform: 'uppercase',
          marginTop: 4, textShadow: '0 2px 14px rgba(0,0,0,.6)'}}>{cargo}</div></Sube>
      </div>
    </div>
  </AbsoluteFill>;
};

// ───────────────────────── CAPÍTULO (etiqueta arriba a la izquierda) ─────────────────────────
export const Capitulo: React.FC<{num: number; titulo: string; lado?: 'izq' | 'der'}> = ({num, titulo, lado = 'izq'}) => {
  const der = lado === 'der';
  const f = useCurrentFrame();
  const s = useSalida(14);
  const velo = interpolate(f, [0, 14], [0, 1], {...cl, easing: expo});
  const lin = interpolate(f, [10, 34], [0, 1], {...cl, easing: expo});
  return <AbsoluteFill style={{opacity: s}}>
    <AbsoluteFill style={{opacity: velo, background: `linear-gradient(${der ? 245 : 115}deg, rgba(32,30,31,.82) 0%, rgba(32,30,31,.45) 30%, rgba(32,30,31,0) 52%)`}} />
    <div style={{position: 'absolute', top: der ? 190 : 96, ...(der ? {right: 110, textAlign: 'right' as const} : {left: 110}), maxWidth: 900}}>
      <Sube><div style={{fontFamily: Z, fontWeight: 700, fontSize: 24, letterSpacing: 9, color: C.oro}}>
        CAPÍTULO {String(num).padStart(2, '0')}</div></Sube>
      <Linea p={lin} w={260} style={{margin: der ? '18px 0 20px auto' : '18px 0 20px', ...(der ? {display: 'flex', justifyContent: 'flex-end'} : {})}} />
      <Sube delay={8} dur={24}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.paper, letterSpacing: -0.5,
        textShadow: '0 4px 26px rgba(0,0,0,.45)'}}>{titulo}</div></Sube>
    </div>
  </AbsoluteFill>;
};

// ───────────────────────── FRASE CLAVE (lateral, sobre el plano abierto) ─────────────────────────
export const Frase: React.FC<{texto: string; lado?: 'izq' | 'der'}> = ({texto, lado = 'izq'}) => {
  const f = useCurrentFrame();
  const s = useSalida(14);
  const velo = interpolate(f, [0, 14], [0, 1], {...cl, easing: expo});
  const pal = texto.split(' ');
  return <AbsoluteFill style={{opacity: s}}>
    <AbsoluteFill style={{opacity: velo, background: lado === 'izq'
      ? 'linear-gradient(90deg, rgba(32,30,31,.85) 0%, rgba(32,30,31,.5) 32%, rgba(32,30,31,0) 50%)'
      : 'linear-gradient(270deg, rgba(32,30,31,.85) 0%, rgba(32,30,31,.5) 32%, rgba(32,30,31,0) 50%)'}} />
    <div style={{position: 'absolute', top: 0, bottom: 0, [lado === 'izq' ? 'left' : 'right']: 110, width: 700, display: 'flex',
      flexDirection: 'column', justifyContent: 'center', textAlign: lado === 'izq' ? 'left' : 'right'}}>
      <div style={{fontFamily: Z, fontWeight: 800, fontSize: 120, lineHeight: 0.6, color: C.oro, opacity: velo}}>“</div>
      <div style={{display: 'flex', flexWrap: 'wrap', gap: '4px 16px', justifyContent: lado === 'izq' ? 'flex-start' : 'flex-end'}}>
        {pal.map((w, i) => <Sube key={i} delay={4 + i * 1.6}><span style={{fontFamily: Z, fontWeight: 700, fontSize: 54, lineHeight: 1.12,
          color: C.paper}}>{w}</span></Sube>)}
      </div>
    </div>
  </AbsoluteFill>;
};

// ───────────────────────── CTA (tarjeta abajo) ─────────────────────────
export const CTA: React.FC<{titulo: string; sub: string; extra?: string}> = ({titulo, sub, extra}) => {
  const f = useCurrentFrame();
  const s = useSalida(14);
  const p = interpolate(f, [0, 22], [0, 1], {...cl, easing: expo});
  return <AbsoluteFill style={{opacity: s}}>
    <AbsoluteFill style={{background: 'linear-gradient(0deg, rgba(32,30,31,.7) 0%, rgba(32,30,31,0) 40%)', opacity: p}} />
    <div style={{position: 'absolute', bottom: 110, left: '50%', transform: `translate(-50%, ${(1 - p) * 40}px)`, opacity: p,
      background: 'rgba(32,30,31,.88)', borderRadius: 22, padding: '30px 54px', minWidth: 900, textAlign: 'center',
      boxShadow: '0 20px 60px rgba(0,0,0,.45)', border: `1px solid ${C.paper}22`}}>
      <div style={{position: 'absolute', top: 0, left: 40, right: 40, height: 4, background: DEGRADADO(90), borderRadius: 4}} />
      <Sube delay={6}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 46, color: C.paper}}>{titulo}</div></Sube>
      <Sube delay={11}><div style={{fontFamily: Z, fontWeight: 600, fontSize: 28, color: C.oro, marginTop: 8}}>{sub}</div></Sube>
      {extra ? <Sube delay={16}><div style={{fontFamily: Z, fontWeight: 500, fontSize: 24, color: `${C.paper}BB`, marginTop: 10}}>{extra}</div></Sube> : null}
    </div>
  </AbsoluteFill>;
};

// ───────────────────────── SUSCRÍBETE (recordatorio animado, abajo a la izquierda) ─────────────────────────
export const Suscribete: React.FC<{texto: string}> = ({texto}) => {
  const f = useCurrentFrame();
  const s = useSalida(14);
  const p = interpolate(f, [0, 20], [0, 1], {...cl, easing: expo});
  const clic = interpolate(f, [52, 58, 64], [1, 0.9, 1], cl);          // "clic" en el botón
  const hecho = f >= 58;
  const campana = hecho ? Math.sin(Math.max(0, f - 70) / 2.2) * 18 * Math.exp(-Math.max(0, f - 70) / 18) : 0;
  return <AbsoluteFill style={{opacity: s}}>
    <div style={{position: 'absolute', left: 64, bottom: 90, display: 'flex', alignItems: 'center', gap: 22, opacity: p,
      transform: `translateY(${(1 - p) * 40}px)`, background: 'rgba(32,30,31,.88)', borderRadius: 22, padding: '20px 26px 20px 30px',
      border: `1px solid ${C.paper}22`, boxShadow: '0 20px 60px rgba(0,0,0,.45)'}}>
      <div style={{fontFamily: Z, fontWeight: 700, fontSize: 30, color: C.paper, maxWidth: 520, lineHeight: 1.15}}>{texto}</div>
      <div style={{transform: `scale(${clic})`, background: hecho ? '#5A5758' : C.naranja, color: C.paper, fontFamily: Z, fontWeight: 800,
        fontSize: 30, letterSpacing: 1.5, padding: '16px 30px', borderRadius: 40, whiteSpace: 'nowrap'}}>{hecho ? 'SUSCRITO ✓' : 'SUSCRÍBETE'}</div>
      <div style={{fontSize: 44, transform: `rotate(${campana}deg)`, transformOrigin: '50% 10%', opacity: hecho ? 1 : 0.35}}>🔔</div>
    </div>
  </AbsoluteFill>;
};

// ───────────────────────── PANTALLA FINAL (20 s, espacio para los elementos de YouTube) ─────────────────────────
export const Final: React.FC<{titulo: string; web: string; comunidad: string; videos?: string[]}> = ({titulo, web, comunidad, videos = []}) => {
  const f = useCurrentFrame();
  const entra = interpolate(f, [0, 18], [0, 1], {...cl, easing: expo});
  const lin = interpolate(f, [10, 40], [0, 1], {...cl, easing: expo});
  const caja = (delay: number) => interpolate(f, [delay, delay + 24], [0, 1], {...cl, easing: expo});
  return <AbsoluteFill style={{opacity: entra}}>
    <Fondo />
    {/* izquierda: marca y llamados */}
    <div style={{position: 'absolute', left: 130, top: 0, bottom: 0, width: 620, display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
      <Img src={logo} style={{width: 420, filter: BLANCO, opacity: caja(4)}} />
      <Linea p={lin} w={300} style={{margin: '40px 0 36px'}} />
      <Sube delay={16}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 60, lineHeight: 1.08, color: C.paper}}>{titulo}</div></Sube>
      <Sube delay={24}><div style={{fontFamily: Z, fontWeight: 700, fontSize: 34, color: C.oro, marginTop: 30}}>{web}</div></Sube>
      <Sube delay={30}><div style={{fontFamily: Z, fontWeight: 500, fontSize: 28, color: `${C.paper}CC`, marginTop: 12}}>{comunidad}</div></Sube>
      {/* zona del botón de suscribirse de YouTube */}
      <div style={{marginTop: 54, width: 190, height: 190, borderRadius: 95, border: `2px solid ${C.paper}33`, opacity: caja(36)}} />
    </div>
    {/* derecha: dos ventanas 16:9 para los elementos de pantalla final de YouTube (videos elegidos en YouTube Studio) */}
    {[0, 1].map((i) => <div key={i} style={{position: 'absolute', right: 130, top: 80 + i * 475, width: 720, opacity: caja(20 + i * 8),
      transform: `translateX(${(1 - caja(20 + i * 8)) * 60}px)`}}>
      {videos[i] ? <div style={{fontFamily: Z, fontWeight: 800, fontSize: 30, letterSpacing: 2, color: i ? C.oro : C.paper, marginBottom: 14,
        textTransform: 'uppercase'}}>{videos[i]}</div> : null}
      <div style={{width: 720, height: 405, borderRadius: 18, border: `2px solid ${i ? C.oro : C.acento}88`, background: 'rgba(255,255,255,.04)',
        boxShadow: `0 0 60px ${i ? C.oro : C.acento}22`}} />
    </div>)}
  </AbsoluteFill>;
};

// ───────────────────────── LOGO (marca de agua, arriba a la derecha) ─────────────────────────
export const Mosca: React.FC = () =>
  <AbsoluteFill>
    <AbsoluteFill style={{background: 'radial-gradient(520px 230px at 92% 6%, rgba(32,30,31,.42) 0%, rgba(32,30,31,0) 72%)'}} />
    <Img src={logo} style={{position: 'absolute', top: 54, right: 64, width: 250, opacity: 0.92,
      filter: `${BLANCO} drop-shadow(0 0 10px rgba(0,0,0,.55)) drop-shadow(0 2px 3px rgba(0,0,0,.5))`}} />
  </AbsoluteFill>;

// ───────────────────────── MINIATURA de YouTube (1280×720) ─────────────────────────
export const Miniatura: React.FC<{chip: string; lineas: string[]; resalta: number}> = ({chip, lineas, resalta}) =>
  <AbsoluteFill style={{background: C.navy, overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(620px 520px at 78% 55%, ${C.naranja}66 0%, transparent 70%)`}} />
    <AbsoluteFill style={{background: `radial-gradient(700px 560px at 10% 10%, ${C.acento}77 0%, transparent 70%)`}} />
    <Img src={staticFile('anfitrion.png')} style={{position: 'absolute', height: 500, right: -190, bottom: 0, filter: 'brightness(.92) saturate(.95)'}} />
    <Img src={staticFile('invitado.png')} style={{position: 'absolute', height: 590, right: 110, bottom: -10,
      filter: 'drop-shadow(0 0 30px rgba(0,0,0,.55)) saturate(1.05) contrast(1.04)'}} />
    <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(32,30,31,.92) 0%, rgba(32,30,31,.6) 38%, rgba(32,30,31,0) 58%)'}} />
    <div style={{position: 'absolute', left: 56, top: 54, width: 660}}>
      <div style={{display: 'inline-block', background: C.acento, color: C.paper, fontFamily: Z, fontWeight: 800, fontSize: 30,
        letterSpacing: 2, padding: '10px 22px', borderRadius: 10}}>{chip}</div>
      <div style={{marginTop: 26}}>
        {lineas.map((l, i) => <div key={i}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 78, whiteSpace: 'nowrap', lineHeight: 1.0, letterSpacing: -2,
          textTransform: 'uppercase', color: i === resalta ? C.navy : C.paper, background: i === resalta ? C.oro : 'transparent',
          display: 'inline-block', padding: i === resalta ? '4px 14px 8px' : '2px 0', marginTop: i === resalta ? 10 : 0,
          textShadow: i === resalta ? 'none' : '0 4px 18px rgba(0,0,0,.6)'}}>{l}</div></div>)}
      </div>
      <div style={{width: 300, height: 8, borderRadius: 8, background: DEGRADADO(90), marginTop: 26}} />
    </div>
    <Img src={logo} style={{position: 'absolute', left: 56, bottom: 44, width: 230, filter: BLANCO}} />
  </AbsoluteFill>;

// ─────────────── MINIATURA v2: caras grandes con expresión, máximo 4 palabras, alto contraste ───────────────
export const Miniatura2: React.FC<{chip: string; lineas: string[]; resalta: number; ella: string; el: string; dx?: number; tono?: string}> = ({chip, lineas, resalta, ella, el, dx = 0, tono = ''}) =>
  <AbsoluteFill style={{background: C.navy, overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(560px 520px at 70% 45%, ${C.acento}aa 0%, transparent 72%)`}} />
    <AbsoluteFill style={{background: `radial-gradient(520px 460px at 96% 85%, ${C.naranja}88 0%, transparent 70%)`}} />
    <Img src={staticFile(el)} style={{position: 'absolute', height: 540, right: -175 + dx, bottom: -30,
      filter: 'drop-shadow(0 0 26px rgba(0,0,0,.6)) brightness(1.02) saturate(1.05) contrast(1.06)'}} />
    <Img src={staticFile(ella)} style={{position: 'absolute', height: 700, right: 120 + dx, bottom: -90,
      filter: `drop-shadow(0 0 34px rgba(0,0,0,.7)) brightness(.97) saturate(1.12) contrast(1.08) ${tono}`}} />
    <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(32,30,31,.95) 0%, rgba(32,30,31,.75) 30%, rgba(32,30,31,0) 50%)'}} />
    <div style={{position: 'absolute', left: 52, top: 60, width: 640}}>
      <div style={{display: 'inline-block', background: C.acento, color: C.paper, fontFamily: Z, fontWeight: 800, fontSize: 28,
        letterSpacing: 2, padding: '9px 20px', borderRadius: 10}}>{chip}</div>
      <div style={{marginTop: 30}}>
        {lineas.map((l, i) => <div key={i}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 100, whiteSpace: 'nowrap', lineHeight: 0.98, letterSpacing: -4,
          textTransform: 'uppercase', color: i === resalta ? C.navy : C.paper, background: i === resalta ? C.oro : 'transparent',
          display: 'inline-block', padding: i === resalta ? '6px 18px 12px' : '0', marginTop: i === resalta ? 14 : 0, transform: i === resalta ? 'rotate(-1.5deg)' : 'none',
          textShadow: i === resalta ? 'none' : '0 6px 24px rgba(0,0,0,.7)'}}>{l}</div></div>)}
      </div>
    </div>
    <Img src={logo} style={{position: 'absolute', left: 52, bottom: 44, width: 210, filter: BLANCO}} />
  </AbsoluteFill>;

// Miniatura 3 · los dos sonriendo, caras grandes a la derecha, texto GANA corto a la izquierda
export const Miniatura3: React.FC<{chip: string; lineas: string[]; resalta: number; ella: string; el: string;
  ellaH?: number; elH?: number; ellaR?: number; elR?: number; ellaB?: number; elB?: number}> =
  ({chip, lineas, resalta, ella, el, ellaH = 1000, elH = 980, ellaR = -40, elR = 330, ellaB = -330, elB = -360}) =>
  <AbsoluteFill style={{background: C.navy, overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(620px 560px at 72% 40%, ${C.acento}bb 0%, transparent 72%)`}} />
    <AbsoluteFill style={{background: `radial-gradient(520px 460px at 98% 95%, ${C.naranja}99 0%, transparent 70%)`}} />
    <Img src={staticFile(el)} style={{position: 'absolute', height: elH, right: elR, bottom: elB,
      filter: 'drop-shadow(0 0 30px rgba(0,0,0,.65)) brightness(1.04) saturate(1.08) contrast(1.06)'}} />
    <Img src={staticFile(ella)} style={{position: 'absolute', height: ellaH, right: ellaR, bottom: ellaB,
      filter: 'drop-shadow(0 0 34px rgba(0,0,0,.7)) brightness(1.0) saturate(1.1) contrast(1.08)'}} />
    <AbsoluteFill style={{background: 'linear-gradient(90deg, rgba(32,30,31,.96) 0%, rgba(32,30,31,.8) 28%, rgba(32,30,31,0) 46%)'}} />
    <div style={{position: 'absolute', left: 52, top: 70, width: 600}}>
      <div style={{display: 'inline-block', background: C.acento, color: C.paper, fontFamily: Z, fontWeight: 800, fontSize: 28,
        letterSpacing: 2, padding: '9px 20px', borderRadius: 10}}>{chip}</div>
      <div style={{marginTop: 30}}>
        {lineas.map((l, i) => <div key={i}><div style={{fontFamily: Z, fontWeight: 800, fontSize: 104, whiteSpace: 'nowrap', lineHeight: 0.98, letterSpacing: -4,
          textTransform: 'uppercase', color: i === resalta ? C.navy : C.paper, background: i === resalta ? C.oro : 'transparent',
          display: 'inline-block', padding: i === resalta ? '6px 18px 12px' : '0', marginTop: i === resalta ? 14 : 0, transform: i === resalta ? 'rotate(-1.5deg)' : 'none',
          textShadow: i === resalta ? 'none' : '0 6px 24px rgba(0,0,0,.7)'}}>{l}</div></div>)}
      </div>
    </div>
    <Img src={logo} style={{position: 'absolute', left: 52, bottom: 44, width: 210, filter: BLANCO}} />
  </AbsoluteFill>;
