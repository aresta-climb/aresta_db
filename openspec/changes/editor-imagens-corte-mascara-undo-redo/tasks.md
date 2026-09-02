## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [ ] 1.1 Criar casos de teste de integração em `editor/legacy_views/area_principal_imagens_integracao_test.py` (Red) validando o fluxo de rotação, corte por seleção e máscara com conta-gotas no `WidgetEditorImagens`, verificando a emissão de comandos para a pilha `QUndoStack`, a reversão com `Ctrl+Z` (Desfazer), refazer com `Ctrl+Y` e a sincronização com o modelo.

## 2. Biblioteca Pura de Transformações de Imagem (Princípio II - Library-First & Princípio IV - TDD)

- [ ] 2.1 Criar a suíte de testes unitários `editor/core/transformacoes_imagem_test.py` (Red) definindo os contratos para `rotacionar_imagem_bytes`, `cortar_imagem_bytes`, `aplicar_mascara_bytes` e `obter_cor_pixel`.
- [ ] 2.2 Implementar a biblioteca pura `editor/core/transformacoes_imagem.py` (Green) com manipulação de bytes WebP via Pillow sem dependência de interface gráfica.
- [ ] 2.3 Refatorar e assegurar 100% de cobertura de testes unitários na biblioteca de transformações (Refactor / Princípio III).

## 3. Rotação Integrada com Desfazer/Refazer (Princípio VII & Princípio IV - TDD)

- [ ] 3.1 Criar casos de teste unitários em `editor/legacy_views/widget_editor_imagens_test.py` (Red) para rotação horária (+90°) e anti-horária (-90°) acionando `CroquiController.substituir_imagem`.
- [ ] 3.2 Integrar os botões de rotação de `WidgetEditorImagens` com a biblioteca de transformações e o controlador de croqui (Green).

## 4. Modo Cortar Interativo por Seleção de Área (Princípio IV - TDD)

- [ ] 4.1 Criar casos de teste unitários em `editor/legacy_views/widget_editor_imagens_test.py` (Red) para o Modo Cortar (ativação, arrasto de seleção, corte imediato ao soltar o mouse, cancelamento com `Esc` e reversão com `Ctrl+Z`).
- [ ] 4.2 Implementar o Modo Cortar no visualizador do `WidgetEditorImagens`, removendo a caixa estática `CropBoxItem` e despachando o comando de corte para o controlador (Green).

## 5. Modo Máscara Direto com Conta-gotas (Princípio IV - TDD)

- [ ] 5.1 Criar casos de teste unitários em `editor/legacy_views/widget_editor_imagens_test.py` (Red) para o Modo Máscara (captura de cor, desenho de retângulo, preenchimento direto e reversão atômica via `Ctrl+Z`).
- [ ] 5.2 Implementar o Modo Máscara no `WidgetEditorImagens` utilizando `obter_cor_pixel` e `aplicar_mascara_bytes`, removendo `MaskBoxItem` e acúmulo de estados flutuantes (Green).

## 6. Limpeza de Interface e Remoção de Controles Obsoletos (Princípio VI - Simplicidade)

- [ ] 6.1 Remover os botões "Resetar" e "Limpar Máscaras" e renomear "Cortar (Preview)" para "Cortar" no `WidgetEditorImagens`.
- [ ] 6.2 Atualizar testes existentes em `widget_editor_imagens_test.py` e `scripts/editar_imagens_test.py` para refletir a nova interface limpa e simplificada.

## 7. Verificação de Cobertura e Integridade (Princípio III & Princípio I)

- [ ] 7.1 Executar a suíte completa de testes com medição de cobertura (`pytest --cov`) assegurando 100% de cobertura de código nos módulos novos e modificados.
- [ ] 7.2 Validar conformidade de tipagem e linters (`mypy` e `ruff`) e garantir que todo o código, docstrings e comentários estejam estritamente em português brasileiro.
