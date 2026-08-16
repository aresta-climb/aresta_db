## Context

A base de dados da ArestaDB, especificamente da Lapinha, é armazenada em arquivos estruturados (YAML). O usuário precisará realizar inspeções em campo (off-line) usando o Obsidian no celular. É necessário exportar o conteúdo do banco de dados em um formato que (1) seja fácil de preencher usando a interface de texto (Markdown) no celular, usando listas aninhadas, e (2) seja rigoroso o suficiente para permitir a reingestão automatizada na segunda etapa do fluxo.

## Goals / Non-Goals

**Goals:**
- Gerar os arquivos e diretórios seguindo a estrutura lógica: `setor/nome_da_via.md`.
- Inserir informações da via presentes no `aresta_db` (Nome, Conquistadores, Datas).
- Estabelecer um template predefinido para a avaliação da via (Estado, Informações Gerais) e proteção por proteção usando listas Markdown.

**Non-Goals:**
- **NÃO** é o objetivo deste script realizar a reingestão das anotações de volta para o banco de dados (isso será feito no futuro em outra funcionalidade).
- **NÃO** alterará dados existentes no `aresta_db`. O acesso à base de dados será apenas de leitura.

## Decisions

- **Uso de Python Script Independente:** Será criado um script Python independente na raiz ou pasta de scripts (ex: `export_obsidian_lapinha.py`) ao invés de alterar funcionalidades core. A razão é que se trata de uma ferramenta de operação iterativa (e descartável no médio prazo, se necessário) focada na UX do Obsidian.
- **Formato Markdown com Listas Aninhadas:** 
  - Optou-se por usar listas (bullet points) no corpo do markdown, ex:
    ```markdown
    - **Tipo:**
      - [ ] inox pingo
      - [ ] inox outro
    ```
  - **Rationale:** Aumenta muito a área de toque (tap target) para os usuários no smartphone. O usuário apenas dá um tap na linha e o check é marcado (quando usando plugins nativos ou compatíveis do Obsidian), evitando a digitação complexa em dispositivos móveis.
- **Tamanho Fixo de Proteções Pré-Geradas (16 proteções):** Como não se sabe o número exato de proteções antes do preenchimento, o template renderizará de "Top Rope 1" e "Top Rope 2" até a "Proteção 16". 
  - **Rationale:** O usuário em campo preencherá até onde houver proteções. É muito mais fácil ignorar campos vazios num scroll vertical do celular do que copiar e colar (ou digitar do zero) blocos complexos de markdown durante a inspeção na pedra.

## Risks / Trade-offs

- **[Risk] Mudança de Template no Celular** → Se o usuário modificar as linhas chaves (ex: `## Proteção 1` ou `- **Estado:**`) acidentalmente, o futuro script de parse poderá falhar ao extrair os dados.
  - *Mitigation:* A reingestão não é o escopo desta feature, mas a estrutura do markdown foi projetada com forte contraste (negrito + cabeçalhos) indicando onde o dado deve ser preenchido, minimizando toques acidentais em metadados vitais.
- **[Trade-off] Arquivos longos para vias curtas** → Criar campos vazios até a proteção 16 gera arquivos relativamente longos visualmente para vias curtas (ex: 5 proteções).
  - *Mitigation:* Esse trade-off é aceitável, dado que a UX no smartphone favorece scrolling rápido ao invés de edição de texto para duplicar "templates".
