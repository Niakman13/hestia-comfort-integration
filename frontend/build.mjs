import {build} from 'esbuild';
await build({entryPoints:['panel.ts'],bundle:true,format:'esm',target:'es2022',minify:true,
  outfile:'../custom_components/niak_comfort/frontend/panel.js',legalComments:'none',loader:{'.css':'text'}});
