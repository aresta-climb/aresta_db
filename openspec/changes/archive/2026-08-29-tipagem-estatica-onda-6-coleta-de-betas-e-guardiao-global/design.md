# Design Técnico: Tipagem Estática Estrita - Onda 6

## Arquitetura e Estratégia de Tipagem

### Grupo 1: Núcleo e Orquestradores do coleta_de_betas
- coleta_de_betas/__init__.py: Inicializador de pacote.
- coleta_de_betas/buscar.py, xtrair_vias.py, xtrator_vias.py: Tipagem de parsing de YAMLs, extração de vias e estruturas de busca.
- coleta_de_betas/io_yaml.py, 
unner_busca.py, 
unner_staging.py, salvar_staging.py: Tipagem de serialização e CLI com Sequence[str] e Optional[List[str]].

### Grupo 2: Extratores, Inteligência, Persistência e Curadoria
- coleta_de_betas/extratores/ (deduplicador.py, duckduckgo.py, ertex.py, youtube.py):
  - Tipagem de requisições HTTP (
equests.Response, params: Dict[str, Union[str, int]]), duck-typing de clientes de busca via protocolo ou classe base comum.
- coleta_de_betas/inteligencia/avaliador.py:
  - Tipagem de validação de pontuação semântica e carregamento de staging binarypb.
- coleta_de_betas/persistencia/salvamento.py:
  - Manipulação de eta_pb2.BetasPendentesPorCroqui e atribuições de campos Protobuf.
- coleta_de_betas/curadoria/ (carregador_imagens.py, painel_curadoria.py):
  - Tipagem de widgets PySide6, workers em threads e conversão de enums eta_pb2.StatusValidacaoHumana.

### Grupo 3: Guardião Global Dinâmico
- 	ests/tipagem_estatica_test.py:
  - Substituição das listas manuais (ARQUIVOS_CORE_ONDA_2, ARQUIVOS_ONDA_3, etc.) por uma função de descoberta dinâmica obter_arquivos_producao_repositorio().
  - Critérios de exclusão bem delimitados (diretórios gerados, caches, venv, arquivos de teste *_test.py).
  - Validação universal por MyPy e AST.
