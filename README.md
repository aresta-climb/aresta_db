# aresta-db
Database de croquis do Aresta.

## ⚠️ Princípios de Desenvolvimento Obrigatórios

Todos os desenvolvedores e agentes autônomos (Google Antigravity, OPSX) trabalhando neste repositório **DEVEM** ler e seguir rigorosamente as regras definidas em [PRINCIPIOS.md](PRINCIPIOS.md).
Isso garante a coesão, simplicidade e testabilidade de todo o código gerado.

## Setup

### Runtime python

Use Python 3.13, pois PaddlePaddle não suporta Python 3.14.

#### Instale PaddlePaddle

Caso você for extrair informações de mapas, instale o PaddlePaddle:
https://www.paddlepaddle.org.cn/en/install/quick

#### Instale Graphviz

Caso você vá gerar visualizações em grafo (ex: uso do protobuf), o sistema requer o binário do Graphviz instalado:
https://graphviz.org/download/

#### Instale dependências Python

Após instalado, instale as dependências em requirements.txt antes de rodar quaisquer scripts:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-deploy.txt
```

## Como converter um novo croqui PDF

1. Inicie a conversão chamando o orquestrador pelo agente (Antigravity):
   Digite `/processar_croqui_completo` e forneça o caminho do PDF do croqui.
   O orquestrador guiará o processo em 3 fases (Preparação, Conversão e Extração de Mapas).

2. Durante o processo, o agente fará paradas estratégicas (Checkpoints) solicitando que você valide os dados gerados usando o Editor de Croquis.

### Dependências do Editor

O editor de croquis é uma interface gráfica para auxiliar a validação. Antes de abri-lo pela primeira vez, certifique-se de instalar suas dependências:

```bash
python -m pip install -r editor/requirements.txt
```

Para rodar o editor para inspecionar e revisar um croqui específico:
```bash
python editor/main.py database/<pais>_<estado>_<cidade>_<pico_de_escalada>
```