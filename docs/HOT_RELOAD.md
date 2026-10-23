# Hot reload e estado persistente

Hot reload é ferramenta de desenvolvimento, não mecanismo de lifecycle de serviços. Aplicações que mantêm sessão HTTP autenticada, SSH, provider de hardware ou cache stateful não podem ter esses objetos recriados a cada navegação.

## Regra

O Vela não faz reload de `apps.*` inteiro. O `HotReloadManager` observa módulos explicitamente classificados pelo manifesto da aplicação.

```python
from vela.apps import AppConfig

class AccessConfig(AppConfig):
    def __init__(self):
        super().__init__(
            name="access",
            module="apps.access",
            reloadable_modules=("apps.access.views",),
            persistent_modules=(
                "apps.access.services",
                "apps.access.providers",
                "apps.access.sessions",
            ),
        )
```

## Reloadable

Use para código de apresentação que pode ser substituído sem perder estado externo:

- views;
- composição de página;
- helpers puramente funcionais de UI.

Quando o arquivo muda, somente o módulo dirty é recarregado. Router/ApiRouter recebem callbacks para atualizar referências quando aplicável.

## Persistent

Use para objetos cujo identity/lifetime não deve depender de uma navegação:

- HTTP sessions autenticadas;
- SSH clients;
- providers de dispositivo;
- caches de conexão;
- managers com threads próprias.

Prefixes persistentes são rastreados como não-reloadable e não são reinstanciados pelo manager.

## Decorators/API

Módulos de API e URLs são persistentes por padrão. Isso evita executar decorators repetidamente e duplicar registries. `register_app()` importa o API module oficialmente dentro do router app-scoped; não é necessário import manual em `config/wsgi.py`.

## Produção

`VELA_PRODUCTION=1` desabilita hot reload completamente.

## Limitações

- hot reload não migra estado entre versões incompatíveis de classes;
- dependências importadas internamente por uma view só são recarregadas se estiverem classificadas e dirty;
- serviços persistentes ainda precisam de shutdown explícito quando possuem recursos próprios;
- páginas DOM persistentes ainda não são um render mode oficial; o modo atual é replace + lifecycle/AbortController.
