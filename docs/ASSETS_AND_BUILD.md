# Assets e build

O Vela separa quatro conceitos que antes podiam ser confundidos em aplicações consumidoras.

## Diretórios

```text
apps/<app>/static/   source static do app
staticfiles/         collected static usado pelo runtime
.vela-build/         staging/workspace temporário do builder
 dist/               artefato final distribuível
```

`.vela-build` nunca deve ser usado como runtime static root. `staticfiles` não é diretório temporário de PyInstaller.

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
