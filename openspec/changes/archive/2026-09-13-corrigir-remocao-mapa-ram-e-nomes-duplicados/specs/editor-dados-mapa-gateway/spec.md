## MODIFIED Requirements

### Requirement: O diálogo DEVE sugerir o nome correto do arquivo e impedir sobrescrita indevida
A sugestão DEVE seguir a convenção de nomenclatura do projeto baseada na entidade pai sem duplicar prefixos de entidade. O arquivo NÃO PODE ser sobrescrito acidentalmente.

#### Scenario: Nome gerado é único
- **WHEN** o usuário adiciona um mapa em um setor ou grupo
- **THEN** o sistema gera o nome sugerido deduplicando o prefixo da entidade quando o nome da entidade já começar com "setor_" ou "grupo_" (e.g. "Setor Fugitivos I" gera `setor_fugitivos_i_p<idx>.webp` em vez de `setor_setor_fugitivos_i_p<idx>.webp`).

#### Scenario: Tentativa de usar nome de arquivo que já existe
- **WHEN** o usuário tenta confirmar (OK) no diálogo e o nome do arquivo já existe na pasta `imagens/`
- **THEN** o sistema exibe um alerta de erro e não permite confirmar, exigindo a edição manual do nome do arquivo.
