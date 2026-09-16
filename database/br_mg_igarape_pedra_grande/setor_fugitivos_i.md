---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Bloco Fugitivos I
escaladas:
- boulder:
    nome: Polydance
    dificuldade: V4
- boulder:
    nome: Bigdance
    dificuldade: V5_BARRA_V6
- boulder:
    nome: Boulder do Bola
    dificuldade: V5
- boulder:
    nome: Trolls
    dificuldade: V1
- boulder:
    nome: Calcinha Larga
    dificuldade: V2_BARRA_V3
- boulder:
    nome: Tanga Frouxa
    dificuldade: V2
- boulder:
    nome: Barriga de Aluguel
    dificuldade: V5
- boulder:
    nome: Primeiro de todos
    dificuldade: V1
- boulder:
    nome: Sem nome 18
    dificuldade: V0
- boulder:
    nome: Bananinha
    dificuldade: V1
- boulder:
    nome: Cactos kid
    dificuldade: V2
- boulder:
    nome: Quem vai primeiro
    dificuldade: V1
mapas:
- caminho_imagem_mapa: imagens/setor_fugitivos_i_p0.webp
  largura_mapa: 2155
  altura_mapa: 1945
  pontos_de_interesse:
  - id: '2'
    label: '2'
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 678
          y: 1132
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '2'
        - x: 654
          y: 847
          tipo: PASSAGEM
        - x: 672
          y: 550
          tipo: PASSAGEM
        - x: 687
          y: 295
          tipo: FIM_TOP
          rotulo: B
      espessura: 3
    cor: '#FFD600'
  - id: '3'
    label: '3'
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1008
          y: 1116
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
        - x: 1116
          y: 912
          tipo: PASSAGEM
          rotulo: D
      espessura: 3
    cor: '#FFD600'
  - id: '4'
    label: '4'
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1305
          y: 961
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '4'
        - x: 1388
          y: 768
          tipo: PASSAGEM
        - x: 1380
          y: 652
          tipo: PASSAGEM
      espessura: 3
    cor: '#FFD600'
  - id: '5'
    label: '5'
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1461
          y: 842
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '5'
        - x: 1321
          y: 906
          tipo: PASSAGEM
        - x: 1247
          y: 964
          tipo: PASSAGEM
        - x: 1206
          y: 974
          tipo: PASSAGEM
          rotulo: A
      espessura: 3
    cor: '#FFD600'
  - id: X
    label: X
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1205
          y: 973
          tipo: PASSAGEM
        - x: 998
          y: 1029
          tipo: PASSAGEM
        - x: 673
          y: 1062
          tipo: PASSAGEM
        - x: 493
          y: 1099
          tipo: PASSAGEM
        - x: 476
          y: 983
          tipo: PASSAGEM
      espessura: 3
    cor: '#FFD600'
  - id: ▲
    label: ▲
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1205
          y: 974
          tipo: PASSAGEM
        - x: 1152
          y: 958
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: ▲
          raio: 14
        - x: 1121
          y: 942
          tipo: PASSAGEM
        - x: 1116
          y: 912
          tipo: PASSAGEM
          rotulo: A
      espessura: 3
    cor: '#FFD600'
  - id: D
    label: D
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1116
          y: 912
          tipo: PASSAGEM
        - x: 1196
          y: 738
          tipo: PASSAGEM
        - x: 896
          y: 279
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: C
      espessura: 3
    cor: '#FFD600'
  - id: linha_1
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 284
          y: 1097
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
        - x: 407
          y: 1136
          tipo: PASSAGEM
        - x: 452
          y: 1050
          tipo: PASSAGEM
        - x: 476
          y: 983
          tipo: PASSAGEM
      espessura: 3
    cor: '#FFD600'
  - id: linha_10
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 476
          y: 982
        - x: 497
          y: 876
          tipo: PASSAGEM
        - x: 496
          y: 768
          tipo: PASSAGEM
        - x: 470
          y: 288
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: A
      espessura: 3
    cor: '#FFD600'
  - id: linha_7
    label: d
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1205
          y: 974
          tipo: PASSAGEM
          rotulo: ''
        - x: 1380
          y: 652
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_14
    label: d
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1380
          y: 652
          tipo: PASSAGEM
          rotulo: ''
        - x: 1444
          y: 423
          tipo: FIM_TOP
          rotulo: D
      espessura: 3
    cor: '#FFD600'
  referencias:
  - ids:
    - '5'
    - ▲
    - D
    escalada: Polydance
  - ids:
    - '5'
    - linha_10
    - X
    escalada: Bigdance
  - ids:
    - '3'
    - ▲
    - linha_7
    - linha_14
    escalada: Boulder do Bola
  - ids:
    - '4'
    - linha_14
    escalada: Trolls
  - ids:
    - '3'
    - D
    escalada: Calcinha Larga
  - ids:
    - '2'
    escalada: Tanga Frouxa
  - ids:
    - linha_1
    - linha_10
    escalada: Barriga de Aluguel
