# Design Técnico: Canal de Distribuição Beta via Windows App Installer e Cloudflare R2

## Contexto

O Editor Aresta é uma aplicação desktop desenvolvida em Python e PyQt6, empacotada como executável para Windows via PyInstaller e distribuída na Microsoft Store em formato MSIX sob o Store ID `9N6CQNH78WN8`.

Embora a publicação na Microsoft Store garanta atualizações automáticas e confiabilidade para o usuário final, qualquer envio para a loja (mesmo em canais de pré-lançamento fechados) passa pela fila de ingestão e certificação da Microsoft, gerando esperas de horas a dias. Isso inviabiliza iterações rápidas com beta-testers e a equipe interna.

Ao mesmo tempo, o projeto Aresta já possui infraestrutura própria de alta disponibilidade com Cloudflare R2 associada ao domínio `serving.arestaclimb.com`, gerenciada por bibliotecas Python com `boto3` e purgação automática de cache da CDN via API Token (`CLOUDFLARE_CACHE_PURGE_API_TOKEN`).

O Windows moderno oferece a tecnologia nativa **Windows App Installer** (`.appinstaller` + MSIX), que permite instalar pacotes MSIX diretamente da web (HTTP/HTTPS) e checar/aplicar atualizações automaticamente na abertura do aplicativo, sem necessitar de rotinas customizadas de auto-atualização em Python e sem depender da esteira de certificação da Microsoft Store.

## Objetivos e Não-Objetivos

**Objetivos:**
- Prover um canal de testes **Beta** independente e de iteração imediata (disponível minutos após a compilação na esteira de CI/CD).
- Permitir a **coexistência lado a lado** da versão oficial da Loja e da versão Beta na mesma máquina Windows, sem colisão de assinaturas ou sobreposição de dados locais virtualizados.
- Diferenciar visualmente o canal Beta de forma inconfundível: identidade visual em **Azul** (em contraste com o **Laranja** de produção), selo textual **"BETA"** na tela de abertura (splash screen), e sufixo `(Beta)` no nome da aplicação e títulos de janela.
- Garantir isolamento de processo na barra de tarefas do Windows via `AppUserModelID` (`aresta.editor.beta` vs `aresta.editor.v1`).
- Oferecer uma experiência de integração do testador amigável e sem atrito através de um instalador `.bat` auto-contido (com certificado embutido em Base64, execução oculta e abertura automática do navegador na página de sucesso).
- Integrar a distribuição Beta ao Cloudflare R2 em `serving.arestaclimb.com/editor-beta/` com nome estático de binário (`EditorArestaBeta.msix`) e purgação imediata de cache na CDN Cloudflare.
- Atualizar o fluxo de trabalho `.github/workflows/release-editor.yml` para compilar e empacotar ambas as versões: Produção como rascunho na Microsoft Store (`--noCommit`) e Beta no R2 via `.appinstaller`.
- Cumprir integralmente os princípios de engenharia em `PRINCIPIOS.md`: Tudo em Português, Library-First, 100% de cobertura de testes, TDD rigoroso e Testes de Integração em primeiro lugar.

**Não-Objetivos:**
- Implementar um mecanismo in-app próprio de download e substituição de executáveis em Python (o Windows App Installer gerencia o ciclo de vida e substituição de arquivos nativamente no sistema operacional).
- Armazenar histórico de versões binárias antigas no bucket R2 (o histórico de binários de lançamentos anteriores é mantido pelo GitHub Releases e tags do Git).
- Adquirir certificados comerciais pagos de assinatura de código neste momento (um certificado autoassinado com importação inicial em `TrustedPeople` atende perfeitamente ao grupo de testes).
- Modificar o fluxo de validação de dados de croqui, autenticação Supabase ou sincronização de banco de dados.

## Decisões Arquiteturais e Estruturais

### 1. Library-First: Separação Modular e Bibliotecas Autossuficientes (Princípio II)
Seguindo o princípio inegociável de *Library-First*, a funcionalidade é decomposta em bibliotecas coesas, testáveis e com propósitos específicos:

1. **`editor/core/configuracao_canal.py`**:
   - Biblioteca autossuficiente responsável por determinar a identidade do canal de execução.
   - Fornece a classe de dados `ConfiguracaoCanal` e a função pura `obter_configuracao_canal(nome_canal: Optional[str] = None) -> ConfiguracaoCanal`.
   - Propriedades expostas: `nome_aplicativo: str`, `app_user_model_id: str`, `titulo_janela(versao: str) -> str`, `eh_beta: bool`, `subdiretorio_recursos: str`.
   - Não depende do ciclo de vida da interface gráfica do Qt, permitindo testes unitários instantâneos e isolados.

