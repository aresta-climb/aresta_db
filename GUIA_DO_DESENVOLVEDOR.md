# Guia do Desenvolvedor: ArestaDB

Bem-vindo ao manual técnico do ecossistema Aresta. Se você é um desenvolvedor, engenheiro de dados ou agente autônomo, este guia contém tudo o que você precisa para configurar o ambiente e processar novos dados.

## ⚠️ Princípios de Desenvolvimento Obrigatórios

Todos os desenvolvedores e agentes autônomos (Google Antigravity, OPSX) trabalhando neste repositório **DEVEM** ler e seguir rigorosamente as regras definidas em [PRINCIPIOS.md](PRINCIPIOS.md).

Isso garante a coesão, simplicidade e testabilidade de todo o código gerado.

## Setup do Ambiente

### Instale o Google Antigravity
Usamos o Google Antigravity para workflows agênticos.
👉 [Download do Antigravity](https://antigravity.google/download)

### Runtime Python e uv
Usamos o gerenciador de pacotes **uv** e o Python 3.13 (pois o framework PaddlePaddle ainda não suporta Python 3.14).
👉 [Instruções Oficiais de Instalação do uv](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Instale o PaddlePaddle
Caso você vá extrair informações de mapas e imagens com OCR, é necessário instalar o PaddlePaddle:
👉 [Instruções Oficiais do PaddlePaddle](https://www.paddlepaddle.org.cn/en/install/quick)

### 2. Instale o Graphviz
Caso você vá gerar visualizações em grafo (ex: uso do protobuf para modelar os relacionamentos da base), o sistema requer o binário do Graphviz instalado nativamente no seu sistema operacional:
👉 [Download do Graphviz](https://graphviz.org/download/)

### 3. Sincronize o Ambiente e Dependências com o uv
Após clonar o repositório, basta sincronizar o ambiente virtual executando na raiz:

```bash
uv sync --all-groups
```

O `uv` provisionará automaticamente o interpretador Python 3.13 fixado e instalará todas as dependências do projeto e dos grupos de desenvolvimento (`dev`, `editor`, `deploy`, `validator`) de acordo com o `uv.lock`.

Para executar a suíte de testes:
```bash
uv run pytest
```

---

## Como Converter um Novo Croqui PDF

O motor do Aresta possui um pipeline para converter antigos guias de escalada (PDFs) em dados estruturados (YAML/Markdown).

1. **Inicie a conversão chamando o orquestrador pelo agente (Antigravity):**
   Digite `/processar_croqui_completo` e forneça o caminho do PDF do croqui no chat.
   O orquestrador guiará o processo em 3 fases: Preparação, Conversão e Extração de Mapas.

2. **Validação Humana:**
   Durante o processo, o agente fará paradas estratégicas (Checkpoints) solicitando que você valide os dados gerados usando o Editor de Croquis.

### Desenvolver o Editor de Croquis (Interface Visual)

O editor de croquis é uma interface gráfica local para auxiliar a validação humana dos dados extraídos pela IA antes de irem para o banco. 

Para abrir o editor com o ambiente gerenciado pelo `uv`, execute simplesmente:
```bash
uv run editor/main.py
```


#### Modo local
O editor também suporta um modo que faz atualizações dos croquis diretamente no repositório ao invés de criar pull requests com as mudanças.

Para abrir o editor nesse modo, execute o `editor/main.py` passando o caminho para o croqui que você quer editar:
```bash
uv run editor/main.py database/<pais>_<estado>_<cidade>_<pico_de_escalada>
```

**Exemplo:**
```bash
uv run editor/main.py database/br_mg_ouro_preto_ouroboulder
```
## 📜 Certificado de Origem do Contribuidor (DCO)

Para garantir que todo código enviado tem procedência limpa, usamos o **Developer Certificate of Origin (DCO)**. Cada commit deve ser assinado com a flag `-s` ou `--signoff`, que adiciona a linha:

```
Signed-off-by: Seu Nome <seu.email@exemplo.com>
```

O DCO completo está disponível abaixo ou no texto oficial em https://developercertificate.org/.

Ao abrir um Pull Request, o CI verifica automaticamente a presença da assinatura. Se faltar, o PR será bloqueado até que o commit seja assinado.

**Como assinar rapidamente:**

- **Git**: `git commit -s -m "msg"`
- **VS Code**: habilite *Git: Always Sign Off* nas configurações.
- **IntelliJ / WebStorm**: marque *Sign‑off commit* na janela de commit.

---

### Texto Oficial Legal do DCO (Em Inglês)

Para validade jurídica internacional, abaixo consta o texto oficial do
[Developer
Certificate of Origin, Versão 1.1](https://developercertificate.org/):

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    this project or the open source license(s) involved.
```

---

### Tradução de Cortesia (Em Português)

> **Aviso Legal:** A tradução abaixo é fornecida apenas como cortesia para
> facilitar o entendimento da comunidade. O texto que possui validade jurídica e
> governa as contribuições para este projeto é o texto oficial em inglês acima.

```text
Certificado de Origem do Desenvolvedor
Versão 1.1

Copyright (C) 2004, 2006 The Linux Foundation e seus contribuidores.

Ao fazer uma contribuição para este projeto, eu certifico que:

(a) A contribuição foi criada no todo ou em parte por mim e eu
    tenho o direito de enviá-la sob a licença de código aberto
    indicada no arquivo; ou

(b) A contribuição é baseada em trabalho anterior que, até onde
    é do meu conhecimento, está coberto sob uma licença de código
    aberto apropriada e eu tenho o direito sob essa licença de enviar
    este trabalho com modificações, seja criado no todo ou em parte
    por mim, sob a mesma licença de código aberto (a menos que eu
    tenha permissão para enviar sob uma licença diferente), conforme
    indicado no arquivo; ou

(c) A contribuição me foi fornecida diretamente por outra pessoa
    que certificou (a), (b) ou (c) e eu não a modifiquei.

(d) Eu entendo e concordo que este projeto e a contribuição
    são públicos e que um registro da contribuição (incluindo todas
    as informações pessoais que eu enviar com ela, incluindo a minha
    assinatura) é mantido indefinidamente e pode ser redistribuído
    de forma consistente com este projeto ou com a(s) licença(s)
    de código aberto envolvida(s).
```