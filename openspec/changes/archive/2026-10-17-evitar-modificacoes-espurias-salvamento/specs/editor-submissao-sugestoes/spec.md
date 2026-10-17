## ADDED Requirements

### Requirement: Comparação e Espelhamento Insensíveis a Diferenças Legadas de EOL em Arquivos Textuais
O `ServicoSubmissao` MUST ignorar diferenças exclusivas de quebras de linha (`CRLF` vs `LF`) ao comparar e espelhar arquivos textuais (`.md`, `.yaml`, `.yml`, `.json`) entre o diretório do croqui experimental e o repositório base local, garantindo que arquivos sem alteração de conteúdo não sejam reportados como modificados nem gerem commits espúrios.

#### Scenario: Detecção de arquivos modificados com diferença apenas de CRLF vs LF
- **WHEN** `obter_arquivos_modificados` comparar um arquivo `.md` ou `.yaml` do croqui experimental (em `LF`) com o arquivo correspondente no repositório base local (com `CRLF` residual, mas mesmo conteúdo textual)
- **THEN** o arquivo NÃO MUST ser incluído na lista de arquivos modificados

#### Scenario: Espelhamento e commit em repositório base
- **WHEN** `sincronizar_arquivos_croqui` espelhar os arquivos do croqui experimental para `database/<id_croqui>/` no repositório base
- **THEN** arquivos textuais cujo conteúdo normalizado em `LF` seja idêntico ao destino NÃO MUST ser considerados alterações de conteúdo, e qualquer arquivo textual escrito no destino MUST estar normalizado em `LF`
