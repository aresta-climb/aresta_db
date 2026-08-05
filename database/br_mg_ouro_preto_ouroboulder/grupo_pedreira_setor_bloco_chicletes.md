---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (c) Aresta Contributors
nome: 'Bloco: Chicletes'
mapas:
- caminho_imagem_mapa: imagens/grupo_pedreira_setor_bloco_chicletes_p0.webp
  largura_mapa: 2364
  altura_mapa: 1773
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 836
      y: 1176
      raio: 20
  - id: '2'
    label: '2'
    circulo:
      x: 939
      y: 1226
      raio: 20
  - id: 3/1A
    label: '3'
    circulo:
      x: 1437
      y: 1420
      raio: 20
  referencias:
  - escalada: Trident
    ids:
    - '1'
  - escalada: Big-Big
    ids:
    - '2'
  - ids:
    - 3/1A
    grupo: Pedreira
    setor: 'Bloco: Chicletes'
    escalada: Babaloo
- caminho_imagem_mapa: imagens/grupo_pedreira_setor_bloco_chicletes_p1.webp
  largura_mapa: 2364
  altura_mapa: 1773
  pontos_de_interesse:
  - id: A
    label: A
    circulo:
      x: 854
      y: 298
      raio: 20
  - id: B
    label: B
    circulo:
      x: 2344
      y: 960
      raio: 20
  - id: '1'
    label: '1'
    circulo:
      x: 920
      y: 1511
      raio: 20
  referencias:
  - escalada: Babaloo
    ids:
    - '1'
    - A
  - escalada: Chicletes
    ids:
    - '1'
    - B
escaladas:
- boulder:
    nome: Trident
    dificuldade: V10
- boulder:
    nome: Big-Big
    dificuldade: V9
- boulder:
    nome: Babaloo
    dificuldade: V7
- boulder:
    nome: Chicletes
    dificuldade: V11
---

