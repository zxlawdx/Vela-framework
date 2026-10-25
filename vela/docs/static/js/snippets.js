// SPDX-License-Identifier: MPL-2.0
const quote=s=>"'"+String(s).replaceAll("'","'\\''")+"'";
export function snippets({url,options}) {
  const {method,headers,body}=options;
  const curl=['curl -X '+method+' '+quote(url),...Object.entries(headers).map(([k,v])=>'-H '+quote(k+': '+v)),...(body!==undefined?['--data-raw '+quote(body)]:[])].join(' \\\n  ');
  const python='import requests\n\nresponse = requests.request(\n    '+JSON.stringify(method)+',\n    '+JSON.stringify(url)+',\n    headers='+JSON.stringify(headers,null,4)+(body!==undefined?',\n    data='+JSON.stringify(body)+'.encode("utf-8")':'')+'\n)\nprint(response.status_code)\nprint(response.text)';
  const javascript='const response = await fetch('+JSON.stringify(url)+', '+JSON.stringify({method,headers,...(body!==undefined?{body}:{})},null,2)+');\n\nconsole.log(response.status);\nconsole.log(await response.text());';
  return {curl,Python:python,JavaScript:javascript};
}
