# Especificação Técnica: Sincronização e Migração Contínua do editor

## 1. Auto-Update do Editor

O editor adota um modelo de atualização "silenciosa e persistente", garantindo que a versão local nunca divirja significativamente da lógica de produção no GitHub.

### 1.1. Detecção e Background Download
Ao iniciar, o PyQt6 dispara uma `QThread` de baixa prioridade para realizar as seguintes etapas:
1.  **Consulta de Versão:** Faz um GET no arquivo `editor_config.json` (via GitHub Raw) para obter o timestamp do `latest_build`.
2.  **Download em Segundo Plano:** Se o build local for inferior ao remoto, o sistema baixa o novo binário (`.exe`, `.AppImage` ou `.app`) e o salva com a extensão temporária `.new` no diretório da aplicação em local storage.
3.  **Validação:** Após o download, verifica o hash do arquivo para garantir que não houve corrupção.

### 1.2. Interface e UX (Banner de Atualização)
Uma vez que o arquivo `.new` está pronto no disco:
-   **Notificação:** Um banner não obstrutivo aparece no topo da interface: *"✨ Uma nova versão está pronta. [Reiniciar para Atualizar]"*.
-   **Troca de Binários:** Ao clicar, o app executa um script de lote (`.bat` ou `.sh`) que aguarda o fechamento do processo atual, substitui o executável antigo pelo `.new` e reinicia a aplicação.

### 1.3. O "Gatekeeper" da Pull Request
Para garantir a integridade do repositório oficial, o envio de contribuições possui uma trava lógica:
-   **Validação de Envio:** O botão "Enviar para Produção" verifica obrigatoriamente se a versão atual é o `latest_build`.
-   **Bloqueio Reativo:** Se houver uma atualização pendente (já baixada ou não), o envio é pausado e o usuário é forçado a atualizar antes de prosseguir com a abertura da PR.

## 2. Migração de Dados (O Formato `.croqui`)

Para evitar que mudanças na API corrompaam croquis editados em versões diferentes, o sistema utiliza um motor de migração sequencial e offline.

### 2.1. Versionamento Baseado em Timestamps
Em vez de números de versão semântica (v1, v2), o sistema utiliza identificadores baseados no momento de criação do script de migração.
-   **Pasta de Migrações:** `/migracoes/YYYYMMDD_HHMM_descricao_da_mudanca.py`.
-   **croqui.yaml:** O arquivo `croqui.yaml` de cada croqui contém a chave `ultima_migracao`, registrando o ID do último script aplicado com sucesso.

### 2.2. O Motor de Migração Sequencial
Sempre que um croqui é aberto, o compilador executa a seguinte lógica interna:
1.  **Varredura:** Lista todos os scripts na pasta `/migracoes` embutida no binário.
2.  **Ordenação Lexicográfica:** Garante que as mudanças sejam aplicadas na ordem cronológica exata em que foram desenvolvidas.
3.  **Execução em Cascata:** Aplica apenas os scripts cujos nomes sejam estritamente "maiores" (posteriores) à `ultima_migracao` do arquivo.

### 2.3. Resiliência Offline
Como todos os scripts de migração históricos são incluídos dentro do executável via PyInstaller, o "poder de cura" do editor é totalmente offline. Um usuário que passe meses sem internet poderá atualizar seu editor via pendrive e, ao abri-lo, todos os seus croquis antigos serão convertidos instantaneamente para o formato atual sem precisar consultar o GitHub.

## 3. Sinergia entre os Sistemas

O sucesso da arquitetura reside na interação entre as duas partes:

1.  **Atualização do Desenvolvedor:** Você altera a API no repositório, cria um novo script de migração em `/migracoes` e faz o push.
2.  **Build Automático:** O GitHub Actions gera o novo executável e atualiza o `editor_config.json`.
3.  **Entrega ao Usuário:** O editor do colaborador baixa o binário novo em segundo plano.
4.  **Consistência dos Dados:** Ao reiniciar, o novo editor identifica que o croqui local está "atrasado" em relação aos scripts que ele agora carrega, aplica a migração e salva o `croqui.yaml` atualizado.
5.  **Submissão Limpa:** A Pull Request chega ao GitHub já no formato novo, passando automaticamente pelos testes de QA da Action de produção.

Essa estrutura transforma o editor em uma ferramenta de "manutenção zero" para o usuário final, protegendo o histórico de abertura de vias e a qualidade dos dados de forma invisível.