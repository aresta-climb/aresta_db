## 1. Helper de Versão

- [x] 1.1 (TDD) Escrever testes unitários (`_test.py`) para o utilitário de descoberta de versão. Deve testar a extração correta baseada em mocks da pasta de migrações.
- [x] 1.2 Implementar utilitário (`aresta_db/scripts/` ou similar) para fazer os testes do passo anterior passarem. Garantir 100% de test coverage.

## 2. Exportação

- [x] 2.1 (TDD) Escrever testes garantindo que o builder utiliza o número da versão para gerar os outputs na pasta correta (ex: `v15`).
- [x] 2.2 Modificar o script de build/exportação (`build.py`) para usar o número de versão na criação das subpastas, mantendo 100% de test coverage.

## 3. Deploy

- [x] 3.1 Configurar variáveis de ambiente (`$GITHUB_ENV`) com a versão do build extraída da migração atual.
- [x] 3.2 Obter os *secrets* do Cloudflare no Github Settings.
- [x] 3.3 Modificar `.github/workflows/deploy.yml` para realizar o upload e cache purge copiando e adaptando o script de exemplo documentado em `docs/cloudflare_setup_guide.md`. O script substitui o antigo push no git por `aws s3 sync` seguido por um `curl` de purge na API do Cloudflare mirando o `indice.binarypb`.
