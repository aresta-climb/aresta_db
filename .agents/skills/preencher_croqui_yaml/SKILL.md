---
name: preencher_croqui_yaml
description: Gera o arquivo final croqui.yaml e compila o projeto até que não existam erros ou warnings.
---

# Preenchimento e Compilação do Croqui

Sua missão é gerar o arquivo `croqui.yaml` e garantir que o croqui compile
perfeitamente, sem nenhum erro ou aviso.

Para esta tarefa, você receberá o caminho para a pasta do croqui dentro de
`database/`.

## 1. Criação ou Atualização do arquivo `croqui.yaml`

Primeiro, verifique se o arquivo `croqui.yaml` já existe na pasta
(`database/<croqui>/croqui.yaml`).

- **Se já existir**: Não o recrie do zero para não sobrescrever possíveis
  edições manuais feitas pelo humano. Apenas confira se ele está íntegro e
  avance para a etapa de compilação.
- **Se não existir**: Gere o arquivo `croqui.yaml` do zero. Este arquivo unirá
  todos os arquivos `.md` gerados na fase de conversão.
  - Utilize a opção de `caminho` dos oneofs de arquivo (conforme descrito em
    `aresta_api/proto/croqui.proto`) para apenas listar os caminhos relativos
    dos arquivos `.md`, sem incluir o conteúdo deles diretamente no YAML.
  - **Defina obrigatoriamente** o campo `ultima_migracao` com o ID numérico da
    migração mais recente presente no diretório `migracoes/` (por exemplo, `1`).
    Você pode checar o diretório usando tools se não tiver certeza.
  - Sempre preencha o `caminho_thumbnail` com a mesma imagem que está
    referenciada na capa, se houver. Alternativamente, escolha uma imagem
    representativa para o croqui dentre as imagens disponíveis.
  - **NUNCA** adicione marcações aos campos `revisado_*`, pois eles são
    reservados para a verificação humana futura.

## 2. Preparação e Compilação em Loop (Test-Driven)

Após gerar o `croqui.yaml`, você deve validar ativamente o projeto inteiro:

1. Execute o comando `python scripts/deploy_generated.py database/<croqui>`.
   - Este script corrige os caminhos das imagens nos arquivos `.md` e gera os
     arquivos compilados na pasta `generated/<croqui>` (`compilado.yaml` e
     `compilado.binarypb`).
   - **IMPORTANTE:** O script pode falhar, retornar exceções, ou apresentar
     **warnings**. Se isso acontecer, você **DEVE** corrigir os problemas de
     forma autônoma. Leia as mensagens, identifique o problema (pode ser sintaxe
     errada no `croqui.yaml` ou marcação/identação YAML errada dentro de um dos
     arquivos `.md` previamente gerados), use a tool de editar o arquivo
     problemático corrigindo-o, e execute `deploy_generated.py` novamente. Por exemplo, erros do tipo `unknown field 'id_no_mapa'` indicam que agentes geraram a estrutura antiga e você deve mover esses ids para o objeto de `mapas` e suas referências.
   - Repita esse processo quantas vezes for necessário, até o script rodar com
     sucesso absoluto (**ZERO erros e ZERO warnings**).

2. Assim que o deploy for um sucesso absoluto, execute o comando
   `python scripts/verificar_binarypb.py database/<croqui>/compilado.binarypb`.
   - Se este comando retornar qualquer erro de parsing ou validação no protobuf,
     isso significa que ainda existem arquivos mal formatados.
   - Edite os arquivos com defeito e volte imediatamente ao passo 1, rodando
     `deploy_generated.py` novamente, até que ambos os scripts passem de
     primeira sem relatar erros.

## Quando usar essa habilidade

Use essa habilidade quando precisar concluir o pipeline de conversão de Markdown
gerando o `croqui.yaml` raiz e compilando a pasta inteira até a estrita
validação técnica do compilador e verificador de binários do Protobuf.
