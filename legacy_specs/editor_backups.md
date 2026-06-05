# Design Doc: Sistema de Backups via GitPython

## 1. Conceito Central
Em vez de implementar um sistema proprietário de backup, a ferramenta utiliza um repositório Git local oculto na pasta do croqui. O Git cuidará da compressão, delta de arquivos e integridade dos dados, enquanto a interface do usuário (PyQt6) abstrai toda a complexidade técnica (commits, hashes, branches).

## 2. Lógica de Automação
O ciclo de vida do histórico será dividido em dois tipos de registros:

### A. Checkpoints Automáticos (Auto-saves)
 * **Gatilho:** Toda vez que o botão "Compilar e Visualizar" for acionado ou a cada 5 minutos.
 * **Mensagem de Commit:** Padronizada como [AUTO] Checkpoint - 2026-04-29 10:30.

### B. Versões Nomeadas (Milestones)
 * **Gatilho:** Ação manual do usuário via botão "Salvar Versão Nomeada".
 * **Interface:** Abre um pequeno diálogo solicitando um nome (ex: "Antes da reboltagem do setor", "Finalizado desenho das vias").
 * **Implementação:** Utiliza **Git Tags** para marcar esses commits específicos, facilitando a recuperação rápida e garantindo que essas versões nunca sejam deletadas pela limpeza de checkpoints automáticos.

## 3. Estratégia de Integração na UI (PyQt6)
A interface deve ser minimalista para não intimidar o usuário leigo. Sugere-se uma aba dedicada chamada **"Histórico"**.
### Componentes de UI:
 1. **Lista de Atividade:** Um QListView ou QTableWidget exibindo o histórico de commits.
   * Ícones diferentes para distinguir o que é [AUTO] e o que é uma versão nomeada.
   * Exibição de tempo relativo (ex: "há 15 minutos", "ontem às 18:00").
 2. **Botão "Restaurar":** Ao selecionar uma versão na lista e clicar em restaurar, a ferramenta executa um git reset --hard para o hash selecionado.
 3. **Botão "Nomear Atual":** Um botão de destaque (estilo FAB ou no topo da lista) para criar uma versão nomeada a partir do estado atual da pasta.

## 4. Workflow de Recuperação
Caso o usuário "faça bobagem":
 1. Ele navega na lista de histórico até encontrar o ponto anterior ao erro.
 2. O sistema exibe um aviso: *"Isso irá substituir todos os arquivos atuais da pasta pelos arquivos desta versão. Deseja continuar?"*.
 3. Ao confirmar, o GitPython restaura os arquivos e a interface do PyQt6 atualiza a visualização do croqui automaticamente.

## 5. Vantagens Técnicas
 * **Eficiência de Espaço:** Como o Git armazena apenas as diferenças entre arquivos, o impacto no disco de salvar 100 versões de um croqui com fotos pesadas é muito menor do que fazer 100 cópias da pasta.
 * **Portabilidade:** Se o usuário mover a pasta do croqui para outro computador, o histórico vai junto dentro da subpasta oculta .git. Essa pasta, portanto, precisa ser empacotada junto no arquivo .croqui.

## 6. Considerações de Implementação
 * **Inicialização Silenciosa:** Se a ferramenta abrir um croqui que não tem um .git, ela deve executar git init e criar um .gitignore padrão (para ignorar arquivos temporários do sistema ou o próprio executável do compilador) sem incomodar o usuário.
 * **Binário do Git:** Para garantir que funcione em qualquer computador via PyInstaller, o Git precisa ser empacotado junto com o binário da ferramenta.