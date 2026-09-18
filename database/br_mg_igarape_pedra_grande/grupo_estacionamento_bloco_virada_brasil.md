---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Estacionamento - Bloco Virada Brasil
escaladas:
- boulder:
    nome: Virada Brasil
    dificuldade: V0
- boulder:
    nome: Tio peruca
    dificuldade: V1
- boulder:
    nome: Sem nome 24
    dificuldade: V0
mapas:
- caminho_imagem_mapa: imagens/grupo_estacionamento_bloco_virada_brasil_p0.webp
  largura_mapa: 1280
  altura_mapa: 960
  pontos_de_interesse:
  - id: linha_1
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1681
          y: 1349
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
          raio: 19
        - x: 1605
          y: 1144
          tipo: PASSAGEM
        - x: 1538
          y: 912
          tipo: PASSAGEM
        - x: 1346
          y: 730
          tipo: PASSAGEM
        - x: 1301
          y: 686
          tipo: PASSAGEM
        - x: 1267
          y: 619
          tipo: PASSAGEM
        - x: 1252
          y: 584
          tipo: PASSAGEM
        - x: 1235
          y: 548
          tipo: PASSAGEM
        - x: 1211
          y: 496
          tipo: FIM_TOP
          rotulo: B
          raio: 19
      espessura: 4
    cor: '#FFD600'
  - id: linha_3
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1466
          y: 1370
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '2'
          raio: 19
        - x: 1426
          y: 1180
          tipo: PASSAGEM
          rotulo: ''
        - x: 1408
          y: 1074
          tipo: PASSAGEM
          rotulo: ''
        - x: 1385
          y: 1010
          tipo: PASSAGEM
          rotulo: ''
        - x: 1346
          y: 961
          tipo: PASSAGEM
          rotulo: ''
        - x: 1298
          y: 946
          tipo: PASSAGEM
          rotulo: ''
        - x: 1234
          y: 949
          tipo: PASSAGEM
          rotulo: ''
        - x: 1184
          y: 954
          tipo: PASSAGEM
          rotulo: ''
        - x: 1104
          y: 913
          tipo: PASSAGEM
          rotulo: ''
        - x: 1021
          y: 799
          tipo: PASSAGEM
          rotulo: ''
        - x: 997
          y: 716
          tipo: PASSAGEM
          rotulo: ''
      espessura: 4
    cor: '#FFD600'
  - id: linha_4
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 997
          y: 716
          tipo: PASSAGEM
          rotulo: ''
        - x: 1004
          y: 643
          tipo: PASSAGEM
          rotulo: ''
        - x: 1011
          y: 579
          tipo: PASSAGEM
          rotulo: ''
        - x: 1010
          y: 501
          tipo: FIM_TOP
          rotulo: A
          raio: 19
      espessura: 4
    cor: '#FFD600'
  - id: linha_2
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 864
          y: 1225
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
          raio: 19
        - x: 887
          y: 1146
          tipo: PASSAGEM
        - x: 902
          y: 1092
          tipo: PASSAGEM
        - x: 920
          y: 1018
          tipo: PASSAGEM
        - x: 938
          y: 953
          tipo: PASSAGEM
        - x: 960
          y: 885
          tipo: PASSAGEM
        - x: 971
          y: 832
          tipo: PASSAGEM
        - x: 997
          y: 716
          tipo: PASSAGEM
          rotulo: C
      espessura: 4
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_1
    escalada: Virada Brasil
  - ids:
    - linha_3
    - linha_4
    escalada: Tio peruca
  - ids:
    - linha_2
    - linha_4
    escalada: Sem nome 24
---
