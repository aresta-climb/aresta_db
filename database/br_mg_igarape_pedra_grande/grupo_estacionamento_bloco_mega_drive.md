---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Estacionamento - Bloco Mega drive
escaladas:
- boulder:
    nome: Atari
    dificuldade: V5
- boulder:
    nome: Projeto Igarapé
    dificuldade: INDEFINIDO
- boulder:
    nome: Sem Nome 25
    dificuldade: V2
- boulder:
    nome: Master System
    dificuldade: V10_BARRA_V11
    conquistadores:
    - Drosa
- boulder:
    nome: Mega drive
    dificuldade: V7
mapas:
- caminho_imagem_mapa: imagens/setor_estacionamento_bloco_mega_drive_p0.webp
  largura_mapa: 1773
  altura_mapa: 2364
  pontos_de_interesse:
  - id: linha_2
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 948
          y: 1676
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '2'
        - x: 954
          y: 1637
          tipo: PASSAGEM
          rotulo: ''
      espessura: 5
    cor: '#00E5FF'
  - id: linha_5
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 331
          y: 1226
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
        - x: 302
          y: 1141
          tipo: PASSAGEM
        - x: 236
          y: 978
          tipo: PASSAGEM
        - x: 230
          y: 908
          tipo: PASSAGEM
        - x: 257
          y: 791
          tipo: PASSAGEM
          rotulo: C
      espessura: 5
    cor: '#00E5FF'
    label: ''
  - id: linha_7
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 954
          y: 1637
          tipo: PASSAGEM
          rotulo: '2'
        - x: 937
          y: 1594
          tipo: PASSAGEM
          rotulo: ''
        - x: 866
          y: 1562
          tipo: PASSAGEM
          rotulo: ''
        - x: 778
          y: 1550
          tipo: PASSAGEM
          rotulo: ''
        - x: 683
          y: 1472
          tipo: PASSAGEM
          rotulo: ''
        - x: 631
          y: 1395
          tipo: PASSAGEM
          rotulo: ''
        - x: 567
          y: 1214
          tipo: PASSAGEM
          rotulo: ''
        - x: 461
          y: 1145
          tipo: PASSAGEM
          rotulo: ''
        - x: 364
          y: 1001
          tipo: PASSAGEM
          rotulo: ''
        - x: 317
          y: 926
          tipo: PASSAGEM
          rotulo: ''
        - x: 274
          y: 858
          tipo: PASSAGEM
        - x: 257
          y: 791
          tipo: PASSAGEM
          rotulo: ''
      espessura: 5
    cor: '#00E5FF'
  - id: linha_8
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 257
          y: 791
          tipo: PASSAGEM
          rotulo: ''
        - x: 270
          y: 639
          tipo: PASSAGEM
          rotulo: ''
        - x: 281
          y: 492
          tipo: FIM_TOP
          rotulo: A
      espessura: 5
    cor: '#00E5FF'
  - id: master2
    label: ''
    circulo:
      x: 380
      y: 1183
      raio: 26
    cor: ''
  - id: linha_1
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1223
          y: 1289
          tipo: PASSAGEM
          rotulo: '4'
        - x: 1237
          y: 1243
          tipo: PASSAGEM
        - x: 1151
          y: 1117
          tipo: PASSAGEM
        - x: 1130
          y: 999
          tipo: PASSAGEM
        - x: 1131
          y: 871
          tipo: PASSAGEM
        - x: 1152
          y: 735
          tipo: PASSAGEM
        - x: 1183
          y: 632
          tipo: PASSAGEM
        - x: 1210
          y: 552
          tipo: PASSAGEM
        - x: 1221
          y: 483
          tipo: PASSAGEM
        - x: 1183
          y: 393
          tipo: PASSAGEM
        - x: 1119
          y: 338
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: B
      espessura: 5
    cor: '#00E5FF'
  - id: linha_9
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 954
          y: 1637
          tipo: PASSAGEM
          rotulo: ''
        - x: 982
          y: 1488
          tipo: PASSAGEM
          rotulo: ''
        - x: 1047
          y: 1404
          tipo: PASSAGEM
          rotulo: ''
        - x: 1155
          y: 1330
          tipo: PASSAGEM
          rotulo: ''
        - x: 1223
          y: 1292
          tipo: PASSAGEM
          rotulo: ''
      espessura: 5
    cor: '#00E5FF'
  - id: linha_10
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1223
          y: 1289
          tipo: PASSAGEM
          rotulo: ''
        - x: 1359
          y: 1242
          tipo: PASSAGEM
          rotulo: ''
        - x: 1479
          y: 1205
          tipo: PASSAGEM
          rotulo: ''
        - x: 1567
          y: 1156
          tipo: PASSAGEM
          rotulo: ''
        - x: 1601
          y: 1065
          tipo: PASSAGEM
          rotulo: ''
        - x: 1634
          y: 961
          tipo: PASSAGEM
          rotulo: ''
        - x: 1635
          y: 862
          tipo: PASSAGEM
          rotulo: ''
        - x: 1632
          y: 800
          tipo: FIM_TOP
          rotulo: C
      espessura: 5
    cor: '#00E5FF'
  - id: master1
    label: ''
    circulo:
      x: 284
      y: 1248
      raio: 27
    cor: ''
  referencias:
  - ids:
    - linha_2
    - linha_9
    - linha_10
    escalada: Atari
  - ids:
    - linha_2
    - linha_7
    - linha_8
    escalada: Projeto Igarapé
  - ids:
    - linha_5
    - linha_8
    - master2
    - master1
    escalada: Master System
  - ids:
    - linha_2
    - linha_9
    - linha_1
    escalada: Mega drive
- caminho_imagem_mapa: imagens/setor_estacionamento_bloco_mega_drive_p1.webp
  largura_mapa: 1773
  altura_mapa: 2364
  pontos_de_interesse:
  - id: linha_4
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 412
          y: 1718
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
          raio: 24
        - x: 341
          y: 1617
          tipo: PASSAGEM
        - x: 297
          y: 1519
          tipo: PASSAGEM
        - x: 286
          y: 1397
          tipo: PASSAGEM
        - x: 345
          y: 1287
          tipo: PASSAGEM
        - x: 404
          y: 1141
          tipo: PASSAGEM
        - x: 445
          y: 1029
          tipo: PASSAGEM
        - x: 507
          y: 924
          tipo: PASSAGEM
        - x: 576
          y: 781
          tipo: PASSAGEM
        - x: 625
          y: 691
          tipo: PASSAGEM
        - x: 656
          y: 650
          tipo: PASSAGEM
          rotulo: A
      espessura: 5
    cor: '#00E5FF'
  - id: linha_6
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 769
          y: 1204
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
        - x: 716
          y: 926
          tipo: PASSAGEM
        - x: 680
          y: 853
          tipo: PASSAGEM
        - x: 700
          y: 700
          tipo: PASSAGEM
        - x: 795
          y: 578
          tipo: PASSAGEM
        - x: 775
          y: 516
          tipo: PASSAGEM
          rotulo: B
      espessura: 5
    cor: '#00E5FF'
  - id: master1
    label: ''
    circulo:
      x: 696
      y: 1206
      raio: 28
    cor: ''
  - id: master2
    label: ''
    circulo:
      x: 836
      y: 1142
      raio: 27
    cor: ''
  referencias:
  - ids:
    - linha_4
    escalada: Sem Nome 25
  - ids:
    - linha_6
    - master2
    - master1
    escalada: Master System
---