2. **`editor/release_tools/gerador_appinstaller.py`**:
   - Biblioteca pura que gera o XML do manifesto Windows App Installer a partir do número da versão e da URI base.
   - Função pura: `gerar_conteudo_appinstaller(versao: str, uri_base: str) -> str`.
   - Valida formatação semântica e gera tags de atualização em segundo plano `<OnLaunch HoursBetweenUpdateChecks="0" />` e `<AutomaticBackgroundTask />`.

3. **`editor/release_tools/gerador_instalador_bat.py`**:
   - Biblioteca pura responsável por montar o script `.bat` embutindo o bloco X.509 Base64 e os comandos de auto-elevação oculta e redirecionamento web.
   - Função pura: `gerar_script_instalador_bat(conteudo_certificado_pem: str, url_sucesso: str) -> str`.

4. **`editor/release_tools/publicador_r2_beta.py`**:
   - Biblioteca autossuficiente para envio dos artefatos ao bucket `aresta-serving` via `boto3` e acionamento da API da Cloudflare para purgação imediata de cache.
   - Reutiliza os padrões declarativos já adotados em `serving/update_serving.py`.

### 2. Testes de Integração em Primeiro Lugar (Princípio V)
Antes da implementação dos detalhes internos, contratos de integração são estabelecidos:
- **`editor/core/integracao_canal_beta_test.py`**: Valida a integração entre a biblioteca `configuracao_canal`, a inicialização do Qt em `main.py` e a instanciação da `TelaDeAbertura`, garantindo que sob `ARESTA_CANAL=beta` o título, a identidade da barra de tarefas e os caminhos de recursos gráficos sejam respeitados.
- **`editor/release_tools/integracao_distribuicao_beta_test.py`**: Valida o fluxo de ponta a ponta: geração do XML `.appinstaller`, geração do script `.bat` com certificado embutido, upload mockado no S3 e requisição de purgação de cache na Cloudflare.

### 3. Identidades Paralelas de Pacote MSIX (Coexistência sem Conflitos)
- Para a versão oficial da Loja: `Name="ArestaClimbApps.EditorArestaClimb"`, `DisplayName="Editor Aresta"`.
- Para a versão Beta: `Name="ArestaClimbApps.EditorArestaClimb.Beta"`, `DisplayName="Editor Aresta (Beta)"`.
- **Justificativa**: O Windows proíbe a sobreposição de pacotes com mesmo nome que possuam chaves criptográficas distintas (chave oficial da Microsoft Store vs certificado autoassinado do Beta). A identidade `.Beta` garante que os dois aplicativos coexistam pacificamente sem apagar o `LocalCache` um do outro.

### 4. Armazenamento Estático no Cloudflare R2 e Purgação de Cache
- O bucket `aresta-serving` recebe apenas 3 arquivos fixos sob `editor-beta/`:
  - `EditorAresta.appinstaller`
  - `EditorArestaBeta.msix`
  - `InstalarCertificadoEditorArestaBeta.bat`
- A cada lançamento, o binário `.msix` e o manifesto `.appinstaller` são atualizados no mesmo local. O script de lançamento dispara a purgação imediata das URLs na CDN Cloudflare.

### 5. Script `.bat` Auto-Contido com Execução Oculta
- O script contém o certificado público PEM embutido ao final do arquivo.
- Utiliza a capacidade nativa de `certutil -decode "%~f0"` para extrair e instalar o certificado na loja `TrustedPeople` da máquina local.
- Relança a si mesmo com elevação UAC utilizando `-WindowStyle Hidden`, eliminando janelas pretas de prompt de comando.
- Ao concluir a importação, abre automaticamente o navegador padrão na página `https://arestaclimb.com/editor/beta/sucesso-certificado` e encerra a execução.

### 6. Identidade Visual Azul para o Canal Beta
- Recursos de produção (Laranja): mantidos em `editor/recursos/` e `editor/msix/Assets/`.
- Recursos do beta (Azul): criados em `editor/recursos_beta/` e `editor/msix_beta/Assets/`.
- O código da aplicação consome os recursos gráficos conforme indicado por `configuracao_canal.obter_configuracao_canal()`.

## Riscos e Mitigações

- **[Aviso do Windows SmartScreen na primeira execução]** → *Mitigação*: A página de sucesso `arestaclimb.com/editor/beta/sucesso-certificado` exibirá orientações visuais claras ("Mais informações" ➔ "Instalar assim mesmo"). Após a primeira instalação, o certificado em `TrustedPeople` torna o pacote confiável para atualizações automáticas.
- **[Permissão de Administrador necessária para instalar o certificado]** → *Mitigação*: O script `.bat` solicita elevação automática nativa do Windows (UAC) apenas uma vez durante a configuração inicial. As atualizações subsequentes via Windows App Installer ocorrem sem necessidade de privilégios administrativos.
- **[Falha de purgação de cache na CDN Cloudflare]** → *Mitigação*: A biblioteca `publicador_r2_beta.py` valida explicitamente a resposta da API Cloudflare e interrompe a esteira em caso de erro de rede ou autenticação.
