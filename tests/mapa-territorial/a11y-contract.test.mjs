// Static checks only: actual layout, keyboard flow and touch still need a browser.
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
const root=new URL('../../experiments/mapa-territorial/public/',import.meta.url);
function luminance(hex){const c=hex.match(/[a-f0-9]{2}/gi).map(x=>parseInt(x,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722;}
const contrast=(a,b)=>{const x=[luminance(a),luminance(b)].sort((a,b)=>b-a);return(x[0]+.05)/(x[1]+.05);};
test('explicit foreground/background colors meet text and control contrast',()=>{
  for(const [fg,bg] of [['#203747','#ffffff'],['#4c6274','#f2f6fa'],['#00769f','#ffffff'],['#f1f7fc','#142a39'],['#b6c9d6','#10222f'],['#80dbf6','#142a39'],['#0e2939','#c2eef9'],['#ffffff','#07516d']])assert.ok(contrast(fg,bg)>=4.5,`${fg}/${bg}`);
  assert.ok(contrast('#333333','#ffffff')>=3);assert.ok(contrast('#123b51','#ffffff')>=3);
});
test('page exposes text alternative, labels, live statuses, safe initial controls and noindex',async()=>{
  const html=await readFile(new URL('laboratorio/mapa-territorial/index.html',root),'utf8');
  for(const token of ['noindex, nofollow','id="mt-territory-table"','id="mt-territory"','id="mt-search"','aria-live="polite"','id="mt-fit" disabled','id="mt-streets" disabled','<noscript>'])assert.ok(html.includes(token),token);
  const css=await readFile(new URL('assets/mapa-territorial/map.css',root),'utf8');
  for(const token of ['min-height:44px',':focus-visible','prefers-reduced-motion','max-width:350px','max-width:760px','min-width:1440px','[data-theme=dark] .mt-input-row button:hover'])assert.ok(css.includes(token),token);
});
