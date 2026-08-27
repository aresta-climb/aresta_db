## 1. Atualização do Arquivo de Licença Raiz

- [x] 1.1 Substituir o conteúdo do arquivo `LICENSE` na raiz pelo texto oficial e integral da Mozilla Public License 2.0 (MPL 2.0)

## 2. Atualização dos Cabeçalhos SPDX no Código-Fonte

- [x] 2.1 Atualizar os identificadores SPDX nos arquivos Python da raiz (`build.py`, `build_test.py`, `conftest.py`) para `SPDX-License-Identifier: MPL-2.0`
- [x] 2.2 Atualizar os identificadores SPDX em todos os módulos de `coleta_de_betas/` para `SPDX-License-Identifier: MPL-2.0`
- [x] 2.3 Atualizar os identificadores SPDX em todos os módulos de `editor/` (models, views, controllers, commands, widgets) para `SPDX-License-Identifier: MPL-2.0`
- [x] 2.4 Atualizar os identificadores SPDX em scripts auxiliares do repositório (`database/**/limpar_imagens_ouroboulder.py`, etc.) para `SPDX-License-Identifier: MPL-2.0`

## 3. Atualização da Documentação

- [x] 3.1 Atualizar `LICENCAS_RESUMO.md` explicando detalhadamente o funcionamento do copyleft a nível de arquivo da MPL 2.0
- [x] 3.2 Atualizar `README.md` com a menção à licença MPL 2.0 para o motor de processamento

## 4. Testes e Validação

- [x] 4.1 Criar teste automatizado de verificação de conformidade de licença para validar que nenhum arquivo `.py` de código contenha `GPL-3.0` e que todos possuam cabeçalho SPDX adequado
- [x] 4.2 Executar a suíte de testes completa (`pytest`) e verificar que todos os testes passam com 100% de sucesso
