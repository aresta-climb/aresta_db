---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Estacionamento - Bloco Solaris
escaladas:
- boulder:
    nome: Solaris
    dificuldade: V4
- boulder:
    nome: Pump
    dificuldade: V3
- boulder:
    nome: Lítio
    dificuldade: V2
- boulder:
    nome: Tório
    dificuldade: V0
- boulder:
    nome: Irídio
    dificuldade: V0
mapas:
- caminho_imagem_mapa: imagens/grupo_estacionamento_bloco_solaris_p0.webp
  largura_mapa: 1773
  altura_mapa: 2364
  pontos_de_interesse:
  - id: linha_2
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1530
          y: 1748
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
        - x: 1437
          y: 1623
          tipo: PASSAGEM
          rotulo: ''
        - x: 1364
          y: 1564
          tipo: PASSAGEM
          rotulo: ''
        - x: 1237
          y: 1501
          tipo: PASSAGEM
          rotulo: ''
        - x: 1115
          y: 1437
          tipo: PASSAGEM
          rotulo: ''
        - x: 1026
          y: 1389
          tipo: PASSAGEM
          rotulo: ''
        - x: 998
          y: 1233
          tipo: PASSAGEM
          rotulo: ''
      espessura: 4
    cor: '#00E5FF'
  - id: linha_3
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 998
          y: 1233
          tipo: PASSAGEM
          rotulo: ''
        - x: 997
          y: 1075
          tipo: PASSAGEM
          rotulo: ''
        - x: 997
          y: 1031
          tipo: PASSAGEM
          rotulo: ''
        - x: 987
          y: 901
          tipo: PASSAGEM
          rotulo: ''
        - x: 974
          y: 792
          tipo: FIM_TOP
          rotulo: A
      espessura: 4
    cor: '#00E5FF'
  - id: linha_5
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 780
          y: 1794
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '2'
        - x: 787
          y: 1741
          tipo: PASSAGEM
          rotulo: ''
      espessura: 4
    cor: '#FFD600'
  - id: linha_6
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 787
          y: 1741
          tipo: PASSAGEM
          rotulo: ''
        - x: 808
          y: 1717
          tipo: PASSAGEM
        - x: 970
          y: 1668
          tipo: PASSAGEM
          rotulo: ''
        - x: 988
          y: 1530
          tipo: PASSAGEM
          rotulo: ''
        - x: 988
          y: 1337
          tipo: PASSAGEM
          rotulo: ''
        - x: 998
          y: 1233
          tipo: PASSAGEM
          rotulo: B
      espessura: 4
    cor: '#00E5FF'
  - id: linha_7
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 784
          y: 1738
          tipo: PASSAGEM
          rotulo: '3'
        - x: 760
          y: 1697
          tipo: PASSAGEM
        - x: 583
          y: 1485
          tipo: PASSAGEM
          rotulo: ''
        - x: 488
          y: 1340
          tipo: PASSAGEM
          rotulo: ''
        - x: 417
          y: 1237
          tipo: PASSAGEM
          rotulo: ''
        - x: 385
          y: 1069
          tipo: FIM_TOP
          rotulo: B
      espessura: 4
    cor: '#00E5FF'
  referencias:
  - ids:
    - linha_2
    - linha_3
    escalada: Solaris
  - ids:
    - linha_5
    - linha_6
    - linha_3
    escalada: Pump
  - ids:
    - linha_5
    - linha_7
    escalada: Lítio
- caminho_imagem_mapa: imagens/grupo_estacionamento_bloco_solaris_p1.webp
  largura_mapa: 2364
  altura_mapa: 1773
  pontos_de_interesse:
  - id: linha_1
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1366
          y: 1285
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
        - x: 1230
          y: 1120
          tipo: PASSAGEM
        - x: 1132
          y: 1043
          tipo: PASSAGEM
        - x: 1041
          y: 865
          tipo: PASSAGEM
        - x: 1012
          y: 712
          tipo: PASSAGEM
        - x: 963
          y: 506
          tipo: PASSAGEM
        - x: 943
          y: 401
          tipo: PASSAGEM
          rotulo: A
      espessura: 4
    cor: '#00E5FF'
  - id: linha_4
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1771
          y: 1100
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '4'
        - x: 1731
          y: 936
          tipo: PASSAGEM
        - x: 1637
          y: 762
          tipo: PASSAGEM
        - x: 1557
          y: 676
          tipo: PASSAGEM
        - x: 1418
          y: 518
          tipo: PASSAGEM
        - x: 1310
          y: 409
          tipo: PASSAGEM
        - x: 1246
          y: 328
          tipo: PASSAGEM
          rotulo: B
      espessura: 4
    cor: '#00E5FF'
  referencias:
  - ids:
    - linha_1
    escalada: Tório
  - ids:
    - linha_4
    escalada: Irídio
---
