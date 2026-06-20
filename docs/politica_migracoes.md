# Política de Migrações de Dados do Aresta

Esta documentação estabelece as diretrizes e regras inegociáveis para a criação de scripts de migração na pasta `aresta_db/migracoes/`. Como o formato dos dados dos croquis baseia-se fortemente em arquivos YAML (Markdown Frontmatter) espalhados pelo repositório, qualquer alteração estrutural no Protobuf que resulte em "Breaking Changes" precisa ser retroativamente aplicada aos dados por meio de scripts de migração automatizados.

## 1. Localização e Nomenclatura

Todos os scripts de migração devem ser arquivos `.py` salvos no diretório `aresta_db/migracoes/`.
A nomenclatura deve OBRIGATORIAMENTE seguir o padrão sequencial:
`XXXX_nome_descritivo.py`

Onde `XXXX` é um número de 4 dígitos, zero-padded, sequencial (ex: `0001_migrar_secoes.py`, `0002_centralizar_map_references.py`).

A cada novo script, o desenvolvedor ou o agente autônomo deve analisar os arquivos já existentes e usar o próximo número disponível.

## 2. Paradigma TDD Obrigatório

A criação de migrações envolve alteração massiva dos dados em disco. Para mitigar o risco de corrupção ou perda de informações, é **Inegociável** que toda migração seja desenhada com base em TDD (*Test-Driven Development*).

### Regras do Ciclo:
1. **Red**: O arquivo de teste (ex: `0002_centralizar_map_references_test.py`) DEVE ser escrito ANTES do script de migração em si. Os testes falharão na primeira execução.
2. **Green**: O script de migração deve ser implementado focado única e exclusivamente em fazer os testes passarem.
3. **Refactor**: Opcionalmente o código da migração é limpo, garantindo que os testes continuem passando.

## 3. Cobertura de Testes (100% Coverage)

Scripts de migração não possuem margem para erros ou *edge cases* não testados. Portanto:
- A validação contínua e integração contínua rejeitarão qualquer script de migração que não atinja **100% de cobertura de código (Line Coverage)**.
- Recomenda-se criar suítes de testes que simulem o estado antes da migração (inclusive arquivos formatados fora do padrão e com comentários arbitrários) e validem detalhadamente o estado após a migração.
- Sempre verifique a cobertura usando: `pytest --cov=aresta_db/migracoes/<nome_da_migracao>.py aresta_db/migracoes/<nome_do_teste>.py`

## 4. Preservação de Comentários (ruamel.yaml)

Os arquivos YAML do projeto muitas vezes contêm anotações ou comentários deixados por editores e ferramentas. A biblioteca padrão `yaml` do Python descarta comentários durante o parsing. Para operações de leitura e escrita nos arquivos do banco de dados, os scripts de migração DEVEM utilizar a biblioteca `ruamel.yaml` em "RoundTrip mode", que garante a integridade completa dos comentários não estruturados originais.

## 5. Abordagem "Library-First"

A lógica de manipulação e transformação de dados DEVE ser desacoplada da rotina de iteração do CLI. O script deve expor funções puras (ex: `transformar_yaml_setor(yaml_dict)`) que recebem os dados carregados em memória e retornam os dados alterados. Isso simplifica o TDD, viabilizando testar a migração passando dicionários diretos, sem a necessidade constante de fazer Mocks custosos do `FileSystem`. Apenas os testes de integração deverão testar os fluxos de leitura e gravação em disco.
