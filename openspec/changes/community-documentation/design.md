## Context

O repositório `aresta_db` transcende um mero banco de dados: ele é a fonte da verdade comunitária da escalada. Pela própria natureza do projeto, os catalogadores (montanhistas/escaladores) são especialistas verticais, mas frequentemente não possuem nenhum letramento em desenvolvimento de software (Git, Github, Branches). A atual ausência de um caminho desenhado para este perfil de usuário resulta em medo técnico e afasta potenciais contribuidores valorosos. A documentação deve servir como o "tapete vermelho" que traduz processos altamente complexos em interações triviais de um software comum.

## Goals / Non-Goals

**Goals:**
- Estruturar o `README.md` como uma vitrine acolhedora, deixando a missão do banco de dados exposta e direcionando o tráfego para a contribuição.
- Construir o arquivo `docs/COMO_CONTRIBUIR.md` num funil educacional em 4 etapas (Conta Github -> Download do Editor -> Uso Básico -> Publicação).
- Hospedar todo e qualquer material de apoio visual (Screenshots/Diagramas simplificados) dentro do diretório padronizado `docs/assets/`.

**Non-Goals:**
- Não criar um manual pesado em texto. O foco é ser prático, visual e pontual.
- Não expor o usuário aos conceitos de Branching, Commits, Rebase ou Forking. O universo do usuário resume-se a: Logar, Editar e Sugerir (Publish).

## Decisions

1. **Jargão de Transição: "Pull Request" vira "Sugerir Alteração"**
   - *Rationale*: Omissão completa da palavra "Pull Request" criaria atrito caso o GitHub (ou o editor) a apresentasse num botão, gerando pânico.
   - *Abordagem*: A documentação abordará o termo como uma formalidade: *"Quando você clica em publicar, o sistema cria uma **Pull Request (PR)**. Isso não é nada mais do que uma Sugestão de Alteração que entrará em uma fila para ser validada pelos mantenedores antes de ir para o App."*

2. **Armazenamento Local e Relativo de Assets**
   - *Rationale*: Links de hospedagem de imagens de terceiros "quebram" com o tempo, e colar nas issues do Github polui tickets.
   - *Abordagem*: Criação iminente do diretório `docs/assets/`. Todo markdown dentro de `docs/` invocará as imagens de forma local relativa (`./assets/exemplo.png`), tornando o versionamento orgânico e portável.

3. **Promoção Forte do Link Customizado e do Auto-Updater**
   - *Rationale*: Reduzir a fricção cognitiva das dolorosas versões de software (v1.0, v2.1).
   - *Abordagem*: Centralizar o redirecionamento num domínio bonito (`arestaclimb.com/download-editor`). Mais importante: imprimir na documentação a regra de ouro construída na Fase 3: *"Baixe apenas uma vez. Deixe o Aresta Editor atualizar a si mesmo para sempre."*
