// SPDX-License-Identifier: MPL-2.0
import {resolve,mediaExample} from './openapi.js';
import {el,button,codebox,tabs,field} from './dom.js';
import {serverUrl,buildRequest,execute} from './request.js';
import {snippets} from './snippets.js';
export function mountTry(root,spec,op) {
  root.replaceChildren();if(!op){root.append(el('h2','','Explore sua API'),el('p','','Selecione um endpoint para montar e enviar uma requisição real.'));return ()=>{}}
  const lifecycle=new AbortController(),values={},title=el('div','trytitle','Try it'),requestPanel=el('div'),codePanel=el('div'),result=el('div'),url=el('code','url'),error=el('p','error');
  let base,language='curl';codePanel.hidden=true;error.setAttribute('role','alert');
  title.append(button('×',()=>root.classList.remove('open'),'mobile'));
  const server=el('select');server.setAttribute('aria-label','Servidor');
  for(const s of op.servers){const option=el('option','',s.description||s.url);try{option.value=serverUrl(s,location.href)}catch{option.value=''}server.append(option)}base=server.value;
  const update=()=>{try{const req=buildRequest(op,values,base);url.textContent=op.method+' '+req.url;codePanel.replaceChildren(tabs(['curl','Python','JavaScript'],l=>{language=l;update()},language),codebox(snippets(req)[language],language,true));error.textContent=''}catch(e){error.textContent=e.message;url.textContent=op.method+' '+op.path;codePanel.replaceChildren(el('p','error',e.message))}};
  server.addEventListener('change',()=>{base=server.value;update()});requestPanel.append(field('Server',server));
  for(const p of op.parameters){const s=resolve(spec,p.schema),key=p.in+':'+p.name;
    if(p.in==='cookie'){requestPanel.append(el('p','muted','Cookie '+p.name+': gerenciado pelo navegador; não pode ser definido como header.'));continue}
    const input=s.enum ? el('select') : el('input');input.name=key;
    if(s.enum)for(const v of ['',...s.enum]){const opt=el('option','',String(v));opt.value=String(v);input.append(opt)}
    const initial=p.example??s.example??s.default??'';input.value=String(initial);values[key]=input.value;input.required=!!p.required;input.addEventListener('input',()=>{values[key]=input.value;update()});
    requestPanel.append(field(p.name+' · '+p.in+(p.required?' · required':''),input));
  }
  const rb=resolve(spec,op.requestBody),content=rb.content || {};op={...op,requestBody:rb};
  if(Object.keys(content).length && !['GET','HEAD'].includes(op.method)){
    const media=el('select'),body=el('textarea');for(const type of Object.keys(content)){const opt=el('option','',type);opt.value=type;media.append(opt)}
    const change=()=>{values.mediaType=media.value;const value=mediaExample(spec,content[media.value]);body.value=media.value.includes('json')?JSON.stringify(value,null,2):typeof value==='string'?value:'';values.body=body.value;update()};media.addEventListener('change',change);body.addEventListener('input',()=>{values.body=body.value;update()});requestPanel.append(field('Content type',media),field('Request body'+(rb.required?' · required':''),body));change();
  }
  const send=button('Send Request ↗',async()=>{
    const controller=new AbortController();
    const abort=()=>controller.abort();lifecycle.signal.addEventListener('abort',abort,{once:true});
    try{const request=buildRequest(op,values,base);send.disabled=true;send.textContent='Sending…';root.setAttribute('aria-busy','true');error.textContent='';
      const timeout=setTimeout(()=>controller.abort(),30000);let response;try{response=await execute(request,controller.signal)}finally{clearTimeout(timeout)}
      if(controller.signal.aborted)return;
      const meta=el('div','responsemeta');meta.append(el('span',response.status<400?'ok':'error',response.status+' '+response.statusText),el('span','',response.time.toFixed(1)+' ms'),el('span','',response.size+' B'));
      const output=el('div'),render=t=>output.replaceChildren(codebox(t==='Response'?response.body:t==='Headers'?response.headers:response.raw,t==='Headers'?'Headers':response.headers['content-type']||'Response',t==='Raw'||(t==='Response'&&typeof response.body==='string')));
      result.replaceChildren(meta,tabs(['Response','Headers','Raw'],render),output);render('Response');
    }catch(e){if(root.isConnected)error.textContent=e.name==='AbortError'?'Requisição cancelada ou tempo limite excedido.':e.message}finally{lifecycle.signal.removeEventListener('abort',abort);send.disabled=false;send.textContent='Send Request ↗';root.setAttribute('aria-busy','false')}
  },'primary');requestPanel.append(send);
  const switchTab=t=>{requestPanel.hidden=t!=='Request';codePanel.hidden=t!=='Code';update()};
  root.append(title,tabs(['Request','Code'],switchTab),url,requestPanel,codePanel,error,el('h2','','Response'),result,el('p','tiny','Requisições reais. Cookies e CORS seguem as regras do navegador.'));
  update();return ()=>lifecycle.abort();
}
