import React from 'react';
import {Composition, Still} from 'remotion';
import '@fontsource/manrope/400.css';
import '@fontsource/manrope/500.css';
import '@fontsource/manrope/600.css';
import '@fontsource/manrope/700.css';
import '@fontsource/manrope/800.css';
import {Intro, Rotulo, Capitulo, Frase, CTA, Final, Mosca, Miniatura, Miniatura2, Miniatura3, Suscribete} from './Podcast';

const comp = (id: string, component: any, defaultProps: any, seg = 5) =>
  <Composition key={id} id={id} component={component} width={1920} height={1080} fps={30} durationInFrames={seg * 30} defaultProps={defaultProps}
    calculateMetadata={({props}: any) => ({durationInFrames: Math.max(15, Math.round((props.duracion ?? seg) * 30))})} />;

export const Root: React.FC = () => <>
  {comp('Intro', Intro, {eyebrow: 'Mi Podcast · Ep. 01', titulo: 'Título del episodio', invitados: 'con Invitado'}, 7)}
  {comp('Rotulo', Rotulo, {nombre: 'Tu Nombre', cargo: 'Tu cargo', lado: 'izq'}, 6)}
  {comp('Capitulo', Capitulo, {num: 1, titulo: 'Título del capítulo'}, 4)}
  {comp('Frase', Frase, {texto: 'La IA no reemplaza a tu equipo, lo potencia', lado: 'izq'}, 6)}
  {comp('Suscribete', Suscribete, {texto: '¿Te está gustando la charla?'}, 6)}
  {comp('CTA', CTA, {titulo: 'Consultoría 1 a 1', sub: 'Agenda en el link de la descripción', extra: 'Únete a mi comunidad'}, 8)}
  {comp('Final', Final, {titulo: 'Gracias por acompañarnos', web: 'tuweb.com', comunidad: 'Únete a mi comunidad'}, 20)}
  <Still id="Mosca" component={Mosca} width={1920} height={1080} />
  <Still id="Miniatura" component={Miniatura} width={1280} height={720} defaultProps={{chip: "NUEVO EPISODIO", lineas: ["La idea", "que cambia", "todo"], resalta: 2}} />
  <Still id="Miniatura2" component={Miniatura2} width={1280} height={720} defaultProps={{chip: "NUEVO EPISODIO", lineas: ["La idea", "clave"], resalta: 1, ella: "invitado.png", el: "anfitrion.png"}} />
  <Still id="Miniatura3" component={Miniatura3} width={1280} height={720} defaultProps={{chip: "NUEVO EPISODIO", lineas: ["Lo que", "nadie dice"], resalta: 1, ella: "invitado.png", el: "anfitrion.png"}} />
</>;