- caminho_imagem_mapa: imagens/setor_fugitivos_i_p1.webp
  largura_mapa: 1280
  altura_mapa: 960
  pontos_de_interesse:
  - id: linha_3
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1006
          y: 507
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '6'
          raio: 14
        - x: 1008
          y: 337
          tipo: PASSAGEM
        - x: 1022
          y: 157
          tipo: PASSAGEM
        - x: 1009
          y: 55
          tipo: FIM_TOP
          rotulo: E
          raio: 14
      espessura: 3
    cor: '#FFD600'
  - id: linha_4
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1137
          y: 455
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '5'
          raio: 14
        - x: 1134
          y: 304
          tipo: PASSAGEM
        - x: 1094
          y: 71
          tipo: FIM_TOP
          rotulo: F
          raio: 14
      espessura: 3
    cor: '#FFD600'
  - id: linha_8
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 439
          y: 615
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
          raio: 14
        - x: 454
          y: 537
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_11
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 651
          y: 557
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '4'
          raio: 14
        - x: 673
          y: 404
          tipo: PASSAGEM
        - x: 645
          y: 288
          tipo: PASSAGEM
          rotulo: E
      espessura: 3
    cor: '#FFD600'
    label: ''
  - id: linha_13
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 646
          y: 289
          tipo: PASSAGEM
          rotulo: ''
        - x: 618
          y: 56
          tipo: FIM_TOP
          rotulo: D
          raio: 14
      espessura: 3
    cor: '#FFD600'
  - id: linha_15
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 454
          y: 537
          tipo: PASSAGEM
          rotulo: ''
        - x: 489
          y: 502
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_16
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 489
          y: 502
          tipo: PASSAGEM
          rotulo: ''
        - x: 568
          y: 515
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_17
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 568
          y: 515
          tipo: PASSAGEM
          rotulo: ''
        - x: 585
          y: 428
          tipo: PASSAGEM
          rotulo: ''
        - x: 631
          y: 371
          tipo: PASSAGEM
          rotulo: ''
        - x: 646
          y: 289
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_12
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1138
          y: 455
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '5'
          raio: 14
        - x: 1007
          y: 455
        - x: 848
          y: 470
        - x: 713
          y: 492
        - x: 660
          y: 497
        - x: 569
          y: 515
      espessura: 3
    cor: '#FFD600'
  - id: linha_19
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 454
          y: 537
          tipo: PASSAGEM
          rotulo: ''
        - x: 455
          y: 510
          tipo: PASSAGEM
        - x: 446
          y: 495
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_9
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 489
          y: 502
        - x: 446
          y: 495
      espessura: 3
    cor: '#FFD600'
  - id: linha_50
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 397
          y: 480
          tipo: PASSAGEM
          rotulo: '11'
        - x: 326
          y: 481
          tipo: PASSAGEM
        - x: 192
          y: 520
          tipo: PASSAGEM
        - x: 85
          y: 499
          tipo: PASSAGEM
        - x: 60
          y: 403
          tipo: PASSAGEM
        - x: 122
          y: 255
          tipo: FIM_TOP
          rotulo: A
          raio: 14
      espessura: 3
    cor: '#FFD600'
  - id: linha_18
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 446
          y: 495
          tipo: PASSAGEM
          rotulo: ''
        - x: 424
          y: 485
          tipo: PASSAGEM
          rotulo: ''
        - x: 397
          y: 480
          tipo: PASSAGEM
          rotulo: ''
      espessura: 3
    cor: '#FFD600'
  - id: linha_21
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 397
          y: 480
          tipo: PASSAGEM
          rotulo: ''
        - x: 341
          y: 381
          tipo: PASSAGEM
          rotulo: ''
        - x: 284
          y: 279
          tipo: PASSAGEM
          rotulo: ''
        - x: 241
          y: 179
          tipo: FIM_TOP
          rotulo: C
          raio: 14
      espessura: 3
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_3
    escalada: Primeiro de todos
  - ids:
    - linha_4
    escalada: Sem nome 18
  - ids:
    - linha_8
    - linha_19
    - linha_18
    - linha_21
    escalada: Calcinha Larga
  - ids:
    - linha_8
    - linha_15
    - linha_16
    - linha_17
    - linha_13
    escalada: Boulder do Bola
  - ids:
    - linha_11
    - linha_13
    escalada: Trolls
  - ids:
    - linha_12
    - linha_16
    - linha_9
    - linha_18
    - linha_21
    escalada: Polydance
  - ids:
    - linha_12
    - linha_16
    - linha_9
    - linha_50
    - linha_18
    escalada: Bigdance
