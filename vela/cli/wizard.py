"""Assistente visual de compilacao/instalacao. Sem comandos manuais.

python manage.py init-process:instalation
python manage.py init-process:installation
"""
from __future__ import annotations

import platform
import queue
import threading
import traceback
from pathlib import Path

from vela.cli.build import BuildOptions, backend_for, build_app, read_settings
from vela.cli.doctor import diagnose, print_report, remedy
from vela.cli.install import install_bundle


def launch_wizard(root=None):
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as exc:
        raise RuntimeError(
            "O assistente precisa de Tkinter. Ubuntu/Linux Mint: "
            "sudo apt install python3-tk. Windows: instale Python com Tcl/Tk."
        ) from exc

    class Wizard:
        def __init__(self, root_dir):
            self.project = Path(root_dir or Path.cwd()).resolve()
            self.settings = read_settings(self.project)
            self.window = tk.Tk()
            self.window.title("Vela • Assistente de distribuição")
            self.window.geometry("860x640")
            self.window.minsize(730, 520)
            self.window.configure(bg="#111b2b")
            self.window.protocol("WM_DELETE_WINDOW", self.on_close)
            self.messages = queue.Queue()
            self.running = False
            self.step = 0
            self.result = None
            self.gui = tk.StringVar(value="auto")
            self.icon = tk.StringVar(value=str(getattr(self.settings, "APP_ICON", "")))
            self.want_installer = tk.BooleanVar(value=True)
            self.want_tailwind = tk.BooleanVar(value=False)
            self.scope = tk.StringVar(value="user")
            self.status = tk.StringVar(value="Pronto")
            self.steps = [
                "Bem-vindo", "Configuração", "Dependências", "Compilar e instalar"
            ]
            style = ttk.Style(self.window)
            style.theme_use("clam")
            style.configure(".", background="#111b2b", foreground="#eff4ff", font=("Sans", 11))
            style.configure("TFrame", background="#111b2b")
            style.configure("TLabel", background="#111b2b", foreground="#e7efff")
            style.configure("TButton", padding=10)
            style.configure("TCheckbutton", background="#111b2b", foreground="#e7efff")
            style.configure("TRadiobutton", background="#111b2b", foreground="#e7efff")
            style.configure("TCombobox", padding=5)
            style.configure("Horizontal.TProgressbar", troughcolor="#223249",
                            background="#438fff")
            self.outer = ttk.Frame(self.window, padding=26)
            self.outer.pack(fill="both", expand=True)
            self.heading = ttk.Label(self.outer, text="", font=("Sans", 21, "bold"))
            self.heading.pack(anchor="w", pady=(0, 6))
            self.subtitle = ttk.Label(self.outer, text="", wraplength=710)
            self.subtitle.pack(anchor="w", pady=(0, 18))
            self.content = ttk.Frame(self.outer)
            self.content.pack(fill="both", expand=True)
            self.progress = ttk.Progressbar(self.outer, mode="indeterminate")
            self.progress.pack(fill="x", pady=(16, 6))
            ttk.Label(self.outer, textvariable=self.status, wraplength=720).pack(anchor="w")
            controls = ttk.Frame(self.outer)
            controls.pack(fill="x", pady=(16, 0))
            self.back = ttk.Button(controls, text="← Voltar", command=self.previous)
            self.back.pack(side="left")
            self.next = ttk.Button(controls, text="Próximo →", command=self.forward)
            self.next.pack(side="right")
            self.render()
            self.window.after(120, self.poll)

        def on_close(self):
            if self.running:
                messagebox.showinfo("Vela", "Conclua a operação antes de fechar.", parent=self.window)
            else:
                self.window.destroy()

        def clear(self):
            for child in self.content.winfo_children():
                child.destroy()

        def label(self, text, **kwargs):
            ttk.Label(self.content, text=text, wraplength=740, **kwargs).pack(
                anchor="w", pady=8)

        def render(self):
            self.clear()
            self.heading.config(text=self.steps[self.step])
            self.back.config(state="normal" if self.step else "disabled")
            self.next.config(text="Próximo →" if self.step < 3 else "Concluir",
                             state="normal")
            if self.step == 0:
                self.subtitle.config(text="Crie um pacote para o seu sistema com cliques, "
                                          "sem configurar manualmente o PyInstaller.")
                self.label("Projeto: " + str(self.project))
                self.label("Aplicação: " + getattr(self.settings, "APP_TITLE", "Vela App"))
                self.label("Sistema operacional detectado: " + platform.system())
                self.label("O build não exige permissões administrativas. "
                           "A instalação para o usuário atual também não precisa de sudo.")
            elif self.step == 1:
                self.subtitle.config(text="Escolha o backend gráfico, ícone e as opções de instalação.")
                row = ttk.Frame(self.content)
                row.pack(fill="x", pady=12)
                ttk.Label(row, text="Backend gráfico:").pack(side="left", padx=(0, 16))
                available = (("auto", "qt6", "qt5", "gtk") if platform.system() == "Linux"
                             else ("auto", "native", "qt6", "qt5"))
                ttk.Combobox(row, textvariable=self.gui, state="readonly",
                             values=available, width=19).pack(side="left")
                line = ttk.Frame(self.content)
                line.pack(fill="x", pady=12)
                ttk.Label(line, text="Ícone:").pack(side="left", padx=(0, 16))
                ttk.Entry(line, textvariable=self.icon, width=44).pack(
                    side="left", fill="x", expand=True)
                ttk.Button(line, text="Procurar...", command=self.select_icon).pack(
                    side="left", padx=8)
                ttk.Checkbutton(self.content, text="Gerar scripts de instalação no ZIP",
                                variable=self.want_installer).pack(anchor="w", pady=12)
                ttk.Checkbutton(self.content, text="Compilar CSS offline com Tailwind (requer Node.js)",
                                variable=self.want_tailwind).pack(anchor="w", pady=6)
                self.label("Instalar depois do build:")
                ttk.Radiobutton(self.content, text="Somente para meu usuário (recomendado)",
                                variable=self.scope, value="user").pack(anchor="w", pady=4)
                if platform.system() == "Linux":
                    ttk.Radiobutton(self.content,
                                    text="Para todos os usuários (solicita Polkit)",
                                    variable=self.scope, value="system").pack(anchor="w", pady=4)
            elif self.step == 2:
                self.subtitle.config(text="Confira os componentes antes da compilação.")
                checks = diagnose(self.project, self.gui.get())
                box = tk.Text(self.content, height=14, bg="#0c1320", fg="#dae6ff",
                              relief="flat", font=("Monospace", 10), wrap="word")
                box.pack(fill="both", expand=True)
                for item in checks:
                    box.insert("end", f"[{item.status.upper():7}] {item.name} — {item.message}\n")
                    if item.status != "ok":
                        box.insert("end", "  " + item.hint + "\n")
                box.config(state="disabled")
                ttk.Button(self.content, text="Instalar dependências ausentes...",
                           command=self.install_missing).pack(anchor="e", pady=12)
            else:
                self.subtitle.config(text="Revise e compile. A instalação só será executada "
                                          "depois da sua confirmação.")
                self.label("Sistema: " + platform.system())
                self.label("Backend: " + backend_for(self.gui.get()))
                self.label("Ícone: " + (self.icon.get() or "Padrão"))
                self.label("Destino: " + str(self.project / "dist"))
                actions = ttk.Frame(self.content)
                actions.pack(anchor="w", pady=12)
                self.compile_btn = ttk.Button(actions, text="Compilar aplicativo",
                                              command=self.compile)
                self.compile_btn.pack(side="left", padx=(0, 14))
                self.install_btn = ttk.Button(actions, text="Instalar agora",
                                              command=self.install, state=(
                                                  "normal" if self.result else "disabled"))
                self.install_btn.pack(side="left")
                self.output = tk.Text(self.content, height=11, bg="#0c1320",
                                      fg="#dceaff", font=("Monospace", 10))
                self.output.pack(fill="both", expand=True)
                if self.result:
                    self.output.insert("end", "Pacote: " + str(self.result["archive"]) + "\n")

        def select_icon(self):
            selected = filedialog.askopenfilename(
                parent=self.window, title="Selecionar ícone",
                filetypes=[("Ícones", "*.png *.ico *.icns"), ("Todos", "*.*")])
            if selected:
                self.icon.set(str(Path(selected).resolve()))

        def previous(self):
            if not self.running and self.step:
                self.step -= 1
                self.render()

        def forward(self):
            if self.running:
                return
            if self.step < 3:
                self.step += 1
                self.render()
            else:
                self.on_close()

        def busy(self, value):
            self.running = value
            for btn in (self.back, self.next):
                btn.config(state="disabled" if value else "normal")
            if value:
                self.progress.start(10)
            else:
                self.progress.stop()
                self.back.config(state="normal" if self.step else "disabled")

        def run_worker(self, task):
            if self.running:
                return
            self.busy(True)
            def runner():
                try:
                    result = task()
                    self.messages.put(("success", result))
                except Exception:
                    self.messages.put(("failure", traceback.format_exc()))
            threading.Thread(target=runner, daemon=True).start()

        def poll(self):
            while True:
                try:
                    kind, value = self.messages.get_nowait()
                except queue.Empty:
                    break
                if kind == "log":
                    self.status.set(str(value))
                    if self.step == 3 and hasattr(self, "output"):
                        self.output.insert("end", str(value) + "\n")
                        self.output.see("end")
                elif kind == "confirm":
                    prompt, evt, result = value
                    result.append("s" if messagebox.askyesno(
                        "Confirmar instalação", prompt, parent=self.window) else "n")
                    evt.set()
                elif kind == "success":
                    self.busy(False)
                    if isinstance(value, dict) and "archive" in value:
                        self.result = value
                        self.status.set("Build concluído!")
                        if self.step == 3:
                            self.install_btn.config(state="normal")
                            self.output.insert("end", "Pacote: " + str(value["archive"]) + "\n")
                    else:
                        self.status.set("Operação concluída.")
                        if self.step == 2:
                            self.render()
                elif kind == "failure":
                    self.busy(False)
                    self.status.set("Ocorreu um erro; detalhes exibidos abaixo.")
                    messagebox.showerror("Vela — Operação interrompida",
                                         str(value)[-3500:], parent=self.window)
                    if self.step == 3 and hasattr(self, "output"):
                        self.output.insert("end", str(value) + "\n")
            if self.window.winfo_exists():
                self.window.after(120, self.poll)

        def log(self, message):
            self.messages.put(("log", str(message)))

        def ask_from_worker(self, text):
            event = threading.Event()
            reply = []
            self.messages.put(("confirm", (text, event, reply)))
            event.wait()
            return reply[0]

        def install_missing(self):
            checks = diagnose(self.project, self.gui.get())
            self.run_worker(lambda: remedy(checks, confirm=self.ask_from_worker,
                                           notify=self.log))

        def compile(self):
            self.compile_btn.config(state="disabled")
            options = BuildOptions(
                gui=self.gui.get(), icon=self.icon.get(),
                installer=self.want_installer.get(),
                tailwind=self.want_tailwind.get())
            self.run_worker(lambda: build_app(self.project, options, notify=self.log))

        def install(self):
            if not self.result or self.running:
                return
            if not messagebox.askyesno("Instalar aplicativo",
                                       "Instalar " + self.result["meta"]["name"] +
                                       " (" + self.scope.get() + ")?",
                                       parent=self.window):
                return
            self.run_worker(lambda: install_bundle(self.result["bundle"],
                                                    scope=self.scope.get(),
                                                    notify=self.log))

    Wizard(root).window.mainloop()
