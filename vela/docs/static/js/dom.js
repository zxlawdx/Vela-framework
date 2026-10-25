// SPDX-License-Identifier: MPL-2.0
export function el(tag, cls='', text) {
  const node=document.createElement(tag); if(cls) node.className=cls;
  if(text!==undefined) node.textContent=String(text); return node;
}
export function button(text,action,cls='') { const b=el('button',cls,text);b.type='button';b.addEventListener('click',action);return b; }
export function codebox(value,label='application/json',raw=false) {
  const box=el('div','codebox'),head=el('div','codehead'),pre=el('pre');
  pre.textContent=raw ? String(value) : JSON.stringify(value,null,2) ?? '';
  const copy=button('Copy ⧉',async()=>{try{await navigator.clipboard.writeText(pre.textContent);copy.textContent='Copiado ✓'}catch{copy.textContent='Cópia indisponível'}},'tiny');
  head.append(el('span','',label),copy);box.append(head,pre);return box;
}
export function tabs(labels,change,selected=labels[0]) {
  const row=el('div','tabs');row.setAttribute('role','tablist');
  labels.forEach(label=>{const b=button(label,()=>{for(const c of row.children){const on=c===b;c.classList.toggle('active',on);c.setAttribute('aria-selected',String(on));c.tabIndex=on?0:-1}change(label)},label===selected?'active':'');b.setAttribute('role','tab');b.setAttribute('aria-selected',String(label===selected));b.tabIndex=label===selected?0:-1;row.append(b)});
  row.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();const all=[...row.children],i=all.indexOf(document.activeElement);const n=e.key==='Home'?0:e.key==='End'?all.length-1:(i+(e.key==='ArrowRight'?1:-1)+all.length)%all.length;all[n].click();all[n].focus()});return row;
}
export function field(label,input) {const wrap=el('label','field',label);wrap.append(input);return wrap;}
export const storage={get(k,fallback){try{return JSON.parse(localStorage.getItem('vela.docs.'+k))??fallback}catch{return fallback}},set(k,v){try{localStorage.setItem('vela.docs.'+k,JSON.stringify(v))}catch{}}};
