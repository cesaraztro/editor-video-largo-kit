// Tu marca: única fuente de verdad de colores y tipografía de los gráficos del motor.
// Se conservan los nombres de la paleta anterior (navy, paper, oro…) para que cada componente siga igual.
export const C = {
  navy: '#201E1F',      // Darkest Hour: fondos y cajas
  paper: '#F3F0EB',     // Cloud Dancer: texto claro
  oro: '#DAFF02',       // Sun Glare: énfasis
  oroClaro: '#EDFF8A',  // Sun Glare aclarado: brillos
  acento: '#685BC7',    // Blue Violet
  naranja: '#FE582A',   // Exuberant Orange
};
export const P = 'Manrope', Z = 'Manrope';
// degradado de firma: violeta → naranja (55 %) → lima
export const DEGRADADO = (ang = 90) => `linear-gradient(${ang}deg, ${C.acento} 0%, ${C.naranja} 55%, ${C.oro} 100%)`;
