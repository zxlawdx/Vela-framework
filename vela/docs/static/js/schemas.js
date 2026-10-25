// SPDX-License-Identifier: MPL-2.0
import {resolve} from './openapi.js';
import {el} from './dom.js';
export function schemaTree(spec,raw={},name='object',required=false,seen=new Set(),depth=0) {
  const node=el('details','schema-node');node.open=depth===0;
  const circular=raw.$ref && seen.has(raw.$ref),s=resolve(spec,raw),title=el('summary');
  title.append(el('span','',name+'  '),el('span','muted',(raw.$ref?.split('/').pop() || s.type || 'schema')+'  '),el('span',required?'req':'muted',required?'required':'optional'));
  node.append(title);
  if(circular || depth>12){node.append(el('p','muted','Referência circular / limite de expansão: '+(raw.$ref||name)));return node}
  const next=new Set(seen);if(raw.$ref)next.add(raw.$ref);
  if(s.description) node.append(el('p','',s.description));
  for(const key of ['nullable','minimum','maximum','minLength','maxLength','minItems','maxItems','pattern','enum','default','example','format','readOnly','writeOnly','additionalProperties']) {
    if(s[key]!==undefined)node.append(el('div','muted',key+': '+JSON.stringify(s[key])));
  }
  for(const [key,value] of Object.entries(s.properties || {}))node.append(schemaTree(spec,value,key,(s.required||[]).includes(key),next,depth+1));
  if(s.items)node.append(schemaTree(spec,s.items,'items',false,next,depth+1));
  for(const union of ['oneOf','anyOf','allOf'])for(const [i,item] of (s[union]||[]).entries())node.append(schemaTree(spec,item,union+' '+(i+1),false,next,depth+1));
  return node;
}
