# Legacy Views

Este diretório contém os componentes de interface que foram construídos antes da adoção da arquitetura MVC Estrita orientada a comandos do Aresta Editor.

Eles ainda misturam lógica de interface, orquestração de histórico e estado, e portanto **não devem ser usados como referência** para novas implementações. A manutenção nestes arquivos deve focar em não quebrar o ecossistema existente até que entrem no fluxo de migração para as camadas `models/`, `views/` e `controllers/`.
