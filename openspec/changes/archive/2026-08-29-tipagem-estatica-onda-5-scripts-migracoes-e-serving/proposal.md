# Proposta: Tipagem Estática Estrita - Onda 5: Scripts, Migrações, Release Tools e Serving

## Por que

Após a conclusão das Ondas 1 (Infraestrutura), 2 (Núcleo de Dados/Core), 3 (Comandos e Controladores) e 4 (Views e UI PySide6), o ecossistema de suporte do repositório — que inclui os scripts utilitários de compilação, o pipeline de migrações de dados Protobuf, as ferramentas de release e o serviço de validação/serving de PRs — ainda opera com tipagem dinâmica sem anotações completas.

Garantir tipagem estática estrita nesses módulos é essencial para:
1. Prevenir regressões e falhas em pipelines de CI/CD durante validação de dados e migrações de esquema.
2. Fornecer contratos de tipo confiáveis para scripts executados em lote no banco de dados e na exportação de croquis.
3. Assegurar conformidade universal no MyPy estrito e no metateste sintático AST em todo o ferramental de automação.

## O que será feito

- Anotar com tipagem estática estrita (typing, MyPy --strict, 100% de parâmetros e retornos explicitados) todos os módulos dos pacotes scripts/, migracoes/, serving/ e ditor/release_tools/.
- Tipar o proxy utilitário remanescente ditor/models/readonly_proxy.py.
- Integrar todos os módulos da Onda 5 na suíte guardiã 	ests/tipagem_estatica_test.py com validação de conformidade AST e MyPy.
- Assegurar 100% de aprovação na suíte de testes do repositório (pytest).

## Critérios de Sucesso

- 0 erros reportados pelo MyPy sob configuração estrita nos módulos da Onda 5.
- 0 funções ou métodos sem anotações de parâmetros ou retorno na inspeção de AST.
- 100% de aprovação na suíte completa de testes (pytest).
