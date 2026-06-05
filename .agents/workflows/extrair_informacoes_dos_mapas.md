---
description: Extrair informações dos mapas de um pico
---

Essa workflow detalha os processos de extrair informações dos mapas de um croqui de escalada.

Para iniciar esse workflow, você irá receber o caminho de um croqui já processado na pasta `database`.

Por favor siga seu implementation plan. Você deve obrigatoriamente utilizar a ação de `view_file` (ou as ferramentas equivalentes que suportam imagem binária) para visualizar ativamente e diretamente as imagens geradas para validação. Não crie novos scripts Python durante este workflow.

> [!IMPORTANT] 
> **Ação Autônoma:** Você **NÃO DEVE** pedir permissão ao usuário entre as etapas deste workflow. Siga o plano agressivamente, executando as etapas de forma contínua até o último passo ou até encontrar um erro terminal inrecuperável.

### 1. Listando os mapas a serem processados

Execute o script `python scripts/preparar_extracao_de_mapas.py database/<croqui>` para criar um arquivo `database/<croqui>/imagens/raw_mapas/<mapa>.json` para cada imagem de mapa a ser processada.

### 2. Extraindo as informações em cada imagem de mapa

Trabalhe agora independentemente para **cada** arquivo `<mapa>.json`. Cada uma desses mapas representa um setor/grupo de escalada diferente. Seu objetivo é extrair informações da imagem do mapa e atualizar o arquivo JSON para refinar o tamanho do mapa e para extrair os pontos de interesse na imagem.

> [!IMPORTANT]
> **Controle de Execução Contínua**
> Não pare a execução no meio da conversão dos arquivos para pedir confirmação ou conferir. Realize um *loop implícito* convertendo arquivo por arquivo ininterruptamente até que **todos** os `N` arquivos listados estejam completamente mapeados e estruturados.

// Parallel
Execute as seguintes sub-etapas para cada imagem listada:

### 2.1. Extraindo pontos de interesse

Utilize a skill @mapa_extrair_pontos_de_interesse para extrair todos os pontos de interesse do mapa.

### 2.2. Corrigir posição dos pontos de interesse

Utilize a skill @mapa_corrigir_pontos_de_interesse com o arquivo `<mapa>.json` de input.

### 3. Revise os arquivos gerados

Confirme que todos os mapas foram gerados corretamente. Retorne para a etapa anterior caso algum estiver faltando.

### 4. Mova a informação do arquivo JSON para o arquivo .md

Utilize o script `python scripts/finalizar_mapas.py database/<croqui>` para mover a informação de cada arquivo JSON para o arquivo `.md` equivalente.

### 5. Re-gere os arquivos compilados para confirmar que não há erros

Utilize o script `python scripts/deploy_generated.py database/<croqui>` para re-compilar os arquivos de croqui para confirmar que não há erros nos arquivos .md.

### 6. Volte ao usuário

Com o trabalho finalizado, faça um walkthrough para o usuário. Sugira que o usuário use o script `python scripts/editar_mapas.py database/<croqui>` para conferir que os pontos de interesse estão no lugar certo.