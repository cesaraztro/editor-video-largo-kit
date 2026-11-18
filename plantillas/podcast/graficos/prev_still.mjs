// node prev_still.mjs lista.json frame  -> renderiza un cuadro concreto (para revisar composiciones animadas)
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs'; import path from 'node:path';
const [lista, frame] = [JSON.parse(fs.readFileSync(process.argv[2], 'utf8')), Number(process.argv[3] || 60)];
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
for (const g of lista) {
  const composition = await selectComposition({serveUrl, id: g.comp, inputProps: g.props});
  await renderStill({composition, serveUrl, output: g.out, inputProps: g.props, frame, imageFormat: 'png'});
}
