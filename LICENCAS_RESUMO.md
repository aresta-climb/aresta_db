# Entenda as Licenças do Aresta (Em Linguagem Simples)

Acreditamos que todo mundo deve conseguir entender o que pode e não pode fazer com o código e os dados do Aresta, sem precisar ser um advogado. 

Este é um **resumo prático e amigável (TL;DR)** do ecossistema de licenciamento do projeto. 

> [!WARNING] 
> Este documento tem caráter educativo. Em caso de disputas legais, os textos oficiais em inglês da MPL 2.0 e ODbL prevalecem.

---

## 1. O Motor e Ferramentas (`aresta_db`)
**Licença Oficial:** [Mozilla Public License 2.0 (MPL 2.0)](./LICENSE)

O `aresta_db` e o editor utilizam a licença MPL 2.0, caracterizada por um *Copyleft a nível de arquivo* (*file-level weak copyleft*). Ela garante que as ferramentas e o código do Aresta permaneçam sempre abertos, facilitando a reutilização e integração em outros projetos e bibliotecas.

**✅ O que você PODE fazer:**
* Baixar, instalar e rodar o `aresta_db` e o editor de graça para qualquer propósito (pessoal ou comercial).
* Modificar qualquer arquivo existente do `aresta_db` ou adicionar novos arquivos ao seu projeto.
* Combinar o `aresta_db` com outros softwares e bibliotecas (mesmo que sejam proprietários ou usem outras licenças de código aberto).

**📝 O que você PRECISA fazer:**
* Se você modificar arquivos de código pertencentes ao `aresta_db` e distribuir essa versão, você **é obrigado** a disponibilizar as alterações feitas nesses arquivos sob a mesma licença MPL 2.0.
* Arquivos novos ou separados que você criar no seu projeto não são afetados e podem ter a licença que você escolher.

---

## 2. A Interface da API (`aresta_api`)
**Licença Oficial:** [Mozilla Public License 2.0 (MPL 2.0)](./aresta_api/LICENSE)

A API define os esquemas de dados (Protobuf) e clientes de comunicação do ecossistema Aresta. Ela utiliza a MPL 2.0 para garantir total compatibilidade e liberdade de integração em outros aplicativos.

**✅ O que você PODE fazer:**
* Pegar o código cliente/servidor da API e integrar no seu próprio aplicativo de escalada (seja ele gratuito, open source, ou um app pago/fechado nas lojas de aplicativos).
* Usar as definições e stubs gRPC/Protobuf livremente em outros projetos.

**📝 O que você PRECISA fazer:**
* Se você fizer alterações nos arquivos da própria `aresta_api` e distribuí-las, deve disponibilizar essas alterações sob a MPL 2.0.
* O restante do seu aplicativo permanece sob a licença que você desejar.

---

## 3. A Base de Dados Comunitária
A base de dados estruturada do projeto (arquivos YAML puros e cabeçalhos YAML na pasta `database/`) opera sob uma licença livre para dados (ODbL), enquanto os textos em Markdown operam sob Copyright.

### 3.1. Metadados e Fatos (Arquivos e Cabeçalhos YAML)
**Licença Oficial:** [Open Database License (ODbL 1.0)](./LICENSE.DATA)

Isto cobre estritamente a extração de dados estruturados e fatos (nomes das vias, graus, coordenadas GPS, quantidades) contidos nos arquivos `.yaml` dedicados e nos cabeçalhos (frontmatter) YAML que ficam no topo dos arquivos `.md`. Ao utilizar esses dados estruturados, você deve seguir a licença ODbL.
* **Resumo:** Você pode extrair, copiar e usar essas informações livremente em qualquer aplicativo. Se você usar nossos dados para construir uma base derivada/melhorada, você é obrigado a compartilhar a sua nova base aberta para a comunidade sob a mesma licença (ODbL).

### 3.2. Textos em Markdown, PDFs e Imagens
**Licença:** Copyright Privado dos Autores Originais (Todos os Direitos Reservados)

Para proteger a autoria de contribuições literárias, descrições detalhadas e preservação histórica, **todo o corpo de texto (fora do cabeçalho YAML)** nos arquivos Markdown (`.md`), bem como PDFs antigos, guias digitalizados e imagens, pertencem aos seus autores originais e **não são** licenciados de forma livre. O Aresta hospeda e cataloga esses conteúdos operando estritamente sob o princípio do **Uso Justo (Fair Use)** para fins de arquivo histórico e educação (veja a política de remoção na seção 4).

---

## 4. Política de Direitos Autorais e Remoção (Notice and Takedown)

O ArestaDB cataloga dados, croquis e informações históricas para a preservação da memória da escalada e acesso da comunidade. Todo o nosso esforço é direcionado para creditar corretamente os autores originais. 

Os metadados estruturados do projeto (arquivos `.yaml` e frontmatter YAML nos arquivos `.md`) operam sob a licença livre **ODbL 1.0**. No entanto, reconhecemos que todo o corpo de texto nos arquivos Markdown, além de materiais históricos em PDF e imagens, pertencem estritamente aos seus autores e não possuem licenciamento livre. Nós os catalogamos sob o princípio do **Uso Justo (Fair Use)** para fins educacionais e de arquivo histórico, sem fins lucrativos.

Se você é o autor ou detentor dos direitos autorais de qualquer material, imagem, artigo ou PDF hospedado neste repositório e **não concorda com a sua exibição gratuita**, por favor tome uma das ações abaixo:
 * Envie um email para contato@arestaclimb.com pedindo a remoção do conteúdo
 * Abra uma *Issue* neste repositório pedindo a remoção do conteúdo
 * Envie uma *Pull Request* diretamente removendo conteúdo

Com a comprovação de sua autoria, **O conteúdo será removido imediatamente e sem questionamentos.**