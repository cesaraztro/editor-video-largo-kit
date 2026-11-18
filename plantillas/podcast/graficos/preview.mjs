import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const P = [['Intro', 80], ['Intro', 200], ['Rotulo', 60], ['Capitulo', 60], ['Frase', 80], ['CTA', 80], ['Final', 90], ['Mosca', 0]];
for (const [id, frame] of P) {
  const composition = await selectComposition({serveUrl, id, inputProps: {}});
  await renderStill({composition, serveUrl, output: `prev/${id}_${frame}.png`, frame});
}
console.log('ok');
