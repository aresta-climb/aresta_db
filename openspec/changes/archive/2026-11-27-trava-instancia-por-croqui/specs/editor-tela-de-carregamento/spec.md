# Spec Delta

## ADDED Requirements

### Requirement: Prevenção de Reabertura de Croqui Já Aberto em Outra Janela
A `TelaDeCarregamento` MUST verificar antes de abrir um croqui do histórico, importar um croqui oficial ou criar um novo croqui se o identificador lógico correspondente já possui uma janela aberta em outra instância do Editor Aresta, elevando a janela existente sem abrir cópia duplicada.

#### Scenario: Seleção ou importação de croqui já aberto em outra instância
- **WHEN** o usuário solicita abrir um croqui experimental, importar um croqui oficial ou criar um croqui cujo `id_croqui` já está ativo em outra janela do editor
- **THEN** a `TelaDeCarregamento` MUST elevar a janela já aberta para o primeiro plano, informar o usuário por diálogo que o croqui já está aberto e permanecer sem iniciar edição duplicada
