const button=document.getElementById('mt-theme');
try{const saved=localStorage.getItem('cepoes-theme');if(saved==='light'||saved==='dark')document.documentElement.dataset.theme=saved;}catch{}
const label=()=>{button.textContent=document.documentElement.dataset.theme==='dark'?'Tema claro':'Tema oscuro';};
label();
button.addEventListener('click',()=>{const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('cepoes-theme',theme);}catch{}label();});
