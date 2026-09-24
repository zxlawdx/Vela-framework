# Serviços auxiliares do Vela

Esses recursos são opcionais e evitam adicionar dependências pesadas ao
núcleo do framework.

## Jobs de longa duração

~~~python
from vela.jobs import JobManager
jobs = JobManager(io_workers=4, cpu_workers=2)
future = jobs.submit(minha_funcao_de_io, dados, mode="io")
future.add_done_callback(lambda f: print(f.result()))
# mode="cpu" usa ProcessPoolExecutor para tarefas CPU-bound.
~~~

Callbacks acontecem **fora da thread da interface**: para alterar UI
Tk/Qt/WebView, agende a ação na thread principal.

## Eventos Python → JavaScript

~~~python
# Em uma BaseBridge personalizada, depois da janela estar pronta:
self.emit("progresso", {"etapa": 2, "total": 5})
~~~

~~~javascript
window.addEventListener("vela:event", event => {
  if (event.detail.name === "progresso") {
    console.log(event.detail.payload);
  }
});
~~~

Em Python puro, \`EventBus.on(name, callback)\` registra ouvintes e
\`EventBus.off(name, callback)\` os remove.

## SQLite e migrations

~~~python
from vela.database import SQLiteStore
store = SQLiteStore("meu-app")
store.migrate("migrations")
with store.connect() as db:
    db.execute("INSERT INTO exemplo(valor) VALUES(?)", ("exemplo",))
    db.commit()
~~~

Os arquivos \`migrations/*.sql\` são aplicados em ordem lexicográfica
e cada SHA-256 é registrado. A alteração de migration já aplicada gera
erro em vez de corromper a trilha de versões. Também existe
\`python manage.py dbmigrate --dir migrations\`.
Por padrão, o banco fica no diretório de dados do usuário do SO.

## Notificações e consulta de atualizações

~~~python
from vela.desktop import notify, check_for_updates
notify("DFD Studio", "Exportação concluída")
info = check_for_updates("zxlawdx/DFD-Studio", "0.2.0")
if info["available"]:
    print("Veja a versão publicada:", info["url"])
~~~

A consulta é **opt-in** e usa GitHub Releases; não faz download nem
instala atualizações silenciosamente. Linux usa notify-send, macOS
osascript; no Windows, notificações dependem do extra opcional
\`pip install "vela-framework[notifications]"\`. Também é possível
\`python manage.py checkupdates --repo owner/repo\`.

## Plugins de build

~~~python
from vela.plugins import register_build_hook

@register_build_hook
def minha_integracao(plan):
    # modifique plan["command"] ou valide condições antes do PyInstaller
    pass
~~~

Pacotes confiáveis podem registrar um entry point
\`[project.entry-points."vela.build_hooks"]\`. Para usar, selecione
\`python manage.py buildapp --plugins\`. Hooks executam código Python
dos pacotes instalados: **ative apenas plugins em que confia**.
