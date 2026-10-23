# Modelo de segurança do Vela

Aplicação desktop não implica input confiável. A WebView executa HTML/JavaScript e possui uma ponte para Python; por isso o Vela trata template data, inputs da Bridge, HTTP local e paths como boundaries explícitos.

## Trust boundaries

```text
[Application Python / plugins] ---- trusted code
              |
       [Template source] ---------- trusted code
              |
       context values ------------- untrusted data
              |
       [Template renderer]
       autoescape by default
              |
        [Rendered HTML]
              |
           [WebView]
          /         \
         v           v
 [Bridge inputs]  [HTTP requests] -- untrusted data
         \           /
          validation
              |
      [Application Python]
              |
         [filesystem]
```

## Templates e HTML

`{{ value }}` usa escaping equivalente a `html.escape(str(value), quote=True)`, inclusive em loops. `&`, `<`, `>`, `"` e `'` são protegidos.

HTML cru requer intenção explícita:

```python
from vela.template_engine import mark_safe

content = mark_safe("<strong>trusted application HTML</strong>")
```

`mark_safe()` não sanitiza. Não o use com conteúdo vindo de usuário, dispositivo, rede ou banco sem sanitização adequada.

## Scripts de páginas

Scripts pertencentes ao template da aplicação são considerados código confiável e continuam suportados por compatibilidade. O shell só os reativa em `RouteResult.ok=True`; páginas internas 404/500 não executam scripts da resposta. A substituição de página remove o DOM anterior, e o lifecycle fornece `AbortSignal` para cleanup de fetch/timers/observers.

CSP/nonces mais restritivos continuam uma evolução futura porque remover inline scripts agora quebraria aplicações existentes.

## Shell e DOM

O CSS do Vela fica namespaceado sob `.vela-shell`. O framework não aplica `user-select: none` global nem regras globais para `dialog`, `canvas`, `button`, `main`, `contenteditable` ou `.textLayer`. Isso também é uma proteção contra mudanças de comportamento inesperadas em interfaces com edição/seleção.

## Static/filesystem

`StaticResolver` normaliza paths e rejeita `../`, paths absolutos, drives absolutos do Windows e symlink escape. Templates seguem roots permitidas equivalentes. O namespace HTTP interno de static não deve ser construído manualmente por aplicações; use `static()`/`{{ static(...) }}`.

## Bridge JavaScript -> Python

Todo argumento recebido por `BaseBridge` é não confiável. A facade valida tipos e limites antes de navegar, emitir eventos ou escrever no clipboard. Helpers internos não fazem parte do contrato público.

Extensões de Bridge implementadas por apps devem validar IDs, filenames, paths e JSON e nunca interpolar input JS em shell commands.

## Clipboard

`Vela.platform.clipboard.writeText()` usa primeiro `clipboard_write_text` da Bridge. No Windows a implementação nativa usa a API Unicode do sistema; macOS/Linux usam ferramentas nativas disponíveis com `subprocess.run([...], shell=False)`. Se a capability nativa não existir, o shell usa fallback DOM baseado em `execCommand('copy')`.

O framework não chama `navigator.clipboard`, evitando depender de permissões/implementações instáveis do engine WebView.

## HTTP

O default é loopback. Bind não-loopback exige `allow_remote=True`. CORS wildcard remoto é rejeitado. O body tem limite configurável e exceder o limite retorna 413 antes do processamento da aplicação.

Erros em produção são redigidos e recebem identificador `VELA-E-*`; traceback permanece em log. A forma de erro é:

```json
{
  "ok": false,
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

Um token HTTP obrigatório não foi introduzido nesta etapa porque quebraria consumidores existentes que fazem fetch local sem header. APIs deliberadamente remotas continuam responsáveis por autenticação da aplicação.

## Dynamic imports

`ModuleNotFoundError` só é tratado como módulo opcional ausente quando `exc.name` corresponde ao target (ou pacote pai do target). Dependência interna quebrada é propagada, inclusive em settings, apps e CLI.

## Plugins

Plugins executam Python com os privilégios do processo e pertencem ao boundary de código confiável. O Vela não tenta sandboxar plugins.

## Checklist

- use `mark_safe()` somente em HTML confiável;
- mantenha API em loopback quando não houver necessidade remota;
- valide inputs de Bridges customizadas;
- use `StaticResolver`/`static()` em vez de concatenar paths/URLs;
- mantenha providers/sessions stateful em módulos `persistent_modules`;
- use `VELA_PRODUCTION=1` em builds distribuídos;
- não use `shell=True` com input externo.
