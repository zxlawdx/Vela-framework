# Performance e complexidade

O foco desta refatoração é remover custos assintóticos e trabalho repetido no hot path, não perseguir micro-otimizações.

## Complexidades

| Operação | Complexidade esperada | Observação |
|---|---:|---|
| `Router.resolve(path)` | O(1) médio | dict por path |
| `Router.url_for(name)` | O(1) médio | dict por nome |
| `Router.add(...)` | O(1) médio | validação + dois dicts |
| primeira `get_sidebar_routes()` após mutação | O(R log R) | filtro + sort |
| `get_sidebar_routes()` cache hit | O(S) | cópia defensiva de S itens visíveis |
| `ApiRouter.add_route()` | O(1) médio | dict por `(method, path)` |
| registrar R APIs | O(R) médio | antes era O(R²) por busca linear de duplicatas |
| `ApiRouter.get_route()` | O(1) médio | lookup direto |
| `EventBus.emit()` | O(L) | L listeners do evento |
| template tokenize/parse | O(T) esperado | varredura linear + AST |
| template render | O(T + O) aproximado | T nós visitados + tamanho de output/dados |
| loop template | O(N * B + O) | N itens, B nós do bloco |
| template cache hit | O(stat + render) | AST não é reparseada |
| hot reload sem mudança | O(M) stats | M módulos explicitamente rastreados |
| hot reload com D dirty | O(M + reload(D)) | não percorre/recarrega todo `apps.*` |
| migration discovery | O(M log M) | `glob` + ordenação |

`S`, `R`, `L`, `T`, `O`, `N`, `B`, `M` e `D` representam respectivamente rotas visíveis, rotas, listeners, tamanho/estrutura do template, output, itens de loop, corpo do loop, módulos rastreados e módulos alterados.

## Mudanças relevantes

### API registry

Antes, `ApiRouter.add_route()` percorria a lista inteira para encontrar uma duplicata. Adicionar R rotas fazia aproximadamente `1 + 2 + ... + R`, isto é, O(R²).

Agora o registry é `dict[(method, path)] -> ApiRoute`. O registro total passa a O(R) médio e a substituição da mesma chave preserva sua posição no dict.

### Reflection

`inspect.signature()` e `typing.get_type_hints()` são calculados na criação de `ApiRoute`, não em cada request. O adapter HTTP compila o binder uma vez quando registra a rota no Bottle.

### Templates

O renderer antigo fazia múltiplos `.replace()` e concatenava strings dentro de loops. O engine atual compila uma AST e acumula output em `list.append()` + `''.join()`.

Templates em arquivo usam dois caches limitados a 256 entradas: leitura e `CompiledTemplate`. `mtime_ns` e tamanho fazem invalidação automática quando o arquivo muda.

### Hot reload

Navegação não executa mais reload global de `sys.modules`. `HotReloadManager` mantém um registry pequeno de módulos do app e compara `mtime_ns`; somente módulos dirty são recarregados.

## Benchmarks

`benchmarks/bench_core.py` mede mean, median, p95 e p99 para lookup do page router, registro de 10/100/1000 APIs, parse/render/loop/cache de template e dispatch WSGI do Bottle.

```bash
python benchmarks/bench_core.py
```

Os números não são gates de CI porque runners compartilhados têm ruído. Regressões de ordem de grandeza devem ser investigadas. Comparações externas só devem ser publicadas com ambiente e carga equivalentes.

## Cache e memória

O cache de template é bounded (`maxsize=256`) e possui `clear_template_cache()` para testes/hot reload. Router/API registries substituem chaves existentes em vez de acumular duplicatas. EventBus não adiciona o mesmo listener duas vezes e o shell instala o handler delegado de links uma única vez.
