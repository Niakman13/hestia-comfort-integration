import {build} from 'esbuild';
import {haCardBuild} from './ha-card-build.mjs';
// Built straight into the integration, which serves the card on every dashboard.
await build({entryPoints:['src/card.ts'],bundle:true,...haCardBuild,target:'es2022',minify:true,
  outfile:'../custom_components/niak_comfort/frontend/niak-comfort-card.js',legalComments:'none',loader:{'.css':'text'}});
