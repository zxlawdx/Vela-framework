// SPDX-License-Identifier: MPL-2.0
import {indexSpec,resolve,mediaExample} from './openapi.js';
import {schemaTree} from './schemas.js';
import {el,button,codebox,tabs,storage} from './dom.js';
import {mountTry} from './try_it.js';
import {serverUrl} from './request.js';
const $=id=>document.getElementById(id),main=$('main'),schemaURL=document.querySelector('meta[name="vela-openapi"]').content;
let spec,index,active='',dispose=()=>{},searchItems=[];
const closed=new Set(storage.get('closed',[]));
function link(id){return '#/'+encodeURIComponent(id)}
function navigate(id){if(location.hash===link(id))render(id);else location.hash=link(id)}
function selected(){try{return decodeURIComponent(location.hash.slice(2))||'intro'}catch{return 'intro'}}
function overview(){
  const title=el('h1','',spec.info?.title || 'Vela API');main.append(el('div','crumb','Workspace / Introduction'),title,el('p','',spec.info?.description || 'Documentação interativa da API local desta aplicação Vela.'));
  const table=el('table');for(const [name,value] of [['OpenAPI',spec.openapi],['Server',spec.servers?.[0]?.url || '/'],['Framework','Vela'],['API version',spec.info?.version || '']]){const tr=el('tr');tr.append(el('td','muted',name),el('td','',value));table.append(tr)}main.append(table);
  const quick=index.operations.find(o=>o.method==='GET'&&!o.path.includes('{'));if(quick){main.append(el('h2','','Quick start'),codebox('curl '+serverUrl(quick.servers[0],location.href).replace(/\/$/,'')+'/'+quick.path.replace(/^\//,''),'bash',true))}
  main.append(el('h2','','Endpoints'));const stats=el('div','stats');for(const [count,name] of [[index.operations.length,'endpoints'],[index.groups.size,'grupos'],[index.schemas.length,'schemas']]){const item=el('div','stat');item.append(el('strong','',count),el('span','',name));stats.append(item)}main.append(stats);
  if(!index.operations.length)main.append(el('p','','No API endpoints registered.'));
}
function parameterTable(op){const table=el('table'),head=el('tr');for(const h of ['Name / Location','Type','Required','Description'])head.append(el('th','',h));table.append(head);for(const p of op.parameters){const row=el('tr'),s=resolve(spec,p.schema);row.append(el('td','',p.name+' · '+p.in),el('td','muted',s.type || s.$ref || 'schema'),el('td',p.required?'req':'muted',p.required?'required':'optional'),el('td','',p.description||'—'));table.append(row)}return table}
function contentView(content){const root=el('div'),types=Object.keys(content||{});if(!types.length){root.append(el('p','muted','Nenhum corpo documentado.'));return root}
  const selected=el('div');const renderType=t=>{const media=content[t],body=el('div');selected.replaceChildren(tabs(['Example','Schema'],mode=>body.replaceChildren(mode==='Schema'?schemaTree(spec,media.schema):codebox(mediaExample(spec,media),t))),body);body.append(codebox(mediaExample(spec,media),t))};
  if(types.length>1)root.append(tabs(types,renderType));root.append(selected);renderType(types[0]);return root;
}
function operationView(op){
  main.append(el('div','crumb','API Reference / '+op.tags.join(' / ')));const path=el('div','path');path.append(el('span','pill',op.method),el('code','',op.path));main.append(path,el('h1','',op.summary || op.operationId || op.path),el('p','',op.description || 'No description provided.'));
  const meta=el('div','meta','operationId: '+(op.operationId || '—'));op.tags.forEach(t=>meta.append(el('span','badge',t)));meta.append(button('Try it ↗',()=>{$('try').classList.add('open');$('try').querySelector('button')?.focus()},'mobile'));main.append(meta);
  const params=el('section');params.append(el('h2','','Parameters'));params.append(op.parameters.length?parameterTable(op):el('p','muted','Nenhum parâmetro documentado.'));main.append(params);
  if(op.requestBody){const body=resolve(spec,op.requestBody),section=el('section');section.append(el('h2','','Request body'),el('p','',body.description||''),contentView(body.content));main.append(section)}
  const section=el('section'),response=el('div'),codes=Object.keys(op.responses||{});section.append(el('h2','','Responses'));const renderResponse=code=>{const r=resolve(spec,op.responses[code]);response.replaceChildren(el('h3','',code+' — '+(r.description||'')),contentView(r.content))};
  if(codes.length){section.append(tabs(codes,renderResponse),response);renderResponse(codes[0])}else section.append(el('p','muted','Nenhuma resposta documentada.'));main.append(section);
}
function render(id){if(!index)return;dispose();active=id;main.replaceChildren();const op=index.operations.find(o=>o.id===id);if(id.startsWith('schema:')){const name=id.slice(7);if(Object.hasOwn(spec.components?.schemas||{},name))main.append(el('div','crumb','API Reference / Schemas'),el('h1','',name),schemaTree(spec,spec.components.schemas[name],name));else main.append(el('p','','Schema não encontrado.'))}else if(op)operationView(op);else overview();
  dispose=mountTry($('try'),spec,op);document.querySelectorAll('[data-id]').forEach(b=>{const on=b.dataset.id===id;b.classList.toggle('active',on);if(on)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});storage.set('last',id);main.scrollTop=0;$('palette').close();if(innerWidth<700)$('sidebar').classList.remove('open');
}
function buildNav(){
  $('nav').replaceChildren();$('schemas').replaceChildren();const fragment=document.createDocumentFragment();
  for(const [tag,ops] of index.groups){const items=el('div');items.hidden=closed.has(tag);const group=button(tag+' ⌄',()=>{items.hidden=!items.hidden;group.setAttribute('aria-expanded',String(!items.hidden));if(items.hidden)closed.add(tag);else closed.delete(tag);storage.set('closed',[...closed])},'group');group.setAttribute('aria-expanded',String(!items.hidden));for(const op of ops){const b=button('',()=>navigate(op.id),'navitem');b.dataset.id=op.id;b.append(el('span','method '+op.method,op.method),el('code','',op.path));items.append(b)}fragment.append(group,items)}$('nav').append(fragment);
  for(const name of index.schemas){const b=button('◇ '+name,()=>navigate('schema:'+name),'navitem');b.dataset.id='schema:'+name;$('schemas').append(b)}
  searchItems=[...index.operations.map(o=>({id:o.id,title:o.method+' '+o.path,search:o.search})),...index.schemas.map(s=>({id:'schema:'+s,title:s+' schema',search:(s+' '+JSON.stringify(spec.components.schemas[s])).toLocaleLowerCase()}))];
}
function search(){const query=$('global-search').value.toLocaleLowerCase().trim();$('results').replaceChildren();const matches=searchItems.filter(item=>item.search.includes(query)).slice(0,80);for(const item of matches){const b=button(item.title,()=>navigate(item.id),'navitem');b.setAttribute('role','option');b.setAttribute('aria-selected','false');$('results').append(b)}if(!matches.length)$('results').append(el('p','','Nenhum resultado encontrado.'))}
function palette(){$('palette').showModal();$('global-search').value='';search();$('global-search').focus()}
$('home').onclick=()=>navigate('intro');$('search').onclick=palette;$('close-palette').onclick=()=>$('palette').close();$('global-search').oninput=search;
$('palette').addEventListener('close',()=>$('search').focus());$('palette').addEventListener('keydown',e=>{const all=[...$('results').querySelectorAll('button')],i=all.indexOf(document.activeElement);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const n=i<0?(e.key==='ArrowDown'?0:all.length-1):(i+(e.key==='ArrowDown'?1:-1)+all.length)%all.length;all[n]?.focus()}if(e.key==='Enter'&&document.activeElement===$('global-search')){e.preventDefault();all[0]?.click()}});
$('menu').onclick=()=>{if(innerWidth<=700){$('sidebar').classList.toggle('open');$('menu').setAttribute('aria-expanded',String($('sidebar').classList.contains('open')))}else{const hidden=$('sidebar').hidden=!$('sidebar').hidden;document.querySelector('.layout').style.gridTemplateColumns=hidden?'minmax(390px,1fr) var(--try-width,390px)':'';$('menu').setAttribute('aria-expanded',String(!hidden));storage.set('sidebarHidden',hidden)}};
const setTheme=dark=>{document.body.classList.toggle('dark',dark);$('theme').setAttribute('aria-pressed',String(dark))};setTheme(storage.get('dark',matchMedia('(prefers-color-scheme:dark)').matches));$('theme').onclick=()=>{const dark=!document.body.classList.contains('dark');setTheme(dark);storage.set('dark',dark)};
if(innerWidth>700 && storage.get('sidebarHidden',false))$('menu').click();
const width=storage.get('width',390);$('width').value=width;const setWidth=v=>document.documentElement.style.setProperty('--try-width',v+'px');setWidth(width);$('width').oninput=e=>{setWidth(e.target.value);storage.set('width',Number(e.target.value))};
window.addEventListener('hashchange',()=>render(selected()));document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('palette').open)palette()}if(e.key==='Escape')$('try').classList.remove('open')});
async function load(){main.replaceChildren(el('div','skeleton'),el('div','skeleton'));try{const response=await fetch(schemaURL,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw new Error('HTTP '+response.status);spec=await response.json();if(!/^3\./.test(spec.openapi||'')||!spec.paths||typeof spec.paths!=='object')throw new Error('Especificação OpenAPI 3.x inválida.');index=indexSpec(spec);$('title').textContent=spec.info?.title || 'Vela API';$('oas').textContent='OpenAPI '+spec.openapi;$('version').textContent=spec.info?.version || '';document.title='Vela Docs — '+(spec.info?.title||'API');$('server-status').textContent='● '+location.host;$('server-status').classList.add('ok');$('open-json').href=schemaURL;buildNav();render(location.hash?selected():'intro')}catch(e){$('server-status').textContent='API unavailable';main.replaceChildren(el('h1','','API unavailable'),el('p','','The local API server could not be reached.'),el('p','error',e.message),button('Retry',load,'primary'))}}
load();
