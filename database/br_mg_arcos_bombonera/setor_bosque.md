---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Setor Bosque
mapas:
- caminho_imagem_mapa: imagens/setor_bosque_p0_i0.webp
  largura_mapa: 1966
  altura_mapa: 1043
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 190
      y: 968
      raio: 15
  - id: '2'
    label: '2'
    circulo:
      x: 382
      y: 968
      raio: 15
  - id: '3'
    label: '3'
    circulo:
      x: 604
      y: 968
      raio: 15
  - id: '4'
    label: '4'
    circulo:
      x: 893
      y: 968
      raio: 15
  - id: '5'
    label: '5'
    circulo:
      x: 1007
      y: 968
      raio: 15
  - id: '6'
    label: '6'
    circulo:
      x: 1274
      y: 968
      raio: 15
  - id: '7'
    label: '7'
    circulo:
      x: 1620
      y: 969
      raio: 15
  - id: '8'
    label: '8'
    circulo:
      x: 1748
      y: 968
      raio: 15
  - id: '9'
    label: '9'
    circulo:
      x: 1899
      y: 968
      raio: 15
  referencias:
  - escalada: La Cucaracha
    ids:
    - '1'
  - escalada: (via inacabada 1) Bem Vindo ao Bosque
    ids:
    - '2'
    setor: Setor Bosque
  - escalada: (via inacabada 2)
    ids:
    - '3'
    setor: Setor Bosque
  - escalada: Malandro é Malandro
    ids:
    - '4'
  - escalada: Mané é Mané
    ids:
    - '5'
  - escalada: Segunda Divisão
    ids:
    - '6'
  - escalada: Diedrinho
    ids:
    - '7'
  - escalada: Dona Leci
    ids:
    - '8'
  - escalada: Caminito
    ids:
    - '9'
- caminho_imagem_mapa: imagens/setor_bosque_p1_i0.webp
  largura_mapa: 916
  altura_mapa: 1151
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 519
      y: 1135
      raio: 15
  - id: '2'
    label: '2'
    circulo:
      x: 846
      y: 1127
      raio: 14
  referencias:
  - escalada: La Cucaracha
    ids:
    - '1'
  - escalada: (via inacabada 1) Bem Vindo ao Bosque
    ids:
    - '2'
    setor: Setor Bosque
- caminho_imagem_mapa: imagens/setor_bosque_p1_i1.webp
  largura_mapa: 916
  altura_mapa: 1155
  pontos_de_interesse:
  - id: '3'
    label: '3'
    circulo:
      x: 35
      y: 1132
      raio: 15
  - id: '4'
    label: '4'
    circulo:
      x: 364
      y: 1099
      raio: 15
  - id: '5'
    label: '5'
    circulo:
      x: 478
      y: 1092
      raio: 15
  referencias:
  - escalada: (via inacabada 2)
    ids:
    - '3'
    setor: Setor Bosque
  - escalada: Malandro é Malandro
    ids:
    - '4'
  - escalada: Mané é Mané
    ids:
    - '5'
- caminho_imagem_mapa: imagens/setor_bosque_p2_i0.webp
  largura_mapa: 910
  altura_mapa: 1154
  pontos_de_interesse:
  - id: '6'
    label: '6'
    circulo:
      x: 49
      y: 1134
      raio: 14
  - id: '7'
    label: '7'
    circulo:
      x: 519
      y: 1135
      raio: 14
  - id: '8'
    label: '8'
    circulo:
      x: 646
      y: 1130
      raio: 15
  - id: '9'
    label: '9'
    circulo:
      x: 798
      y: 1118
      raio: 15
  referencias:
  - escalada: Segunda Divisão
    ids:
    - '6'
  - escalada: Diedrinho
    ids:
    - '7'
  - escalada: Dona Leci
    ids:
    - '8'
  - escalada: Caminito
    ids:
    - '9'
escaladas:
- via_esportiva:
    nome: La Cucaracha
    dificuldade: PROJETO
    quantidade_protecoes_intermediarias: 6
    quantidade_protecoes_parada: 2
    data_abertura: '2021'
- via_esportiva:
    nome: (via inacabada 1) Bem Vindo ao Bosque
    dificuldade: INDEFINIDO
    data_abertura: '2020'
- via_esportiva:
    nome: (via inacabada 2)
    dificuldade: INDEFINIDO
    data_abertura: '2020'
- via_esportiva:
    nome: Malandro é Malandro
    dificuldade: BR_8A
    destaque: true
    quantidade_protecoes_intermediarias: 5
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
- via_esportiva:
    nome: Mané é Mané
    dificuldade: BR_8B_BARRA_8C
    destaque: true
    quantidade_protecoes_intermediarias: 5
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
- via_esportiva:
    nome: Segunda Divisão
    dificuldade: BR_7A
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
- via_esportiva:
    nome: Diedrinho
    dificuldade: BR_5SUP
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
- via_esportiva:
    nome: Dona Leci
    dificuldade: BR_5
    destaque: true
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
- via_esportiva:
    nome: Caminito
    dificuldade: BR_5SUP
    quantidade_protecoes_intermediarias: 3
    destaque: true
    quantidade_protecoes_parada: 2
    data_abertura: '2020'
---

Sombra o dia todo (varia de acordo com a estação).