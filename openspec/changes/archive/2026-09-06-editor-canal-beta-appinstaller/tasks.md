## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 1.1 Criar teste de integração `editor/core/integracao_canal_beta_test.py` definindo os contratos entre a configuração de canal, inicialização em `main.py` e a `TelaDeAbertura` sob variáveis de ambiente do canal Beta.
- [x] 1.2 Criar teste de integração `editor/release_tools/integracao_distribuicao_beta_test.py` definindo o contrato de ponta a ponta: geração do `.appinstaller`, geração do `.bat`, upload no S3/R2 mockado e acionamento da API de purgação de cache na Cloudflare.

## 2. Biblioteca de Configuração de Canal (Princípios II, III e IV - TDD)

- [x] 2.1 Criar suíte de testes unitários `editor/core/configuracao_canal_test.py` cobrindo detecção dos canais `producao` e `beta`, nomes de aplicativo, títulos de janela e `AppUserModelID` (Fase Vermelha - TDD).
- [x] 2.2 Implementar a biblioteca independente `editor/core/configuracao_canal.py` em conformidade estrita com os testes unitários (Fase Verde - TDD).
- [x] 2.3 Integrar `configuracao_canal` em `editor/main.py` e `editor/views/tela_de_abertura.py` para usar dinamicamente o título, caminhos de recursos gráficos e identificador da barra de tarefas do Windows.

## 3. Recursos Gráficos e Manifesto do Canal Beta

- [x] 3.1 Criar variações gráficas em Azul dos recursos visuais da aplicação: `logo_splash.png`, `logo_app.png` e `logo.ico` sob o diretório `editor/recursos_beta/`.
- [x] 3.2 Criar recursos gráficos em Azul para os blocos MSIX em `editor/msix_beta/Assets/` (`Square150x150Logo.png`, `Square44x44Logo.png`, `StoreLogo.png`, `Wide310x150Logo.png`, `SplashScreen.png`).
- [x] 3.3 Criar o manifesto MSIX para o canal Beta em `editor/msix_beta/AppxManifest.xml` com `Name="ArestaClimbApps.EditorArestaClimb.Beta"` e `DisplayName="Editor Aresta (Beta)"`.

## 4. Bibliotecas de Geração de Artefatos (Princípios II, III e IV - TDD)

- [x] 4.1 Criar suíte de testes unitários `editor/release_tools/gerador_appinstaller_test.py` cobrindo a montagem determinística do XML do `.appinstaller` com parâmetros de atualização automática em segundo plano e URI base do R2 (Fase Vermelha - TDD).
- [x] 4.2 Implementar a biblioteca independente `editor/release_tools/gerador_appinstaller.py` em conformidade com os testes (Fase Verde - TDD).
- [x] 4.3 Criar suíte de testes unitários `editor/release_tools/gerador_instalador_bat_test.py` cobrindo a injeção do bloco X.509 Base64 no script batch com elevação oculta (`-WindowStyle Hidden`), importação via `certutil` e redirecionamento para a página de sucesso (Fase Vermelha - TDD).
- [x] 4.4 Implementar a biblioteca independente `editor/release_tools/gerador_instalador_bat.py` e o template do script `InstalarCertificadoEditorArestaBeta.bat` (Fase Verde - TDD).

## 5. Biblioteca de Publicação e Purgação no Cloudflare R2 (Princípios II, III e IV - TDD)

- [x] 5.1 Criar suíte de testes unitários `editor/release_tools/publicador_r2_beta_test.py` mockando upload S3 via `boto3` e chamada de purgação de cache na API da Cloudflare (Fase Vermelha - TDD).
- [x] 5.2 Implementar a biblioteca independente `editor/release_tools/publicador_r2_beta.py` com suporte ao upload dos arquivos fixos (`EditorAresta.appinstaller`, `EditorArestaBeta.msix`, `InstalarCertificadoEditorArestaBeta.bat`) e purgação imediata na Cloudflare (Fase Verde - TDD).

## 6. Orquestração no Fluxo de CI/CD (`release-editor.yml`)

- [x] 6.1 Atualizar o parâmetro de entrada `should_publish` no arquivo `.github/workflows/release-editor.yml` para ter valor padrão `false` (modo rascunho seguro na Microsoft Store).
- [x] 6.2 Adicionar no fluxo de trabalho a compilação dual com PyInstaller para o canal Beta utilizando os recursos de `editor/recursos_beta/`.
- [x] 6.3 Adicionar etapas no fluxo para empacotar o MSIX Beta (`makeappx`), assinar digitalmente (`signtool`), gerar o `.appinstaller` e o instalador `.bat`, enviar para o bucket R2 `aresta-serving` sob `editor-beta/` e disparar a purgação de cache.

## 7. Validação Final e Cobertura de Testes (Princípios III e IV)

- [x] 7.1 Executar a suíte de testes completa via `pytest` com verificação de 100% de cobertura nos módulos novos e modificados.
- [x] 7.2 Executar testes estáticos e de validação arquitetural do repositório para assegurar ausência de regressões.
