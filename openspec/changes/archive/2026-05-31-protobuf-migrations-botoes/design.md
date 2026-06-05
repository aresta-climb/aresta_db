## Context

Atualmente, quando ocorrem breaking changes na API do Protobuf, dezenas de croquis existentes têm sua compilação quebrada por possuírem campos antigos ou inexistentes em seus arquivos fonte (`croqui.yaml` e arquivos `.md`). Para corrigir este cenário, introduziremos um sistema resiliente de migrações offline e sequenciais executadas tanto no pipeline de compilação quanto na inicialização/carregamento do Editor Aresta.

## Goals / Non-Goals

**Goals:**
- Implementar um motor de migração offline sequencial baseado em números inteiros de 4 dígitos (`0001`, `0002`...).
- Registrar no schema (`croqui.proto`) e no arquivo `croqui.yaml` de cada croqui a versão da última migração aplicada (usando um inteiro).
- Executar migrações automaticamente no pipeline de deploy (`preparar_submissao_lib.py`) e no carregamento do Editor (`area_principal.py`).
- Desenvolver a biblioteca de testes auxiliares em `scripts/helpers_migracao.py`.
- Desenvolver a migração para converter a estrutura obsoleta de `secoes_textuais` / `arquivos_markdown` em `botoes` (oneof `DestinoBotao`).

**Non-Goals:**
- Oferecer rollback automatizado de migração pelo sistema (o controle e reversão são garantidos pelo histórico Git do repositório).
- Construir interface gráfica no editor para seleção manual de migrações.

## Decisions

### 1. Versionamento Sequencial e Linear (`0001`, `0002`...)
- **Decisão:** Usar identificadores numéricos de 4 dígitos em ordem estrita.
- **Racional:** Força uma história linear estrita. Ao usar números sequenciais, caso dois desenvolvedores tentem criar migrações independentes com o mesmo ID, o Git gerará um conflito de mesclagem, o que é um comportamento desejável pois obriga os desenvolvedores a resolver a ordem e a numeração conscientemente. Isso também impede que migrações sejam puladas (o que ocorreria no caso de timestamps se um croqui marcasse um timestamp posterior e posteriormente recebesse arquivos com timestamps anteriores).
- **Alternativa Considerada:** Versionamento por timestamps (`YYYYMMDD_HHMM`). Rejeitada devido ao risco de migrações anteriores serem puladas silenciosamente após o croqui ter sido atualizado por um timestamp posterior.


### 2. Execução da Migração na Leitura (Load) e Compilação (Compile)
- **Decisão:** Chamar a migração logo antes de ler o `croqui.yaml` no editor e antes de iniciar a compilação oficial (`corrigir_database`).
- **Racional:** Garante que o arquivo no disco seja migrado para a versão mais recente *antes* que a biblioteca de parsing lance erros por ler campos inválidos.
- **Alternativa Considerada:** Executar migrações apenas sob demanda via linha de comando. Rejeitada porque o usuário do Editor teria falhas imediatas ao tentar abrir croquis de versões anteriores.

### 3. Scripts de Migração programados em Python
- **Decisão:** Cada mudança de schema será um script Python independente que exporta a função `migrar(croqui_dir: Path)`.
- **Racional:** Oferece máxima flexibilidade para atualizar não apenas propriedades no YAML (`croqui.yaml`), mas também manipular o frontmatter e o conteúdo dos markdowns correspondentes.

### 4. Inicialização Automática de Versão para Novos Croquis
- **Decisão:** Novos croquis inicializados no editor ou gerados por workflows de conversão devem ter o campo `ultima_migracao` preenchido com o maior ID de migração disponível na pasta `migracoes/`.
- **Racional:** Evita que croquis novos sejam tratados como obsoletos pelo migrador, prevenindo tentativas desnecessárias de migração ao compilar pela primeira vez.

### 5. Idempotência Fina (No-Op)
- **Decisão:** Garantir que scripts de migração individual (como `0001`) retornem imediatamente sem tocar ou reescrever o arquivo yaml físico se os campos antigos correspondentes não existirem mais no arquivo yaml, mesmo que a propriedade `ultima_migracao` esteja ausente no documento.
- **Racional:** Evita IO de gravação desnecessário, logs de reescrita em produção e chances de corrupção ou lock de arquivos.

## Risks / Trade-offs

- **[Risco] Escrita simultânea ou corrupção de arquivos** -> **Mitigação:** Exigir teste de 100% de cobertura para cada migração individual rodando em diretórios temporários antes de enviar o código, além do uso de tratamento robusto de arquivos para gravação segura.
- **[Risco] Bloqueio de arquivos por permissões ou locks no Windows** -> **Mitigação:** Utilizar retry automático com atraso e limpeza de permissões de leitura (chmod) em operações de disco, seguindo as utilidades já utilizadas em `deploy_generated.py`.
- **[Risco] Testes redundantes lentos** -> **Mitigação:** Criação de testes unitários isolados para o `migrador` utilizando mocks para a classe `Path`, permitindo executar todos os cenários sem precisar tocar na pasta de migrações reais do Git.

