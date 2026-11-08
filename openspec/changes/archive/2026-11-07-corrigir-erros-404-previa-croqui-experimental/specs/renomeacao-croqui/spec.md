## MODIFIED Requirements

### Requirement: Renomeação da Pasta Raiz
O sistema MUST identificar alterações no ID do croqui comparando o ID extraído em memória com o ID anterior real persistido no workspace (obtido dos metadados/arquivos do croqui no modo experimental, e nunca do UUID opaco da pasta raiz, ou do nome da pasta no modo de repositório local), limpando o diretório `compilado/` no modo experimental ou renomeando a pasta via Git no modo de repositório local exclusivamente quando o ID do croqui tiver sido de fato modificado.

#### Scenario: Edição e Salvamento de ID Alterado
- **WHEN** o usuário altera o ID do croqui na aba de dados (ex: de `br_mg_antigo` para `br_mg_novo`) e aciona o salvamento
- **THEN** o sistema detecta a divergência entre o ID anterior real (`br_mg_antigo`) e o novo ID (`br_mg_novo`), limpa os artefatos compilados com o ID antigo (ou renomeia o diretório no modo repositório local) e recompila o croqui com o novo identificador

#### Scenario: Salvamento sem Alteração de ID em Croqui Experimental com Pasta UUID
- **WHEN** o usuário salva um croqui experimental armazenado em uma pasta raiz de nome UUID opaco (ex: `41aea39b`) cujo `id` do croqui permanece inalterado (ex: `br_mg_igarape_pedra_grande`)
- **THEN** o sistema identifica que o ID atual real do croqui já é `br_mg_igarape_pedra_grande`, NÃO executa a limpeza destrutiva da pasta `compilado/` e realiza a compilação incremental preservando as imagens e artefatos existentes
