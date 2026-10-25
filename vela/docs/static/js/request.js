// SPDX-License-Identifier: MPL-2.0
export function serverUrl(server,base) {
  let value=server?.url || '/';
  for(const [k,v] of Object.entries(server?.variables || {}))value=value.replaceAll('{'+k+'}',v.default || '');
  return new URL(value,base).href;
}
export function buildRequest(op,values,base) {
  let path=op.path;const headers={},query=new URLSearchParams();
  for(const p of op.parameters || []) {
    const key=p.in+':'+p.name, value=values[key] ?? '';
    if(p.required && value==='')throw new Error('Parâmetro obrigatório: '+p.name);
    if(value==='')continue;
    if(p.in==='path')path=path.replaceAll('{'+p.name+'}',encodeURIComponent(value));
    if(p.in==='query')query.append(p.name,value);
    if(p.in==='header')headers[p.name]=value;
  }
  if(/\{[^}]+\}/.test(path))throw new Error('Preencha todos os parâmetros de path.');
  const root=new URL(base),url=new URL(root.href.replace(/\/$/,'')+'/'+path.replace(/^\//,''));
  if(!['http:','https:'].includes(url.protocol))throw new Error('O servidor deve usar HTTP ou HTTPS.');
  for(const [k,v] of query)url.searchParams.append(k,v);
  const options={method:op.method,headers,credentials:'same-origin'};
  if(values.body!==undefined && !['GET','HEAD'].includes(op.method)) {
    if(values.body==='') {if(op.requestBody?.required)throw new Error('O corpo da requisição é obrigatório.');}
    else {if((values.mediaType||'application/json').includes('json'))JSON.parse(values.body);options.body=values.body;headers['Content-Type']=values.mediaType || 'application/json';}
  }
  return {url:url.href,options};
}
export async function execute(request,signal) {
  const start=performance.now();const response=await fetch(request.url,{...request.options,signal});
  const buffer=await response.arrayBuffer(),raw=new TextDecoder().decode(buffer);let body=raw;
  try{body=JSON.parse(raw)}catch{}
  return {status:response.status,statusText:response.statusText,time:performance.now()-start,size:buffer.byteLength,headers:Object.fromEntries(response.headers),raw,body};
}
