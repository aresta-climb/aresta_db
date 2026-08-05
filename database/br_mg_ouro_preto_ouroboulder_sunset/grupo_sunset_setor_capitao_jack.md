---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Contributors
nome: Capitão Jack
escaladas:
- boulder:
    nome: Amnesia
    destaque: true
    dificuldade: V3
- boulder:
    nome: Capitão Jack
    destaque: true
    dificuldade: V6
    descricao: Virada exposta, atenção na segurança!
- boulder:
    nome: Purple Rase
    dificuldade: V5
    descricao: Começa em uma fenda bem a esquerda, faz a travessia e vira no Amnésia
- boulder:
    nome: Sunshine
    dificuldade: V6
    descricao: Começa perto do chão de areia bem a direita e vira no Amnésia
mapas:
- caminho_imagem_mapa: imagens/grupo_sunset_setor_capitao_jack_p0.webp
  largura_mapa: 374
  altura_mapa: 336
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 251
      y: 307
      raio: 9
  - id: x
    label: x
    circulo:
      x: 12
      y: 12
      raio: 9
  referencias:
  - escalada: Sunshine
    ids:
    - '1'
    - x
- caminho_imagem_mapa: imagens/grupo_sunset_setor_capitao_jack_p1.webp
  largura_mapa: 845
  altura_mapa: 805
  pontos_de_interesse:
  - id: 1_b
    label: '1'
    circulo:
      x: 805
      y: 704
      raio: 9
  - id: '2'
    label: '2'
    circulo:
      x: 379
      y: 666
      raio: 10
  - id: '3'
    label: '3'
    circulo:
      x: 294
      y: 734
      raio: 9
  - id: y
    label: y
    circulo:
      x: 256
      y: 13
      raio: 10
  - id: x_b
    label: x
    circulo:
      x: 562
      y: 15
      raio: 9
  referencias:
  - escalada: Amnesia
    ids:
    - 1_b
    - x_b
  - escalada: Capitão Jack
    ids:
    - '2'
    - y
  - escalada: Purple Rase
    ids:
    - '3'
    - x_b
---

# Bloco Capitão Jack