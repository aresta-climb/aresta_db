---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Setor Tramontina
escaladas:
- boulder:
    nome: Sobe e desce
    dificuldade: VB
    descricao: 'Boulder usado para descer do topo do bloco. Desça de frente para a
      rocha, desescalando.


      ![Agarra de saída do Sobe e desce](imagens/setor_tramontina_sobe_e_desce_p0.webp)'
    conquistadores:
    - Renato Utsch
    - Bunitin
    - Ana
    - Camila
    - Lucas
    - Evandro
- boulder:
    nome: Questionamentos
    dificuldade: V0
    conquistadores:
    - Renato Utsch
    - Ana
    - Lucas
    - Evandro
- boulder:
    nome: Não vai descalço
    dificuldade: V0
    conquistadores:
    - Bunitin
    - Lucas
    - Ana
    - Renato Utsch
    - Evandro
- boulder:
    nome: Linhas paralelas
    dificuldade: V1
    descricao: 'Boulder sai bem aberto, com as duas mãos em barbatanas opostas. A
      ideia é subir mantendo a oposição em agarras opostas entre as duas linhas até
      a virada!


      ![Agarras de saída](imagens/whatsapp_image_2026_09_20_at_230736.webp)'
    conquistadores:
    - Renato Utsch
    - Evandro
    - Ana
- boulder:
    nome: Só vejo almas
    dificuldade: V1
    descricao: Virada um pouco mais delicada do que os boulders ao lado desse boulder.
    conquistadores:
    - Bunitin
    - Renato Utsch
mapas:
- caminho_imagem_mapa: imagens/setor_tramontina_p0.webp
  largura_mapa: 1825
  altura_mapa: 1369
  pontos_de_interesse:
  - id: linha_1
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 100
          y: 925
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
          raio: 21
        - x: 128
          y: 776
          tipo: PASSAGEM
        - x: 143
          y: 674
          tipo: PASSAGEM
        - x: 157
          y: 582
          tipo: PASSAGEM
        - x: 173
          y: 546
          tipo: PASSAGEM
          rotulo: A
      espessura: 4
    cor: '#00E5FF'
  - id: linha_2
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 447
          y: 805
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '2'
          raio: 21
        - x: 428
          y: 656
          tipo: PASSAGEM
        - x: 430
          y: 506
          tipo: PASSAGEM
        - x: 442
          y: 376
          tipo: PASSAGEM
        - x: 451
          y: 293
          tipo: PASSAGEM
          rotulo: B
      espessura: 4
    cor: '#00E5FF'
  - id: linha_3
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 991
          y: 720
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '3'
          raio: 21
        - x: 963
          y: 564
          tipo: PASSAGEM
        - x: 900
          y: 361
          tipo: PASSAGEM
        - x: 852
          y: 250
          tipo: PASSAGEM
        - x: 832
          y: 191
          tipo: PASSAGEM
          rotulo: C
      espessura: 4
    cor: '#00E5FF'
  - id: linha_4
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1420
          y: 579
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '4'
          raio: 21
        - x: 1375
          y: 419
          tipo: PASSAGEM
        - x: 1314
          y: 282
          tipo: PASSAGEM
        - x: 1289
          y: 238
          tipo: PASSAGEM
          rotulo: D
      espessura: 4
    cor: '#00E5FF'
  - id: linha_5
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1629
          y: 634
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '5'
          raio: 21
        - x: 1592
          y: 500
          tipo: PASSAGEM
        - x: 1553
          y: 421
          tipo: PASSAGEM
        - x: 1524
          y: 355
          tipo: PASSAGEM
        - x: 1480
          y: 274
          tipo: PASSAGEM
          rotulo: E
      espessura: 4
    cor: '#00E5FF'
  - id: paral1
    label: ''
    circulo:
      x: 1232
      y: 562
      raio: 26
    cor: '#FFD600'
  - id: paral2
    label: ''
    circulo:
      x: 1519
      y: 613
      raio: 24
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_1
    escalada: Sobe e desce
  - ids:
    - linha_2
    escalada: Questionamentos
  - ids:
    - linha_3
    escalada: Não vai descalço
  - ids:
    - linha_4
    - paral2
    - paral1
    escalada: Linhas paralelas
  - ids:
    - linha_5
    escalada: Só vejo almas
- caminho_imagem_mapa: imagens/setor_tramontina_p1.webp
  largura_mapa: 1825
  altura_mapa: 1369
  pontos_de_interesse:
  - id: linha_6
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 331
          y: 690
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '4'
          raio: 21
        - x: 335
          y: 540
          tipo: PASSAGEM
        - x: 362
          y: 431
          tipo: PASSAGEM
        - x: 408
          y: 334
          tipo: PASSAGEM
        - x: 440
          y: 263
          tipo: PASSAGEM
          rotulo: A
      espessura: 4
    cor: '#00E5FF'
  - id: linha_7
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 651
          y: 658
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '5'
          raio: 21
        - x: 663
          y: 424
          tipo: PASSAGEM
        - x: 673
          y: 305
          tipo: PASSAGEM
        - x: 690
          y: 235
          tipo: PASSAGEM
        - x: 695
          y: 211
          tipo: PASSAGEM
          rotulo: B
      espessura: 4
    cor: '#00E5FF'
  - id: paral1
    label: ''
    circulo:
      x: 207
      y: 642
      raio: 21
    cor: '#FFD600'
  - id: paral2
    label: ''
    circulo:
      x: 437
      y: 660
      raio: 27
    cor: '#FFD600'
  referencias:
  - ids:
    - linha_6
    - paral2
    - paral1
    escalada: Linhas paralelas
  - ids:
    - linha_7
    escalada: Só vejo almas
- caminho_imagem_mapa: imagens/setor_tramontina_p2.webp
  largura_mapa: 1825
  altura_mapa: 1369
  pontos_de_interesse:
  - id: linha_8
    label: ''
    linha:
      estilo: TRACEJADO
      conteudo:
        nos:
        - x: 1376
          y: 764
          tipo: CIRCULO_IDENTIFICADOR
          rotulo: '1'
          raio: 21
        - x: 1323
          y: 631
          tipo: PASSAGEM
        - x: 1306
          y: 547
          tipo: PASSAGEM
        - x: 1279
          y: 431
          tipo: PASSAGEM
        - x: 1210
          y: 364
          tipo: PASSAGEM
        - x: 1153
          y: 323
          tipo: PASSAGEM
          rotulo: ''
      espessura: 4
    cor: '#00E5FF'
  referencias:
  - ids:
    - linha_8
    escalada: Sobe e desce
---
Descida do topo do bloco Tramontina é feita pelo boulder "Sobe e desce".

Setor com vários boulders dos mais variados graus. Destaque a boulders bem acessíveis para pessoal iniciando no climb.

Trilha para o setor começa no setor Fugitivos II, cerca de 2 minutos de caminhada do boulder Olha a Jaca no Fugitivos II. Link para a trilha: https://loc.wiki/t/287028747?wa=sc