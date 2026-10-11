# Guia de Distribuição Linux: Repositório Flatpak OSTree no Cloudflare R2

O Editor Aresta para distribuições Linux é distribuído oficialmente através de um repositório Flatpak soberano baseado em **OSTree** (modo `archive-z2`), hospedado no Cloudflare R2 sob o domínio `https://serving.arestaclimb.com/flatpak/`.

Essa arquitetura garante:
- **Sandbox completo** via Flatpak para segurança do usuário.
- **Assinatura criptográfica GPG** em todos os commits e índices do repositório.
- **Static Deltas** para downloads ultrarrápidos e atualizações binárias incrementais de poucos kilobytes/megabytes.
- **Atualização contínua obrigatória**: os usuários recebem correções instantâneas via `flatpak update` e por verificação ativa no arranque (`TelaDeAbertura`).
- **Resolução automática de runtimes**: o arquivo `.flatpakref` delega a resolução dos runtimes do KDE ao Flathub público sem exigir que o Aresta seja mantido no catálogo deles.

---

## 1. Como os Usuários Instalam o Editor Aresta no Linux

### Opção A: Instalação Gráfica em 1 Clique (Recomendada)

1. No site oficial ([arestaclimb.com](https://arestaclimb.com)), o usuário clica no botão de download para Linux, baixando o arquivo:
   ```text
   https://serving.arestaclimb.com/flatpak/com.arestaclimb.Editor.flatpakref
   ```
2. Ao abrir o arquivo (dois cliques no gerenciador de arquivos), o instalador gráfico do sistema operacional (**GNOME Software**, **KDE Discover**, etc.) abrirá a tela nativa de instalação.
3. O repositório `aresta` é registrado automaticamente no sistema do usuário para atualizações automáticas futuras.

### Opção B: Instalação via Terminal (CLI)

O usuário pode adicionar o repositório oficial e instalar o aplicativo via terminal:

```bash
# 1. Adicionar o repositório Aresta Climb (assinado e verificado)
flatpak remote-add --if-not-exists aresta https://serving.arestaclimb.com/flatpak/aresta.flatpakrepo

# 2. Instalar o Editor Aresta
flatpak install aresta com.arestaclimb.Editor

# 3. Executar o Editor
flatpak run com.arestaclimb.Editor
```

---

## 2. Como Funcionam as Atualizações Automáticas

1. **Atualização Passiva (Sistema Operacional)**:
   - As lojas de aplicativos (GNOME Software / KDE Discover) e daemons do sistema operacional consultam o repositório periodicamente.
   - O comando padrão `flatpak update` atualizará o Editor Aresta aplicando os deltas estáticos com consumo mínimo de banda.
2. **Atualização Ativa (Dentro do Aplicativo)**:
   - Ao iniciar o aplicativo, a `TelaDeAbertura` consulta `https://serving.arestaclimb.com/flatpak/version.json`.
   - Se uma nova versão for publicada, o banner *"Atualização Disponível"* ou *"Atualização Obrigatória"* é exibido imediatamente para evitar discrepâncias ou erros de schema com versões antigas.

---

## 3. Configuração da Chave GPG para o CI/CD (GitHub Actions)

O repositório OSTree é assinado com uma chave GPG dedicada.

### 3.1 Gerando a Chave GPG

Em sua máquina de desenvolvimento local:

```bash
# 1. Gerar um par de chaves GPG sem senha (batch/desassistida para CI)
cat <<EOF > /tmp/gpg_batch.txt
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Aresta Climb Flatpak
Name-Email: contato@arestaclimb.com
Expire-Date: 0
%no-protection
%commit
EOF

gpg --batch --generate-key /tmp/gpg_batch.txt
rm /tmp/gpg_batch.txt

# 2. Localizar o ID da chave criada
GPG_KEY_ID=$(gpg --list-secret-keys --with-colons "contato@arestaclimb.com" | grep '^sec' | cut -d: -f5)

# 3. Exportar a chave privada em formato ASCII armor
gpg --armor --export-secret-keys "$GPG_KEY_ID"
```

### 3.2 Cadastrando nos Segredos do Repositório

1. Copie todo o conteúdo gerado (incluindo `-----BEGIN PGP PRIVATE KEY BLOCK-----` e `-----END PGP PRIVATE KEY BLOCK-----`).
2. Acesse o GitHub: `aresta_db` > **Settings** > **Secrets and variables** > **Actions**.
3. Crie o segredo:
   - **Nome**: `ARESTA_FLATPAK_GPG_PRIVATE_KEY`
   - **Valor**: Chave privada completa exportada acima.

Durante o workflow `release-editor.yml` / `build_editor_linux.yml`, o runner Ubuntu importará essa chave privada automaticamente, assinará o repositório e embutirá a chave pública correspondente no `.flatpakref` e `.flatpakrepo`.

---

## 4. Estrutura dos Arquivos no Cloudflare R2 (`aresta-serving`)

```text
aresta-serving/
└── flatpak/
    ├── version.json                     # Metadados leves de versão remota
    ├── com.arestaclimb.Editor.flatpakref # Instalador de 1 clique
    ├── aresta.flatpakrepo               # Configuração do remote Flatpak
    └── repo/                            # Repositório OSTree (archive-z2)
        ├── config
        ├── summary                      # Índice com hash e assinatura GPG
        ├── summary.sig                  # Assinatura GPG destacada
        ├── refs/
        ├── deltas/                      # Static deltas binários entre versões
        └── objects/                     # Blocos imutáveis (Content-Addressable Storage)
```

Todos os arquivos sob `flatpak/repo/objects/` e `flatpak/repo/deltas/` possuem cache estático de longo prazo (1 ano). Apenas os arquivos de índice (`summary`, `summary.sig`, `version.json`, `.flatpakref`, `aresta.flatpakrepo`) sofrem purgação imediata de cache na CDN Cloudflare ao final de cada release.
