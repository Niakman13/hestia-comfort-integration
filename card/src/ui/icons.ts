import {html} from 'lit';
import {unsafeSVG} from 'lit/directives/unsafe-svg.js';
const paths:Record<string,string>={
  window:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M12 3v18M4 12h16"/>',
  open:'<path d="M4 3h16v18H4zM12 3l6 3v12l-6 3V3M4 12h8"/>',
  air:'<path d="M3 8h12a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h6a3 3 0 1 1-3 3"/>',
  temp:'<path d="M10 14V5a2 2 0 0 1 4 0v9a4 4 0 1 1-4 0Z"/><path d="M12 9v8"/>',
  drop:'<path d="M12 3C10 7 5 11 5 15a7 7 0 0 0 14 0c0-4-5-8-7-12Z"/><path d="M8 15a4 4 0 0 0 4 4"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  moon:'<path d="M20 14a9 9 0 0 1-10-12 9 9 0 1 0 10 12Z"/>',
  heat:'<path d="M7 20V8m5 12V8m5 12V8M5 10h14v10H5zM8 2v3m4-3v3m4-3v3"/>',
  rain:'<path d="M6 14a4 4 0 0 1 0-8 6 6 0 0 1 11-1 4.5 4.5 0 0 1 1 9H6m1 3-1 3m6-3-1 3m6-3-1 3"/>',
  cold:'<path d="M12 2v20M3 7l18 10M3 17 21 7M9 4l3 3 3-3M9 20l3-3 3 3"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  chevron:'<path d="m6 9 6 6 6-6"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  up:'<path d="m6 14 6-6 6 6"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  settings:'<path d="M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6M10 15v6"/>',
  source:'<path d="M8 8h8v8H8zM9 2v3m6-3v3M9 19v3m6-3v3M2 9h3m-3 6h3m14-6h3m-3 6h3"/>',
  cloud:'<path d="M6 18a5 5 0 0 1-1-10 7 7 0 0 1 13-2 6 6 0 0 1 0 12H6Z"/>',
  home:'<path d="m3 11 9-8 9 8M5 9v12h14V9M10 21v-7h4v7"/>',
  link:'<path d="m10 14 4-4m-5-3 2-2a5 5 0 0 1 7 7l-2 2M8 10l-2 2a5 5 0 0 0 7 7l2-2"/>',
  alert:'<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3v.1"/>',
  ask:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .9-1 1.7M12 17h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  shut:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M17 12H8m3-3-3 3 3 3"/>',
  pm:'<circle cx="7" cy="8" r="1.4"/><circle cx="14" cy="6" r="1.1"/><circle cx="18" cy="11" r="1.4"/><circle cx="10" cy="14" r="1.1"/><circle cx="16" cy="17" r="1.3"/><circle cx="7" cy="19" r="1"/>',
  flask:'<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
  vmc:'<path d="M4 7h11a3 3 0 1 0-3-3M4 12h15a3 3 0 1 1-3 3M4 17h7"/><path d="M19 4v4m-2-2h4"/>',
  fan:'<circle cx="12" cy="12" r="2"/><path d="M12 10c-1-4 0-7 3-7 2 0 2 3-1 7m-2 4c1 4 0 7-3 7-2 0-2-3 1-7m2-2c4-1 7 0 7 3 0 2-3 2-7-1m-4 0c-4 1-7 0-7-3 0-2 3-2 7 1"/>'
};
export const icon = (name:string, cls='') => html`<svg class=${'icon '+cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${unsafeSVG(paths[name]??paths.info)}</svg>`;
