// Reparent the existing controls; one map, one selection, and one data controller.
const homes=new Map();
let initialized=false;
const $=id=>document.getElementById(id);
function move(node,target){
  if(!homes.has(node)){const home=document.createComment('territorial control home');node.before(home);homes.set(node,home);}
  target.append(node);
}
export function setImmersiveLayout(active){
  const panel=$('mt-floating-panel'),content=$('mt-sheet-content'),dock=$('mt-scene-dock');
  if(!panel)return;
  if(!initialized){
    initialized=true;
    const details=document.createElement('details');details.id='mt-territory-disclosure';details.innerHTML='<summary>Buscar o cambiar escala territorial</summary>';content.append(details);
    $('mt-sheet-toggle').addEventListener('click',()=>{
      const expanded=panel.dataset.expanded!=='true';panel.dataset.expanded=String(expanded);
      $('mt-sheet-toggle').setAttribute('aria-expanded',String(expanded));
      $('mt-sheet-toggle').innerHTML=expanded?'Volver al mapa <span aria-hidden="true">↓</span>':'Comparar comunas <span aria-hidden="true">↑</span>';
    });
  }
  document.body.classList.toggle('mt-immersive',active);
  for(const node of [panel,dock,...document.querySelectorAll('.mt-scene-title,.mt-scene-foot')])node.hidden=!active;
  if(active){
    move(document.querySelector('.mt-toolbar'),$('mt-territory-disclosure'));
    move($('mt-analysis-controls'),content);
    move(document.querySelector('.mt-dossier'),content);
    move(document.querySelector('.mt-analysis-action-row'),dock);
    // Keep the advanced territory search last in reading order.
    content.append($('mt-territory-disclosure'));
  }else for(const [node,home] of homes)home.after(node);
}
