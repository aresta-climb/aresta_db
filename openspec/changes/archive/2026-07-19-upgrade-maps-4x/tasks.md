## 1. Mapeamento e OCR

- [x] 1.1 Criar e executar script para extrair OCR (via PaddleOCR) das imagens da pasta `original_com_legenda/0.5x` gerando arquivos JSON lado a lado.
- [x] 1.2 Gerar o arquivo `mapping.json` no repositório a partir dos JSONs.
- [x] 1.3 Revisão manual e aprovação do `mapping.json` (Parada no sistema).

## 2. Preparação de Imagens (Sem Legenda)

- [x] 2.1 Criar script de renomeação `renomear_imagens.py` que lê o `mapping.json` e copia+renomeia os arquivos da pasta `sem_legenda/4x` para uma nova pasta temporária (`temp_mapas`).json`.
- [x] 2.2 Rodar `scripts/comprimir_imagens.py` nos arquivos `.png` renomeados em `sem_legenda/4x` para convertê-los em `.webp` redimensionados.
- [x] 2.3 Substituir todas as imagens legadas na pasta destino do banco de dados pelos novos arquivos otimizados em `.webp`.

## 3. Re-escala de Coordenadas

- [x] 3.1 Criar script para recalcular coordenadas baseado nas novas resoluções finais versus as antigas listadas nos Markdown originais.
- [x] 3.2 Modificar os metadados JSON no `database/br_mg_ouro_preto_ouroboulder/imagens/raw_mapas` aplicando o fator X e Y calculado.
- [x] 3.3 Modificar os atributos YAML originais `largura_mapa`, `altura_mapa` e todos os valores geográficos de colisão (`x`, `y`, `raio`, `comprimento`, `largura`) espelhados no diretório `database/br_mg_ouro_preto_ouroboulder/*.md`.

## 4. Finalização

- [x] 4.1 Compilar o dataset inteiro do `Ouroboulder` via `deploy_generated.py`.
- [x] 4.2 Validar a integridade rodando o utilitário do `binarypb`.
