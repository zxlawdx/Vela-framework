# Modelo de segurança do Vela

## Princípio

Aplicação desktop não significa input confiável. A WebView executa HTML/JavaScript e possui uma ponte para Python; portanto um valor transformado acidentalmente em script pode alcançar capacidades maiores que em XSS de navegador comum.

## Trust boundaries

```text
[Filesystem / plugins / app Python] -- trusted application code
              |
              v
       [Template source] ----------- trusted code
              |
     context values ---------------- UNTRUSTED DATA
              |
              v
       [Template renderer]
       autoescape by default
              |
              v
        [Rendered HTML]
              |
              v
           [WebView]
              |
       JS inputs / fetch ------------ UNTRUSTED DATA
          |             |
          v             v
       [Bridge]     [Local HTTP API]
          |             |
          +------ validation --------+
                        |
                        v
                  [Application Python]
```

## Templates e XSS

`{{ valor }}` usa escaping equivalente a `html.escape(str(value), quote=True)`. São protegidos `&`, `<`, `>`, `"` e `'`. A mesma regra vale para valores em loops.

HTML cru exige intenção explícita:

```python
from vela.template_engine import mark_safe

context = {"content": mark_safe("<strong>confiável</strong>")}
```

`mark_safe()` é uma declaração de confiança, não um sanitizador. Nunca passe para ele HTML originado de usuário, rede, banco ou dispositivo sem sanitização independente adequada.

## Scripts do shell

O Vela preserva scripts presentes em templates de aplicação por compatibilidade. O modelo é: template/JS do projeto = código confiável; valores de contexto = dados escapados; `SafeHTML` = opt-in consciente para HTML confiável; páginas internas 404/500 = não executam scripts; `RouteResult.ok=False` = shell renderiza a mensagem, mas não chama o executor de scripts.

Assim, o uso de `innerHTML` permanece restrito a HTML produzido a partir de template confiável + dados autoescapados. Uma política CSP mais restritiva pode ser adicionada no futuro, mas remover scripts inline agora quebraria aplicações existentes.

## Erros

Em produção (`debug=False`/`VELA_PRODUCTION=1`), exceptions de views e API não são retornadas ao usuário. O frontend recebe uma mensagem genérica e um identificador como `VELA-E-a1b2c3d4`. Traceback e mensagem completa ficam nos logs.

Em debug, detalhes podem aparecer para desenvolvimento, mas são escapados antes de entrar em HTML.

## Paths de template e static

Templates e assets são resolvidos por `Path.resolve()` e validados contra roots permitidas. São rejeitados caminhos absolutos fora da root, `../`, symlinks que resolvam fora da root e NUL em static paths. A rota Bottle de estáticos faz a validação antes de delegar para `static_file()`.

## Bridge Python <-> JavaScript

Considere todo argumento vindo de `window.pywebview.api` não confiável. `BaseBridge` valida paths, tamanho e forma dos payloads antes do routing.

Métodos auxiliares internos usam prefixo `_`. O pywebview 6.2.x documenta que métodos de `js_api` iniciados por underscore não são expostos. O Vela ainda evita colocar operações sensíveis desnecessárias na bridge base.

Aplicações que estendem `BaseBridge` devem validar IDs, paths, nomes de arquivos e conteúdo recebido. Não monte comandos shell com valores da WebView.

## API HTTP local

O default é `127.0.0.1`. Bind não-loopback (`0.0.0.0`, IP LAN etc.) falha, a menos que `API['allow_remote'] = True` seja definido explicitamente.

CORS `*` é permitido automaticamente somente em debug + loopback. Em bind remoto, wildcard é rejeitado; configure `cors_origins` explicitamente.

O body possui limite padrão de 1 MiB (`max_body_size`) e é rejeitado com HTTP 413 antes de parsing JSON quando o tamanho declarado/observado excede o limite.

### Token local

Esta refatoração não adiciona token obrigatório ao HTTP local porque aplicações existentes fazem `fetch('/api/...')` diretamente e a introdução silenciosa de um header obrigatório seria breaking change amplo. O hardening equivalente nesta etapa é bind loopback por padrão, exposição remota com opt-in, wildcard CORS remoto proibido, body limitado, erros internos redigidos e binder explícito.

Para APIs deliberadamente remotas, autenticação da aplicação continua necessária. Um token de sessão do shell pode ser introduzido em versão futura com depreciação/migração de `fetch` legado.

## Plugins

Plugins e entry points executam Python arbitrário no processo. Eles pertencem ao boundary de código confiável. O Vela não os executa espontaneamente; o fluxo de build precisa optar por `apply_build_hooks()`. Erros identificam plugin e hook e não são silenciosamente ignorados.

## SQLite

Migrations SQL são código confiável do projeto. Nomes e hashes do histórico são dados e usam parâmetros SQL. A integridade do histórico continua protegida por SHA-256.

## Checklist para aplicações

- Não use `mark_safe()` em dados externos.
- Não exponha `0.0.0.0` sem necessidade e autenticação.
- Valide todos os argumentos de métodos bridge customizados.
- Prefira `Request`/`Response` em handlers novos.
- Não execute subprocess com `shell=True` e input externo.
- Trate plugins como código com os mesmos privilégios do app.
- Use `VELA_PRODUCTION=1` em builds distribuídos.
