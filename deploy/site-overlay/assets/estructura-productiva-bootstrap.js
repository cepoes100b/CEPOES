(function(){
'use strict';
const OFFICIAL='https://cdn.buenosaires.gob.ar/datosabiertos/datasets/innovacion-transformacion-digital/comunas/comunas.geojson';
const LOCAL='/assets/data/estructura-productiva/comunas.geojson';
const nativeFetch=window.fetch.bind(window);
window.fetch=function(input,init){
  const url=typeof input==='string'?input:(input&&input.url)||'';
  if(url===OFFICIAL)return nativeFetch(LOCAL,init);
  return nativeFetch(input,init);
};
})();
