# Histórico de alterações

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
