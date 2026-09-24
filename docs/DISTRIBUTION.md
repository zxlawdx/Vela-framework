# Distribuição de aplicações Vela (0.2)

## Fluxo gráfico: assistente de instalação

Na **raiz do projeto**, instale o Vela com as ferramentas opcionais de
compilação. Em Linux Mint/Ubuntu:

~~~bash
sudo apt update
sudo apt install -y python3-tk libgl1 libegl1 libnss3 libgbm1 \
    libxcb-cursor0 libxkbcommon-x11-0
python -m pip install "git+https://github.com/zxlawdx/Vela-framework.git"
python -m pip install "PyInstaller>=6.16,<7" "PyQt6>=6.8,<7" \
    "PyQt6-WebEngine>=6.8,<7" "qtpy>=2.4,<3"
python manage.py init-process:instalation
~~~

Também é aceito o alias com grafia inglesa corrigida
`init-process:installation` ou `buildapp --wizard`.

O assistente **Next/Next** oferece quatro telas:

1. Identifica o projeto e o sistema operacional atual.
2. Escolhe backend Qt/GTK, ícone e modo de instalação.
3. Diagnostica dependências; solicita consentimento **separado** para
   instalar pacotes. O Polkit solicita autorização administrativa para apt.
4. Compila; **só instala depois de confirmação adicional**.

Compilar não usa `sudo`. A instalação padrão do Linux é por usuário
(sem privilégios administrativos). O Vela não vê nem armazena sua senha.
Em Linux, o Tkinter precisa estar disponível antes de abrir o wizard;
alternativamente rode `python manage.py doctor --fix` no terminal.

## Fluxo completo por terminal

~~~bash
python manage.py doctor --gui qt6
python manage.py doctor --gui qt6 --fix   # confirmação antes de alterar o SO
python manage.py buildapp --dry-run
python manage.py buildapp --gui qt6 --icon assets/logo.png --installer
python manage.py installapp              # instala build local do usuário
python manage.py makeworkflow            # gera Github Actions para outros SOs
~~~

Outras opções: `--output dist`, `--tailwind` (compila CSS para uso offline),
`--plugins` (executa hooks de build de pacotes confiáveis) e `--wizard`.

O build gera `dist/<nome>/` contendo o executável, diretórios da
aplicação, manifesto `.vela-app.json`, script `Instalar.sh` (Linux) ou
`Instalar.cmd` (Windows) quando `--installer` foi solicitado, além de um
ZIP versionado em `dist/` e seu arquivo `.zip.sha256`.

### Ícone, nome e extensões

No `config/settings.py`:

~~~python
APP_TITLE = "DFD Studio"
APP_VERSION = "0.2.0"
APP_ICON = "assets/logo.png"
APP_AUTHOR = "Meu nome"
APP_DESCRIPTION = "Editor visual de diagramas"
APP_FILE_EXTENSIONS = [".dfd.json"]
~~~

Windows requer ícone `.ico` para o executável; macOS, `.icns`; Linux
aceita `.png` para janela e atalho. O ícone é passado ao
`webview.start(icon=...)`, quando suportado.

### Instalação

- Linux usuário: copia para `~/.local/share/vela-apps/<app>`, registra
  `.desktop` em `~/.local/share/applications/` e tipos MIME opcionais.
  A partir do menu, você pode **fixar manualmente** o app no dock/barra;
  forçar esse comportamento não é confiável nem apropriado.
- Linux todos os usuários: `installapp --scope system` pede elevação
  via Polkit, instala em `/opt/vela/<app>` e `/usr/share/applications/`.
- Windows: cópia em `%LOCALAPPDATA%/Programs/Vela/` e atalho de menu
  Iniciar usando WScript.Shell. A fixação na barra é opção do usuário.
- macOS: compilação local experimental; um instalador macOS integrado
  ainda não está validado nesta versão.

**Limite importante:** `--installer` gera scripts de instalação e integração
ao sistema, **não** um MSI/EXE do Inno Setup ou pacote DEB/RPM nativo.
Esses formatos dependem de toolchains adicionais e devem ser
implementados/testados separadamente. O Windows pode precisar do WebView2
Runtime quando a GUI nativa for escolhida.

O PyInstaller compila para o **SO no qual é executado**. O comando
`makeworkflow` cria jobs Windows/Linux nativos (com PyQt6 no Linux)
e publica artefatos em releases geradas por tags `v*`.
A compilação do Linux não inclui glibc; distribua para sistemas com
versões compatíveis. A opção padrão de software rendering em Qt6 tenta
contornar falhas GLX, sem substituir um driver gráfico correto.

### Recursos personalizados

São incluídos `apps/`, `config/`, `staticfiles/` e, se existir,
`assets/`. Dados do usuário, credenciais, caches e bancos pessoais
**não devem ser embutidos no executável**. Persistência fica em diretório
próprio via `vela.database.SQLiteStore`.

### Instalação global a partir do executável

Se o desenvolvedor escolher **todos os usuários**, o instalador Linux
reexecuta o próprio binário congelado com `--vela-install --scope=system`
através do Polkit. Se executado a partir do ambiente de desenvolvimento,
utiliza `python -m vela.cli.install`. Assim, nenhum processo precisa
coletar a senha administrativa por conta própria.

### Modo de produção automático

Todo launcher criado pelo `buildapp` define `VELA_PRODUCTION=1`.
O Vela ignora `DEBUG=True` do projeto durante a execução congelada para
evitar hot reload, habilitação acidental de DevTools e sobrecarga de
navegação. O desenvolvedor pode continuar com `DEBUG=True` em `runapp`
para iterar normalmente.
