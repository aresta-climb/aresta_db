## Por que

Atualmente, a criação de um novo croqui é muito limitada: ela solicita apenas um ID e cria uma pasta vazia. Isso impede que o croqui seja compilado de imediato, exigindo que o usuário configure manualmente o arquivo `croqui.yaml`. Queremos que o usuário tenha um ambiente funcional e compilável assim que clicar em "Novo croqui".

## O que muda

- O botão "Novo croqui" deixará de pedir apenas um ID e passará a abrir um diálogo de criação detalhado.
- Coleta de metadados obrigatórios: Nome do pico de escalada, Cidade, Estado (2 letras) e País (2 letras).
- Geração automática e determinística do ID do croqui baseado nos metadados, seguindo o padrão `<pais>_<estado>_<cidade>_<nome_do_pico_em_camel_case>`.
- Criação automática do arquivo `croqui.yaml` inicial com os dados fornecidos.
- Execução de uma compilação inicial automática para a pasta `compilado`, garantindo que o setup esteja pronto para uso.

## Capacidades

### Novas Capacidades
- Nenhuma.

### Capacidades Modificadas
- `editor-tela-de-carregamento`: O cenário de "Novo croqui" será expandido para incluir o diálogo de metadados e a inicialização completa do ambiente do croqui.

## Impacto

- `editor/views/tela_de_carregamento.py`: Atualização da ação do botão "Novo croqui" e criação do novo diálogo.
- `editor/app/fluxo_carregamento.py` (ou serviço equivalente): Lógica para criar a estrutura inicial e disparar a primeira compilação.
- `compilador/`: Será utilizado para a compilação inicial.
