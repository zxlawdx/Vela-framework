// SPDX-License-Identifier: MPL-2.0
export const methods = ['get','post','put','patch','delete','head','options','trace'];
export function resolve(spec, node, seen = new Set()) {
  if (!node?.$ref) return node || {};
  const ref = node.$ref;
  if (!ref.startsWith('#/') || seen.has(ref)) return {description: 'Referência externa ou circular: ' + ref};
  const value = ref.slice(2).split('/').reduce((o,k) => o?.[k.replace(/~1/g,'/').replace(/~0/g,'~')],spec);
  return {...resolve(spec,value,new Set([...seen,ref])),...Object.fromEntries(Object.entries(node).filter(([k])=>k!=='$ref'))};
}
export function indexSpec(spec) {
  const operations = [], groups = new Map(), schemas = Object.keys(spec.components?.schemas || {});
  for (const [path, raw] of Object.entries(spec.paths || {})) {
    const item = resolve(spec,raw);
    for (const method of methods) {
      if (!item[method]) continue;
      const op = resolve(spec,item[method]);
      const parameters = new Map();
      for (const p of [...(item.parameters || []),...(op.parameters || [])]) {
        const value = resolve(spec,p); parameters.set(value.in+':'+value.name,value);
      }
      const entry = {...op,method:method.toUpperCase(),path,parameters:[...parameters.values()],
        servers:op.servers || item.servers || spec.servers || [{url:'/'}],
        id:method+':'+path, tags:op.tags?.length ? op.tags : ['API']};
      entry.search = [path,method,op.operationId,op.summary,op.description,...entry.tags].join(' ').toLocaleLowerCase();
      operations.push(entry);
      for (const tag of entry.tags) { if (!groups.has(tag)) groups.set(tag,[]); groups.get(tag).push(entry); }
    }
  }
  return {operations,groups,schemas};
}
export function example(spec, raw, seen = new Set(), depth = 0) {
  if (!raw || depth > 8 || (raw.$ref && seen.has(raw.$ref))) return null;
  const next = new Set(seen); if(raw.$ref) next.add(raw.$ref);
  const s = resolve(spec,raw);
  if (s.example !== undefined) return s.example;
  if (s.default !== undefined) return s.default;
  if (s.enum?.length) return s.enum[0];
  if (s.oneOf || s.anyOf) return example(spec,(s.oneOf || s.anyOf)[0],next,depth+1);
  if (s.allOf) return Object.assign({},...s.allOf.map(x=>example(spec,x,next,depth+1)||{}));
  if (s.type==='array') return [example(spec,s.items,next,depth+1)];
  if (s.properties || s.type==='object') return Object.fromEntries(Object.entries(s.properties || {}).map(([k,v])=>[k,example(spec,v,next,depth+1)]));
  if (s.type==='integer' || s.type==='number') return s.minimum ?? 1;
  if (s.type==='boolean') return true;
  return s.type==='string' ? '' : null;
}
export function mediaExample(spec,media) {
  if (media?.example !== undefined) return media.example;
  const first = Object.values(media?.examples || {})[0];
  return first ? resolve(spec,first).value ?? null : example(spec,media?.schema);
}
