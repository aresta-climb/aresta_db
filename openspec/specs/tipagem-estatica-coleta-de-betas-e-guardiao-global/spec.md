# Spec: Tipagem Estática Estrita - Coleta de Betas e Guardião Global

## Escopo

Garantir 100% de tipagem estática estrita em todos os módulos de código de produção de coleta_de_betas/ e blindagem dinâmica no teste guardião 	ests/tipagem_estatica_test.py.

## Requisitos

1. Todos os 20 arquivos de coleta_de_betas/ devem passar em erificar_arquivo_ast (0 funções sem tipos).
2. Todos os arquivos de produção devem passar no MyPy sob configuração estrita (--strict).
3. 	ests/tipagem_estatica_test.py deve descobrir dinamicamente todos os módulos de produção do repositório sem listas manuais.
4. Suíte pytest com 100% de testes passando.
