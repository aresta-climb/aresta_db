## Why

Ao remover um mapa recém-adicionado no editor de dados e tentar adicioná-lo novamente, o usuário é impedido por uma mensagem de erro afirmando que a imagem já existe na memória RAM. Isso ocorre porque o comando de remoção de itens (`CmdRemoverRepeated`) remove apenas a entidade Protobuf, deixando os bytes da imagem órfãos em `CroquiModel._imagens_em_memoria`. Além disso, a validação de colisão de nomes em `DialogoAdicionarMapa` utiliza `obter_bytes_imagem()`, que lê do disco e acusa falsamente conflito na memória RAM mesmo para arquivos persistidos em disco. Por fim, a sugestão automática de nomes para novos mapas e arquivos de setores/grupos duplica desnecessariamente os prefixos quando a entidade já possui a palavra no nome (e.g. "Setor Fugitivos I" resultando em `setor_setor_fugitivos_i_p0.webp`).

## What Changes

- **Limpeza e Restauração de Imagens em RAM no Histórico (`CmdRemoverRepeated`)**:
  - `CmdRemoverRepeated` inspeciona o elemento removido para identificar todas as imagens em memória associadas.
  - Caso não existam outras referências à imagem no restante do croqui, o comando remove os bytes da memória RAM no `executar_redo()` e os restaura no `undo()`.
  - Serialização e deserialização do comando preservam o dicionário de imagens para integridade do diário de recuperação.
- **Correção da Verificação de RAM no Diálogo de Mapas (`DialogoAdicionarMapa`)**:
  - Atualiza a validação de colisão em tempo real para verificar especificamente `self.model.obter_imagens_em_memoria()` para o alerta de memória RAM.
  - Garante que a checagem de disco (`db_dir / caminho_rel`) seja executada corretamente quando o arquivo existir apenas na pasta `imagens/`.
- **Deduplicação de Prefixos no Nome Automático**:
  - Na sugestão de nomes de arquivo de mapas em `WidgetEditorDados`, detecta se o slug gerado já inicia com o prefixo da entidade (`setor_` ou `grupo_`), evitando duplicações como `setor_setor_...` ou `grupo_grupo_...`.
  - Na proposição de nomes de arquivo `.md` em `DialogoCriarSetorOuGrupo`, evita igualmente duplicar o prefixo quando o usuário nomeia o setor/grupo com a palavra correspondente.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade introduzida -->

### Modified Capabilities
- `undo-redo-protobuf`: `CmdRemoverRepeated` passa a gerenciar a remoção e restauração de imagens em memória RAM quando itens repeated contendo imagens são excluídos ou restaurados.
- `editor-mapas`: O diálogo de adicionar mapas passa a validar colisões de RAM estritamente contra o buffer de memória e a permitir a re-inclusão de mapas cujas imagens foram descartadas da RAM.
- `editor-dados-mapa-gateway`: A sugestão automática de nome de arquivo para novos mapas passa a deduplicar prefixos de setor e grupo.

## Impact

- **Código Afetado**:
  - `editor/commands/comandos_protobuf.py`: `CmdRemoverRepeated` atualizado com inspeção de imagens órfãs, remoção em `redo` e restauração em `undo`.
  - `editor/views/dialogos/dialogo_adicionar_mapa.py`: Checagem de RAM em `_validar_estado`.
  - `editor/views/widget_editor_dados.py`: Geração de `nome_sugerido` em `_on_add_clicked` de mapas.
  - `editor/views/dialogos/dialogo_criar_setor_ou_grupo.py`: Geração de `edit_arquivo` em `_atualizar_proposicao_arquivo`.
- **Compatibilidade**: Totalmente retrocompatível; arquivos de croqui já gravados não sofrem alterações automáticas.
- **Dependências**: Nenhuma dependência externa adicionada.
