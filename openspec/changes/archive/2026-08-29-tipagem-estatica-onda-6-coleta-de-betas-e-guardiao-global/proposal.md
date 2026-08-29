# Proposta: Tipagem Estática Estrita - Onda 6: Coleta de Betas e Blindagem Global

## Por que

Com a conclusão das Ondas 1 a 5, cobrimos com sucesso os núcleos de dados, comandos, controladores, views PySide6, scripts de automação, migrações de dados, ferramentas de release e serving.

O único módulo de código de produção remanescente no repositório é o pacote coleta_de_betas/ (responsável pela inteligência e busca de vídeos de escalada via YouTube, DuckDuckGo e Vertex AI, persistência em Protobuf e interface gráfica de curadoria).

Além de concluir a tipagem estrita de 100% dos arquivos de coleta_de_betas/, a Onda 6 irá refatorar o teste guardião 	ests/tipagem_estatica_test.py para utilizar **descoberta dinâmica de arquivos** (
glob('*.py')) em vez de listas estáticas manuais. Isso garantirá uma **blindagem contínua**, onde qualquer novo módulo de produção adicionado ao repositório ou ao submódulo resta_api será imediatamente e compulsoriamente validado por análise de AST e MyPy estrito.

## O que será feito

- Anotar com tipagem estática estrita (typing, MyPy --strict, 100% de parâmetros e retornos explicitados) todos os 20 arquivos de produção de coleta_de_betas/.
- Tipar todos os submódulos: curadoria/, xtratores/, inteligencia/, persistencia/ e executores raiz.
- Assegurar compatibilidade de tipos em enums Protobuf (eta_pb2), interfaces de requisição HTTP e workers assíncronos do PySide6.
- Refatorar 	ests/tipagem_estatica_test.py para descobrir dinamicamente todos os módulos de produção do repositório e resta_api, eliminando a necessidade de registrar arquivos manualmente no futuro.
- Assegurar 100% de aprovação na suíte de testes (pytest com 1070+ testes).

## Critérios de Sucesso

- 0 erros reportados pelo MyPy sob configuração estrita (--strict) em 100% dos arquivos de código de produção do repositório.
- 0 funções ou métodos sem anotações completas de parâmetros ou retorno na inspeção sintática de AST.
- Teste guardião dinâmico aprovado para toda a árvore de produção de resta_db e resta_api.
- 100% de aprovação na suíte completa de testes do repositório (pytest).
