## Context

A aplicação possui atualmente uma `PaginaInicial` que serve como o primeiro estado após a tela de abertura. Ela contém botões para criar/importar croquis e uma lista de croquis experimentais locais. No entanto, ela ocupa todo o espaço da janela principal (`QMainWindow`), o que não condiz com sua função de "ponto de partida" ou "tela de carregamento".

## Goals / Non-Goals

**Goals:**
- Transformar a `PaginaInicial` em uma `TelaDeCarregamento` compacta e visualmente centralizada.
- Implementar um layout vertical dividido em duas partes claras: botões de ação no topo e histórico de croquis na base.
- Garantir que a interface informe o usuário quando não houver croquis experimentais ("Nenhum croqui no histórico").
- Manter a funcionalidade de carregamento de croquis a partir do disco.

**Non-Goals:**
- Implementar novas funcionalidades de negócio ou fluxos de criação nesta etapa.
- Alterar a persistência de dados.

## Decisions

- **Widget vs Diálogo**: Optamos por transformar a `TelaDeCarregamento` em um `QDialog` independente em vez de um widget dentro de um stack. Isso permite que a interface seja compacta e flutuante, eliminando o espaço vazio da `JanelaPrincipal` durante a seleção inicial.
- **Fluxo de Navegação**: A `JanelaPrincipal` (Editor) só será exibida após o usuário realizar uma escolha no diálogo de carregamento ou após o fechamento do diálogo.
- **Nomenclatura Completa**: Os botões retornarão aos seus nomes originais mais descritivos: "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial".

## Risks / Trade-offs

- **[Risk] Centralização Visual** → Ao usar um `QDialog`, o sistema operacional gerencia a janela, mas garantimos um tamanho fixo (`setFixedSize`) para manter a proporção compacta.
- **[Trade-off] Diálogo Modal** → Optamos por um diálogo modal para impedir que o usuário acesse o editor sem antes selecionar um contexto de trabalho, garantindo a integridade do estado inicial.
