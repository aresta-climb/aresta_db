## 1. Infraestrutura e Dependências

- [x] 1.1 Adicionar `qtawesome` ao arquivo `editor/requirements.txt`.
- [x] 1.2 Criar o módulo `editor/views/estilo.py` (ou atualizar se existir) com a classe `Icones` para centralizar o mapeamento de ícones e cores.

## 2. Testes de Integração e Unidade

- [x] 2.1 Criar ou atualizar `editor/views/area_principal_test.py` com testes que validem a atribuição dos novos ícones aos botões da interface.
- [x] 2.2 Criar `editor/views/estilo_test.py` para validar o helper `Icones` e o mapeamento de ícones.

## 3. Implementação da Interface

- [x] 3.1 Atualizar a `Top Toolbar` em `editor/views/area_principal.py` para utilizar os ícones premium mapeados.
- [x] 3.2 Atualizar a `Side Toolbar` em `editor/views/area_principal.py` para utilizar os ícones premium mapeados.
- [x] 3.3 Implementar alinhamento pixel-perfect (82px largura / 63px spacer / 6px margens).
- [x] 3.4 Implementar logo de montanha Verde Musgo com efeito de opacidade.
- [x] 3.5 Corrigir avisos de `QFont::setPointSize` migrando para unidades `pt` e definindo fonte base na janela.

## 4. Validação e Build

- [x] 4.1 Executar a suite de testes completa do editor (`python editor/build.py test`).
- [x] 4.2 Adicionar teste de regressão para capturar avisos de fonte via `qInstallMessageHandler`.
- [x] 4.3 Executar o editor localmente para validação visual humana.
- [x] 4.4 Verificar se o empacotamento via PyInstaller continua incluindo os recursos necessários.