- caminho_imagem_mapa: imagens/setor_fugitivos_i_p2.webp
  largura_mapa: 1280
  altura_mapa: 960
  pontos_de_interesse:
  - id: linha_2
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 632
          y: 626
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
          raio: 14
        - x: 724
          y: 638
          tipo: PASSAGEM
        - x: 808
          y: 585
          tipo: PASSAGEM
        - x: 823
          y: 469
          tipo: PASSAGEM
        - x: 825
          y: 296
          tipo: PASSAGEM
        - x: 799
          y: 138
          tipo: PASSAGEM
        - x: 791
          y: 32
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: A
          raio: 14
      espessura: 3
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_2
    escalada: Barriga de Aluguel
- caminho_imagem_mapa: imagens/setor_fugitivos_i_p3.webp
  largura_mapa: 960
  altura_mapa: 1280
  pontos_de_interesse:
  - id: linha_5
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 615
          y: 776
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '7'
        - x: 565
          y: 620
          tipo: PASSAGEM
        - x: 549
          y: 422
          tipo: PASSAGEM
        - x: 537
          y: 202
          tipo: PASSAGEM
          rotulo: A
      espessura: 3
    cor: '#FFD600'
  - id: linha_6
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 227
          y: 856
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '8'
        - x: 271
          y: 650
          tipo: PASSAGEM
        - x: 312
          y: 461
          tipo: PASSAGEM
        - x: 328
          y: 155
          tipo: PASSAGEM
          rotulo: B
      espessura: 3
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_5
    escalada: Bananinha
  - ids:
    - linha_6
    escalada: Cactos kid
- caminho_imagem_mapa: imagens/setor_bloco_fugitivos_i_p4.webp
  largura_mapa: 1824
  altura_mapa: 1376
  pontos_de_interesse:
  - id: linha_20
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 821
          y: 995
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '9'
          raio: 21
        - x: 779
          y: 650
          tipo: PASSAGEM
        - x: 741
          y: 279
          tipo: PASSAGEM
        - x: 798
          y: 20
          tipo: PASSAGEM
          rotulo: ''
      espessura: 4
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_20
    escalada: Quem vai primeiro
---
Veja a trilha para chegar ao setor no Wikiloc: https://loc.wiki/t/169742661?wa=sc