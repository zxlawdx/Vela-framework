import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../vela/templates/project/apps/home/static/starter.js',import.meta.url),'utf8');
function ui(api,storageFails=false){
  const nodes=new Map();
  const node=()=>({dataset:{},disabled:false,hidden:false,textContent:'',handlers:{},attrs:{},classes:new Set(),
    addEventListener(name,fn){this.handlers[name]=fn},setAttribute(name,value){this.attrs[name]=value},
    get classList(){const classes=this.classes;return {toggle(k,v){if(v===undefined)v=!classes.has(k);v?classes.add(k):classes.delete(k)},contains:k=>classes.has(k),add:k=>classes.add(k),remove:k=>classes.delete(k)}}});
  const root=node();root.querySelector=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id)};root.querySelectorAll=()=>[];
  const window={pywebview:api?{api}:undefined,addEventListener(){}};
  const store=new Map();
  const context={window,document:{getElementById:()=>root},AbortController,console:{error(){}},
    localStorage:{getItem(k){if(storageFails)throw Error('blocked');return store.get(k)},setItem(k,v){if(storageFails)throw Error('blocked');store.set(k,v)}},setTimeout,clearTimeout};
  vm.runInNewContext(source,context);
  return {root,nodes,window,store};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('only Python-produced increments update the visible count',async()=>{
  const calls=[],app=ui({ping:async()=> 'pong',increment_counter:async value=>{calls.push(value);return value+1}});
  await tick();assert.equal(app.nodes.get('#runtime-status').textContent,'Python conectado');
  await app.nodes.get('#increment-button').handlers.click();assert.deepEqual(calls,[0]);assert.equal(app.nodes.get('#counter-value').textContent,'1');
  await app.nodes.get('#increment-button').handlers.click();assert.deepEqual(calls,[0,1]);assert.equal(app.nodes.get('#counter-value').textContent,'2');
  app.window.VelaPage.beforeUnmount();
});
test('missing runtime does not create a successful local fallback',async()=>{
  const app=ui();await tick();assert.equal(app.nodes.get('#increment-button').disabled,true);assert.equal(app.nodes.get('#runtime-status').textContent,'Python indisponível');assert.equal(app.nodes.get('#retry-bridge').hidden,false);assert.match(app.nodes.get('#counter-error').textContent,/runtime desktop/);app.window.VelaPage.beforeUnmount();
});
test('backend errors preserve the counter and enable retry',async()=>{
  const app=ui({ping:async()=> 'pong',increment_counter:async()=>{throw Error('Python failed')}});await tick();await app.nodes.get('#increment-button').handlers.click();assert.equal(app.nodes.get('#counter-error').textContent,'Python failed');assert.equal(app.nodes.get('#increment-button').disabled,true);assert.equal(app.nodes.has('#counter-value'),false);await app.nodes.get('#retry-bridge').handlers.click();assert.equal(app.nodes.get('#increment-button').disabled,false);app.window.VelaPage.beforeUnmount();
});
test('themes toggle and storage failures do not break bridge setup',async()=>{
  const app=ui({ping:async()=> 'pong'},true);await tick();app.nodes.get('#theme-toggle').handlers.click();assert.equal(app.root.classes.has('dark'),true);assert.equal(app.nodes.get('#theme-toggle').attrs['aria-pressed'],'true');assert.equal(app.nodes.get('#runtime-status').textContent,'Python conectado');app.window.VelaPage.beforeUnmount();
});
