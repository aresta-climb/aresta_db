## 1. Modificações no Protobuf

- [x] 1.1 Adicionar mensagens `PrecomputadosSetor`, `PrecomputadosGrupo` e `PrecomputadosPico` no `aresta_api/proto/croqui.proto`.
- [x] 1.2 Incluir campos correspondentes nas mensagens `Setor`, `Grupo` e `Pico` marcados como invisíveis na UI.
- [x] 1.3 Adicionar mensagem `PrecomputadosResumoCroqui` no `aresta_api/proto/indice.proto`.
- [x] 1.4 Adicionar o novo campo de precomputados no `ResumoCroqui`.

## 2. Lógica de Agregação no Build

- [x] 2.1 Criar função `computar_precomputados_setor` em `scripts/preparar_submissao_lib.py`.
- [x] 2.2 Criar função `computar_precomputados_grupo` em `scripts/preparar_submissao_lib.py`.
- [x] 2.3 Criar função `computar_precomputados_pico` em `scripts/preparar_submissao_lib.py`.
- [x] 2.4 Criar a orquestradora `injetar_precomputados(croqui_data)` que chama as três funções em ordem.
- [x] 2.5 Invocar `injetar_precomputados` dentro da `compilar_croqui`.

## 3. Repasse para o Índice

- [x] 3.1 Atualizar `passo_c_gerar_indice` em `scripts/deploy_generated.py` para extrair os totais (escaladas, setores e grupos) iterando os picos do croqui compilado.
- [x] 3.2 Injetar a mensagem calculada no campo `precomputados` de cada novo item `ResumoCroqui`.

## 4. Testes e Validação

- [x] 4.1 Executar a rotina de compilação completa localmente (`python scripts/deploy_generated.py`).
- [x] 4.2 Validar o `compilado.yaml` gerado de um croqui para garantir os totais corretos de Setor, Grupo e Pico.
- [x] 4.3 Validar o `indice.yaml` para garantir que o resumo está recebendo a consolidação correta.
