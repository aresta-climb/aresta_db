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

Comece com a workflow `preparacao_pdf_para_conversao`. Chame essa workflow com o caminho do PDF do croqui a ser convertido, e siga as instruçõest