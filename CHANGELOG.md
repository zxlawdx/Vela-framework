# Histórico de alterações

## 0.2.2 — reparo do runtime PyInstaller / pkg_resources

- O extra \`[build]\` instala dependencias legadas do carregador
  \`pkg_resources\` (setuptools anterior a 82, jaraco e more-itertools).
- \`buildapp\` detecta \`pkg_resources\` e inclui explicitamente suas
  dependencias dinamicas no executavel congelado; falha antecipadamente
  se o venv estiver incompleto.
- O assistente \`doctor\` identifica os pacotes jaraco faltantes,
  oferece a instalacao com consentimento e mostra erro de empacotamento
  com orientacoes mais especificas.
- CI passa a exercitar o runtime hook \`pyi_rth_pkgres\` com
  \`pkg_resources\` importado no aplicativo de teste.


## 0.2.1 — correção de pacotes Linux congelados

- Build aborta caso `gi` (GTK) ou `qtpy`/QtWebEngine (Qt) não estejam acessíveis no Python do desenvolvedor.
- Força o backend escolhido ao pywebview, sem depender da ordem padrão de detecção.
- PyInstaller coleta explicitamente QtPy (ou bindings GTK na opção correspondente).
- Executa `--self-test` no executável congelado antes de gerar o ZIP; testes agora verificam imports da GUI selecionada, e não apenas pastas copiadas.
- Documenta a distinção entre bibliotecas GTK do SO e os bindings `gi` usados por Python/venv.

## 0.2.0 — prévia de desenvolvimento (sem tag oficial)

- buildapp: build nativo Windows/Linux e ZIP SHA-256 usando PyInstaller.
- Assistente gráfico Next/Next: init-process:instalation (e installation).
- doctor: diagnóstico e correção com consentimento/Polkit.
- installapp: menu .desktop Linux, atalhos Windows e associação MIME opcional.
- Configuração centralizada de nome, versão, ícone, autor e extensões.
- makeworkflow: GitHub Actions Linux Qt6 e Windows e releases por tags.
- API: Waitress multithread, cache de introspecção e docs OpenAPI offline.
- Produção sem reload de módulos em cada navegação; cache de templates.
- Serviços opcionais: jobs, events, notificações, verificações de updates,
  hooks de build e SQLite com migrations.
- Testes em Python 3.10/3.12 e smoke build Qt6 no GitHub Actions.

### Limites conhecidos

- Instaladores MSI/DEB/RPM nativos e instalador macOS não inclusos nesta prévia;
  --installer cria scripts e integração no SO.
- Benchmark contra Django **não** foi concluído; performance depende da carga.
- Builds nativos exigem runner do próprio SO; Linux depende de bibliotecas
  gráficas/glibc compatíveis; a compilação do Qt6 usa fallback de software.
