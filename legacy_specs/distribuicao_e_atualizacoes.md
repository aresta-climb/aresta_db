# Especificação Técnica: Arquitetura de Distribuição e Ciclo de Vida de Dados

## 1. Objetivo
Definir a estratégia de distribuição experimental e o mecanismo de sincronização de dados offline para o aplicativo, garantindo que testadores utilizem versões compatíveis do software sem comprometer o acesso a dados críticos em ambientes sem conectividade (setores de escalada).

## 2. Estratégia de Distribuição
O aplicativo será distribuído exclusivamente através dos canais oficiais de teste para garantir controle de acesso e segurança do binário.
 * **Android:** Google Play Console - *Trilha de Teste Fechado*. Acesso restrito via whitelist de e-mails (Google Accounts).
 * **iOS:** App Store Connect - *TestFlight*. Distribuição via grupos externos com convites por e-mail, sem geração de link público.
 * **Validade da Build:** O limite de expiração de 90 dias do TestFlight será renovado a cada novo *upload* de binário.

## 3. Versionamento e Trava de Atualização (In-App)
A arquitetura separa o ciclo de vida do **Binário (App)** do ciclo de vida dos **Dados (Croquis/Índices)**.

### 3.1. Estrutura do Manifesto de Atualização
O aplicativo consultará um arquivo de manifesto (JSON) hospedado no servidor/CDN antes de cada tentativa de sincronização de dados.
```json
{
  "latest_data_version": "2026.04.15",
  "app_version_policy": {
    "min_required": "1.2.0",
    "recommended": "1.3.5",
    "update_url_ios": "https://beta.itunes.apple.com/...",
    "update_url_android": "https://play.google.com/apps/testing/..."
  }
}

```
### 3.2. Lógica de Validação
Ao verificar o índice, o app executa a seguinte máquina de estados:
 1. **Versão Instalada < min_required:**
   * **Estado:** *Hard Update Required*.
   * **Ação:** Exibe banner persistente de bloqueio de sincronização.
   * **Comportamento:** O usuário não pode baixar novos dados. O acesso aos dados já cacheados no LocalStorage é mantido para garantir uso emergencial em campo (Offline-First).
 2. **Versão Instalada < recommended:**
   * **Estado:** *Soft Update Available*.
   * **Ação:** Exibe banner informativo sugerindo atualização.
   * **Comportamento:** Sincronização de dados permitida.
 3. **Versão Instalada >= recommended:**
   * **Estado:** *Up-to-date*.
   * **Ação:** Nenhuma.

## 4. Persistência e LocalStorage
O armazenamento local é tratado como a "fonte da verdade" durante a execução em campo.
 * **Tecnologia:** LocalStorage (persistência de chave-valor para metadados) e banco de dados local para croquis.
 * **Estratégia de Cache:**
   * O índice de croquis é versionado.
   * Imagens e vetores de topos são baixados sob demanda e mantidos em cache permanente.
 * **Integridade:** Caso a atualização de binário envolva uma mudança de esquema (Breaking Change) no banco local, a rotina de migração deve ser disparada no primeiro boot após o update, antes de liberar a nova sincronização de dados.

## 5. Fluxo de Experiência do Usuário (UX)
 * **Em Casa (Online):** O app detecta a necessidade de atualização, avisa o usuário e permite que ele saia para o setor com a versão mais estável e os dados sincronizados.
 * **Na Rocha (Offline/Low Signal):** O app prioriza a exibição do cache local. Mensagens de atualização não devem impedir a leitura de dados já baixados, evitando que o escalador fique sem informação técnica em locais críticos.
**Aprovado por:** Renato Utsch Gonçalves
**Data:** 28 de Abril de 2026
**Status:** Implementação Experimental