// node render.mjs lista.json  -> [{comp, props, out}]  (ProRes 4444 con alfa; .png para Stills). Salta lo que ya existe.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
const lista = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).filter((g) => !fs.existsSync(g.out));
if (!lista.length) { console.log('gráficos: todo en caché'); process.exit(0); }
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
for (const g of lista) {
  const composition = await selectComposition({serveUrl, id: g.comp, inputProps: g.props});
  if (g.out.endsWith('.png')) { await renderStill({composition, serveUrl, output: g.out, inputProps: g.props, imageFormat: 'png'}); continue; }
  const tmp = g.out + '.tmp.mov';
  await renderMedia({composition, serveUrl, codec: 'prores', proResProfile: '4444', pixelFormat: 'yuva444p10le',
    imageFormat: 'png', outputLocation: tmp, inputProps: g.props, concurrency: 4, logLevel: 'error'});
  fs.renameSync(tmp, g.out);
  console.log('ok', path.basename(g.out));
}
