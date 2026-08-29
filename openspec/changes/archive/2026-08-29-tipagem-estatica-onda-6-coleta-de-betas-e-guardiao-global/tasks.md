# Tarefas de Implementacao: Tipagem Estatica Estrita - Onda 6

## 1. Coleta de Betas - Nucleo e Orquestradores

- [x] 1.1 Anotar com tipagem estatica estrita os modulos raiz de coleta_de_betas: buscar.py, extrair_vias.py, extrator_vias.py, io_yaml.py, runner_busca.py, runner_staging.py, salvar_staging.py e __init__.py.

## 2. Coleta de Betas - Extratores, Inteligencia, Persistencia e Curadoria

- [x] 2.1 Anotar com tipagem estatica estrita os extratores (deduplicador.py, duckduckgo.py, vertex.py, youtube.py e __init__.py).
- [x] 2.2 Anotar com tipagem estatica estrita os modulos de inteligencia e persistencia (avaliador.py, salvamento.py e __init__.py).
- [x] 2.3 Anotar com tipagem estatica estrita os modulos de interface grafica de curadoria (carregador_imagens.py, painel_curadoria.py e __init__.py).

## 3. Blindagem Global do Guardiao de Testes

- [x] 3.1 Refatorar tests/tipagem_estatica_test.py para descobrir dinamicamente todos os modulos .py de producao (via rglob/scandir) e validar que nao ha listas manuais estaticas.
- [x] 3.2 Validar conformidade de 100% dos arquivos descobertos contra o MyPy estrito e validador AST.

## 4. Validacao Global do Repositorio

- [x] 4.1 Executar a suite completa de testes (pytest com 1070+ testes) assegurando 100% de aprovacao e zero depressoes de tipagem.
