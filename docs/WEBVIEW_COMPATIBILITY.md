# Compatibilidade WebView

O WebView faz parte do contrato prático do Vela. O framework não promete que qualquer engine antigo execute qualquer biblioteca JavaScript moderna; em vez disso, expõe backend e probes de capabilities para que aplicações possam decidir com evidência.

## Níveis de suporte baseados na CI atual

| Backend / ambiente | Nível | Evidência atual |
|---|---|---|
| Qt6 WebEngine / Linux | Tier 1 para build/runtime smoke | CI instala Qt6/WebEngine, executa doctor, build PyInstaller e `--self-test` do executável |
| pywebview core / Windows | Tier 1 para core, static e build tooling | matriz Windows executa a suíte Python, path handling e Node launcher real |
| WebView interativo / Windows | Tier 2 | contrato Python/JS testado, mas a CI não abre uma sessão gráfica interativa completa |
| GTK/WebKit / Linux | Experimental | adapter continua disponível, mas não participa do smoke gráfico principal desta matriz |
| macOS | Experimental nesta versão | sem runner de validação neste PR |

`Tier 1` não significa que toda biblioteca de terceiros seja compatível com a versão de Chromium/WebKit instalada no computador do usuário.

## Capability API

No frontend:

```js
const caps = await Vela.capabilities()
```

O resultado combina informações nativas com probes reais do engine, por exemplo:

```json
{
  "platform": "win32",
  "webview": "qt",
  "clipboard": true,
  "filePicker": false,
  "pointerEvents": true,
  "canvas": true,
  "webgl": true,
  "webgl2": false,
  "localStorage": true
}
```

`pointerEvents`, `canvas`, `webgl`, `webgl2` e `localStorage` são detectados dentro da WebView; não são inferidos apenas pelo SO.

## Clipboard

Use:

```js
await Vela.platform.clipboard.writeText(text)
```

O caminho preferido é Bridge -> clipboard nativo. O fallback DOM não usa `navigator.clipboard`.

## JavaScript target

O shell do Vela atualmente depende de recursos presentes em engines modernos usados pelos backends suportados, incluindo:

- `async`/`await`;
- optional chaining (`?.`);
- nullish coalescing (`??`);
- `AbortController`;
- `CustomEvent`;
- `PointerEvent` apenas quando o probe reporta suporte.

Bibliotecas da aplicação devem ser empacotadas para o engine efetivamente usado. O Vela ainda não impõe esbuild/Babel nem adiciona Node como runtime de produção. Se um consumidor precisar suportar QtWebEngine antigo, deve gerar um bundle compatível durante o build e conferir `Vela.capabilities()` quando a feature depender do engine.

## Canvas e WebGL

O shell evita `transform`, `filter`, `backdrop-filter`, `contain` e resets globais no ancestral de `#vela-app-root`. Isso reduz interferência de composição em Canvas/WebGL. `requestAnimationFrame`, resize e gestão do contexto continuam sob responsabilidade da aplicação.

## Pointer, stylus e IME

O shell não intercepta globalmente PointerEvent nem desabilita seleção do app. Mouse, touch, pen, `pressure`, `buttons`, keyboard e IME continuam eventos DOM do engine. Hardware específico (Windows Ink/caneta real) precisa de validação em dispositivo físico; a CI não simula hardware de stylus.
