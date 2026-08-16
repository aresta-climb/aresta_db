## Context

A arquitetura de distribuição atual baseia-se num executável `--onefile` gerado pelo PyInstaller. Pela ausência de um framework dedicado de deployment corporativo, a responsabilidade de "secregar" os binários obsoletos e orquestrar a própria mutação precisava ser resolvida. No Windows, enfrentamos o bloqueio de arquivo (File Lock). O desafio arquitetural reside em efetuar essa troca de binários sem depender de componentes externos. Seguindo o princípio **Library-First** e **TDD**, essa responsabilidade não deve estar acoplada ao fluxo principal de `main.py`, mas encapsulada em uma biblioteca altamente testável.

## Goals / Non-Goals

**Goals:**
- **[TDD & 100% Coverage]** Desenvolver toda a funcionalidade usando Red-Green-Refactor e atingir 100% de cobertura de testes unitários.
- **[Library-First]** Criar a biblioteca autônoma `lib/auto_updater` isolada do PyQt e do `ControladorAplicativo`.
- **[Integration-First]** Escrever testes de integração das fronteiras do atualizador (File System, Requests, Keyring) antes das unidades.
- Orquestrar a Auto-Instalação, Limpeza e Update de forma unificada chamando a biblioteca no "pré-boot" do `main.py`.
- Assegurar a integridade do sistema operacional restringindo severamente a área de atuação da Limpeza de Lixo.
- Garantir a resiliência do request ao GitHub lendo o Credential Manager (Keyring) de modo assíncrono à lógica de negócio.

**Non-Goals:**
- Implementar atualizadores em segundo plano ("daemons"). Todo o fluxo ocorre de maneira determinística antes do boot da UI.
- Desenvolver scripts secundários `.bat` ou instaladores MSIX. A premissa é manter a simplicidade com o Rename Trick via código Python.
- Misturar lógica de rede ou de sistema de arquivos diretamente na interface gráfica.

## Decisions

1. **Abordagem Library-First para o Updater**
   - *Rationale*: Evitar poluir o `main.py` com código complexo não testado. O código testável garante a segurança necessária.
   - *Abordagem*: O pacote `lib/auto_updater` terá classes para cada responsabilidade: Instalação, Updater e Limpeza.

2. **Auto-Install via Cópia Segura e Atalho**
   - *Rationale*: Evitar a "Síndrome da Pasta Downloads".
   - *Abordagem*: A biblioteca injeta validação de path. Estando fora do canônico (`%LOCALAPPDATA%\EditorAresta`), copia seu binário para o destino, salva `cleanup_folder.txt`, cria um atalho (`.lnk`) e reinicia. Isso será extensivamente testado com pastas temporárias (`tempfile`).

3. **Lixeira Estrita (Hardcoded Name)**
   - *Rationale*: Eliminar vulnerabilidade de apagamento acidental.
   - *Abordagem*: A varredura atuará sob regra absoluta, adicionando sempre `EditorAresta.old.exe` ao caminho.

4. **Pré-Auth e Keyring Independente**
   - *Rationale*: Não instanciar Auth/Qt no momento rústico do Boot.
   - *Abordagem*: O uso de `keyring` isolado será mockado nos testes para assegurar 100% de cobertura nos cenários de token presente vs ausente.

5. **Testes Baseados em Mocks Rigorosos**
   - *Rationale*: Operações destrutivas ou dependentes de OS não podem rodar nos testes reais afetando o CI.
   - *Abordagem*: Funções de `os`, `shutil` e `subprocess` serão mockadas ou terão instâncias injetadas (Dependency Injection) onde aplicável para garantir o teste da lógica de negócio.

## Risks / Trade-offs

- **[Risk] Testabilidade de Componentes do OS e File Lock** → *Mitigation*: Uso intensivo de Injeção de Dependências ou `unittest.mock.patch` para simular as falhas do Windows e File Locks e garantir comportamento previsível.
- **[Risk] Processo Zombie segurando Lock** → *Mitigation*: Garantir via testes que o script chame `sys.exit()` imediatamente após o `subprocess.Popen`.
