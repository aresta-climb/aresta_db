# Especificação Técnica: Módulo de Mapas e Navegação

## 1. Visão Geral
Este documento descreve a arquitetura do sistema de mapas do aplicativo. A estratégia divide-se em três pilares: descoberta online via Google Maps, navegação offline delegada a terceiros e expansão futura com mapeamento proprietário via drone.

## 2. Arquitetura de Camadas

### 2.1 Camada de Descoberta (Online)
* **Tecnologia:** `Maps_flutter` (SDK Oficial).
* **Objetivo:** Permitir que o usuário localize setores de escalada geograficamente e selecione quais croquis deseja baixar para uso offline.
* **Regras de Negócio:**
    * Disponível apenas em modo online (com verificação de conectividade via `connectivity_plus`).
    * Uso de `MapType.satellite` para visualização de terreno.
    * Exibição de marcadores (Clusters) representando setores de escalada.
* **Custo:** Gratuito e ilimitado para dispositivos móveis através do Google Maps Platform.

### 2.2 Camada de Navegação e Aproximação (Offline)
Para evitar custos de armazenamento e licenciamento de tiles de satélite, a navegação de trilhas será delegada a aplicativos especializados.
* **Formato de Dados:** Arquivos `.gpx` (GPS Exchange Format) armazenados localmente, ou links para trilhas específicas no Wikiloc.
* **Integração:** Implementação de *Deep Links* e protocolos de compartilhamento de arquivos.
* **Fluxo de Trabalho:**
    1.  O usuário baixa o pacote do setor (Protobuf + imagens + GPX).
    2.  Em cada grupo / setor, o aplicativo oferece um botão "Trilha para esse grupo/setor".
    3.  O Antigravity dispara um `intent` (Android) ou `URL Scheme` (iOS) para abrir o arquivo GPX em aplicativos como Wikiloc, Gaia GPS ou Strava.
* **Vantagem:** Elimina a necessidade de gerenciar complexos sistemas de cache de tiles e reduz drasticamente o tamanho dos downloads.

### 2.3 Camada de Detalhe Técnico (Drone - Expansão)
A visualização de altíssima resolução das faces das rochas será feita com dados proprietários.
* **Fonte de Dados:** Ortofotos geradas via fotogrametria aérea (DJI Mini Pro).
* **Formato:** `MBTiles` (SQLite container para blocos de imagem raster).
* **Hospedagem:** GitHub Pages (Arquivos estáticos < 100MB por setor).
* **Renderização:** Uso do pacote `flutter_map` configurado para ler fontes locais.
* **Lógica de Sobreposição:**
    ```dart
    TileLayer(
      urlTemplate: 'path_to_local_storage/{z}/{x}/{y}.png',
      maxNativeZoom: 18, // Ou superior conforme resolução do drone
      maxZoom: 22,       // Oversampling para visualização de agarras
    )
    ```

## 3. Segurança e Termos de Uso
1.  **Google Maps:** O uso segue os termos de serviço da Google Cloud Platform para SDKs nativos móveis, garantindo gratuidade na visualização dinâmica.
2.  **Propriedade Intelectual:** O aplicativo não redistribui tiles do Google, Bing ou Mapbox. Toda a distribuição offline é composta por dados abertos (GPX) ou de autoria própria (fotos de drone).
3.  **Lojas de Aplicativos:** A conformidade com a Apple App Store e Google Play Store é mantida ao evitar o "scraping" de imagens protegidas por direitos autorais para uso offline não autorizado.

## 5. Roadmap de Implementação
* **V1.0:** Integração Google Maps Online + Download de metadados + Botão "Abrir Trilhas no Wikiloc".
* **V1.5:** Implementação de suporte a MBTiles locais no `flutter_map` para setores piloto.
* **V2.0:** Pipeline de mapeamento aéreo sistemático e substituição gradativa das descrições de acesso por camadas de ortofotos proprietárias.

---

### Notas de Manutenção (ARESTA)
Este modelo de custo zero permite que a associação mantenha o aplicativo ativo sem dependência de doações constantes para pagamento de APIs de mapas, focando recursos na manutenção física dos setores (regrampagem e sinalização).