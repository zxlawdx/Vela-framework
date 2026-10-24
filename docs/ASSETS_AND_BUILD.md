# Assets e build

O Vela separa quatro conceitos que antes podiam ser confundidos em aplicações consumidoras.

## Diretórios

```text
apps/<app>/static/   source static do app
staticfiles/         collected static usado pelo runtime
.vela-build/         staging/workspace temporário do builder
dist/                artefato final distribuível
```

`.vela-build` nunca deve ser usado como runtime static root. `staticfiles` não é diretório temporário de PyInstaller.

## `collectstatic` como entrypoint único

Projetos que precisam preparar bundles JS, CSS ou outros assets antes da coleta podem declarar o pipeline em `config/settings.py`:

```python
ASSETS = {
    "node": {
        "install": "ci",                 # ou "install"
        "scripts": ["build:vendor"],
    },
    "hooks": ["tools.build_css:main"],
    "tailwind": False,                   # hook do projeto já gerencia Tailwind
}
```

Com isso, o fluxo local passa a ser apenas:

```bash
python manage.py collectstatic
```

A ordem é:

1. validar Node.js/npm quando o projeto declarar pipeline Node;
2. validar `node_modules` com `npm ls --depth=0`;
3. se dependências locais estiverem ausentes/inconsistentes, pedir autorização para executar `npm ci` ou `npm install`;
4. executar os scripts npm declarados;
5. executar hooks Python declarados como `modulo:callable`;
6. executar o pipeline Tailwind padrão quando habilitado;
7. copiar `apps/*/static` para `staticfiles`;
8. gerar `manifest.json` SHA-256.

O Vela **não instala Node.js/npm nem usa sudo/apt/choco/winget**. Dependências de sistema exigem instalação explícita pelo usuário. O framework só pode instalar dependências npm locais do próprio projeto após consentimento.

Em terminal interativo, a confirmação é solicitada automaticamente:

```text
Dependências JavaScript ausentes ou inconsistentes. Executar `npm ci` agora? [S/n]
```

Para CI ou automação não interativa, use o mesmo comando com autorização explícita:

```bash
python manage.py collectstatic --yes
```

Para proibir qualquer instalação automática e apenas diagnosticar o estado atual:

```bash
python manage.py collectstatic --no-install
```

Nesse modo a execução falha com a ação necessária, sem modificar `node_modules`.

### Segurança dos hooks

`ASSETS` pertence ao próprio projeto e é tratado como código confiável do projeto. Scripts npm e hooks Python não são descobertos ou executados por heurística: precisam estar explicitamente declarados em `config.settings.ASSETS`.

Todos os subprocessos continuam usando argv em lista e `shell=False`.

## URL de runtime

Aplicações não devem concatenar `/static/` nem `/__vela__/static/`. Use o contrato:

```python
from vela.static import StaticResolver

resolver = StaticResolver.for_project(".")
url = resolver.url("css/app.css")
```

Em templates:

```html
<link rel="stylesheet" href="{{ static('css/app.css') }}">
```

O namespace canônico é interno ao resolver. `/static/...` permanece apenas como alias de compatibilidade no servidor.

## Segurança de path

O resolver rejeita:

- `../` e traversal equivalente;
- paths absolutos POSIX;
- drives absolutos Windows;
- symlinks que escapem da collected root.

## Manifest

`collectstatic` gera `staticfiles/manifest.json` com SHA-256. O hash permite detectar asset ausente/stale e torna o conteúdo verificável independentemente de timestamp.

## Verificação

Global:

```bash
vela assets verify
```

No projeto:

```bash
python manage.py assets verify
```

A verificação checa shell local/offline, `staticfiles`, manifest, hashes e assets source que deveriam ter sido coletados. Mensagens indicam o arquivo ausente/divergente.

## Windows e Node tools

O resolver de subprocess procura executáveis por plataforma. Em Windows, ferramentas do `node_modules/.bin` priorizam `.cmd`, `.exe` ou `.bat` e nunca executam diretamente o shim POSIX sem extensão. Em POSIX, usa o shim executável normal.

Subprocesses de Node/Tailwind usam argv em lista e `shell=False`.

A CI Windows instala Node de verdade, resolve `npx.cmd` e executa `npx --version` sem mock, além de executar um `collectstatic` real.

## Offline mode

O shell de produção não depende de Tailwind CDN, Google Fonts ou JS CDN. Tailwind é uma etapa opcional de build/collectstatic; Node não é runtime obrigatório do aplicativo final.

## Build report

`python manage.py buildapp` escreve `dist/build-report.json` com informações reproduzíveis de Python, Vela, plataforma, backend, apps, hidden imports conhecidos, assets, entrypoint e warnings.

PyInstaller continua coletando recursivamente `apps` e `config`, preservando compatibilidade com projetos legados de registro dinâmico. O `AppConfig` é o contrato explícito para evoluir resources/hidden imports sem depender de imports manuais obscuros.
