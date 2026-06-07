## 1. Preparação (Recursos Visuais)

- [x] 1.1 Copiar os arquivos `logo_splash.png` e `logo_app.png` de `../aresta_app/frontend/assets/` para um novo diretório `editor/recursos/` no repositório local do `aresta_db`.
- [x] 1.2 Atualizar as configurações de build do PyInstaller (`editor/ArestaEditor.spec` ou script correspondente) para incluir a nova pasta `editor/recursos/` nos artefatos `datas` empacotados.

## 2. Testes (TDD)

- [x] 2.1 Adicionar testes em `editor/views/tela_de_abertura_test.py` para verificar se a logo oficial é carregada em `TelaDeAbertura` usando o novo caminho (`editor/recursos/logo_splash.png`).
- [x] 2.2 Adicionar testes em `editor/views/tela_de_abertura_test.py` simulando `QTest.mousePress` e `QTest.mouseMove` na `TelaDeAbertura` para verificar se a posição da janela se altera (arrasto).

## 3. Implementação (Atualização Visual e Arrasto)

- [x] 3.1 Atualizar a `TelaDeAbertura` (`editor/views/tela_de_abertura.py`) para renderizar a imagem usando o novo caminho local (`editor/recursos/logo_splash.png`), substituindo o ícone anterior genérico.
- [x] 3.2 Reimplementar `mousePressEvent` em `TelaDeAbertura` para capturar a posição inicial do clique em `self._drag_pos`.
- [x] 3.3 Reimplementar `mouseMoveEvent` em `TelaDeAbertura` para invocar `self.move()` com o delta calculado, fazendo os testes de arrasto passarem.
