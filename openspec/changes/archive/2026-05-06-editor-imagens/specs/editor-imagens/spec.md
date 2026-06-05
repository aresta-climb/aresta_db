## ADDED Requirements

### Requirement: Integração do Editor de Imagens
O sistema SHALL fornecer um editor de imagens integrado para processamento em lote (crop, rotação e máscaras).

#### Scenario: Acesso ao Editor de Imagens
- **WHEN** o usuário seleciona a visão "Imagens" na barra lateral
- **THEN** o sistema SHALL exibir o widget de edição de imagens na área central.

#### Scenario: Listagem de Imagens
- **WHEN** o editor de imagens é carregado
- **THEN** o sistema SHALL listar todas as imagens presentes na pasta `imagens/` do croqui atual.

#### Scenario: Edição de Imagem (Crop e Máscaras)
- **WHEN** o usuário interage com as ferramentas de crop ou adiciona máscaras em uma imagem
- **THEN** o sistema SHALL manter o estado de edição em memória e marcar a imagem como modificada na lista.

#### Scenario: Sincronização com Salvamento Global
- **WHEN** o usuário clica no botão "Salvar" global da barra de ferramentas superior
- **THEN** o sistema SHALL persistir todas as alterações feitas nas imagens no disco, processando crops, rotações e "queimando" as máscaras.

#### Scenario: Execução Autônoma
- **WHEN** o script `scripts/editar_imagens.py` é executado via linha de comando
- **THEN** ele SHALL abrir uma janela independente com seu próprio botão "Salvar" visível.
