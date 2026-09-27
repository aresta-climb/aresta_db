---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
nome: Falésias do Lenheiro
mapas:
- caminho_imagem_mapa: imagens/setor_falesias_do_lenheiro_p0_i2.webp
  largura_mapa: 1043
  altura_mapa: 782
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 108
      y: 641
      raio: 19
  - id: '2'
    label: '2'
    circulo:
      x: 282
      y: 644
      raio: 19
  - id: '3'
    label: '3'
    circulo:
      x: 775
      y: 529
      raio: 19
  referencias:
  - escalada: Esqueleto do Tempo
    ids:
    - '1'
  - escalada: Parou Mofô
    ids:
    - '2'
  - escalada: Via Normal da Agulhinha Pequeno Polegar
    ids:
    - '3'
- caminho_imagem_mapa: imagens/setor_falesias_do_lenheiro_p1_i2.webp
  largura_mapa: 481
  altura_mapa: 641
  pontos_de_interesse:
  - id: '4'
    label: '4'
    circulo:
      x: 103
      y: 599
      raio: 27
  - id: '5'
    label: '5'
    circulo:
      x: 289
      y: 563
      raio: 27
  - id: '6'
    label: '6'
    circulo:
      x: 363
      y: 546
      raio: 27
  referencias:
  - escalada: Miosótis
    ids:
    - '4'
  - escalada: Chá das Cinco
    ids:
    - '5'
  - escalada: Dança dos Vampiros
    ids:
    - '6'
- caminho_imagem_mapa: imagens/setor_falesias_do_lenheiro_p1_i3.webp
  largura_mapa: 1068
  altura_mapa: 801
  pontos_de_interesse:
  - id: '7'
    label: '7'
    circulo:
      x: 518
      y: 726
      raio: 20
  - id: '8'
    label: '8'
    circulo:
      x: 594
      y: 263
      raio: 22
  - id: paredao_2_5
    label: Paredão 2,5
    retangulo:
      x: 166
      y: 601
      comprimento: 226
      largura: 45
  referencias:
  - escalada: Deixa a Fenda Me Levar
    ids:
    - '7'
  - escalada: Brassavola
    ids:
    - '8'
  - ids:
    - paredao_2_5
- caminho_imagem_mapa: imagens/setor_falesias_do_lenheiro_p2_i3.webp
  largura_mapa: 481
  altura_mapa: 641
  pontos_de_interesse:
  - id: '9'
    label: '9'
    circulo:
      x: 215
      y: 439
      raio: 20
  - id: '10'
    label: '10'
    circulo:
      x: 427
      y: 585
      raio: 25
  referencias:
  - escalada: Feliz Aniversário
    ids:
    - '9'
  - escalada: Juízo Final
    ids:
    - '10'
- caminho_imagem_mapa: imagens/setor_falesias_do_lenheiro_p2_i2.webp
  largura_mapa: 1149
  altura_mapa: 862
  pontos_de_interesse:
  - id: '11'
    label: '11'
    circulo:
      x: 374
      y: 798
      raio: 28
  - id: tres_pontoes
    label: Três Pontões
    retangulo:
      x: 836
      y: 90
      comprimento: 256
      largura: 42
  referencias:
  - escalada: Por Favor Me Esqueça
    ids:
    - '11'
  - grupo: Três Pontões (CEMONTA)
    ids:
    - tres_pontoes
escaladas:
- via_esportiva:
    nome: Esqueleto do Tempo
    dificuldade: BR_6SUP_BARRA_7A
    extensao: 15
    quantidade_protecoes_intermediarias: 7
    quantidade_protecoes_parada: 1
    conquistadores:
    - Antônio Gilmar (Tonhão)
    - João Vagli
    data_abertura: '2025-03-15'
    descricao: Saída levemente negativa e depois pega uma diagonal pra direita, são
      7 chapas e mais o top.
- via_esportiva:
    nome: Parou Mofô
    dificuldade: BR_5SUP_BARRA_6
    extensao: 15
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 1
    conquistadores:
    - Antônio Gilmar (Tonhão)
    - João Vagli
    data_abertura: '2025-03-15'
    descricao: Via reta que termina na mesma parada da via anterior, são 4 chapas
      e mais o top.
- via_movel:
    nome: Via Normal da Agulhinha Pequeno Polegar
    dificuldade: BR_4
    extensao: 15
    conquistadores:
    - Tonico Magalhães
    - André Ilha
    data_abertura: '1984-04-28'
    descricao: Pequena via localizada ao final da falésia do Bloco dos Dois Dedos
      à direita. À partir da via Suco de Laranja acompanhar a rocha pra direita até
      o final. Saindo da estrada, subir alguns metros após os Dois Dedos e subir um
      rampado de pedras e mato à esquerda.
- via_movel:
    nome: Miosótis
    dificuldade: BR_1SUP
    extensao: 35
    conquistadores:
    - André Ilha
    - Lúcia Duarte
    data_abertura: '1984-07-23'
    descricao: Via muito fácil que sobe por agarras entre duas fendas em formato de
      V, localizada no Paredão 2,5 à direita das rotas de treinamento.
- via_movel:
    nome: Chá das Cinco
    dificuldade: BR_3
    extensao: 35
    conquistadores:
    - André Ilha
    - Kate Benedict
    - Boris Flegr
    data_abertura: '2004-10-10'
    descricao: Início em chaminé pelo lado esquerdo do grande bloco que há entre as
      rochas. Uma vez em cima dele, segue para a óbvia fenda acima, voltada para a
      esquerda. Ao final da fenda segue por um trecho meio quebrado, com lances curtos
      e fáceis até a base do lance final de agarras, que é belíssimo e ligeiramente
      negativo.
- via_movel:
    nome: Dança dos Vampiros
    dificuldade: BR_2SUP
    extensao: 45
    conquistadores:
    - André Ilha
    - Lúcia Duarte
    data_abertura: '1984-07-23'
    descricao: Seu início fica atrás de um grande bloco e por isso não pode ser visto
      de fora. Começa em uma chaminé média até atingir um platô, passando para uma
      chaminé larga até sair por entre os blocos de rocha. Depois segue por agarras.
- via_movel:
    nome: Deixa a Fenda Me Levar
    dificuldade: BR_5
    conquistadores:
    - Márcio Andrade
    - Rodolfo Campos
    data_abertura: '2004-10-10'
    descricao: Via à direita das vias anteriores e possui um bonito diedro no início.
- via_movel:
    nome: Brassavola
    dificuldade: BR_4
    descricao: Variante da via anterior.
- via_movel:
    nome: Feliz Aniversário
    dificuldade: BR_7B
    conquistadores:
    - Ronaldo Franzen "Nativo"
    descricao: Linha através de um bonito sistema de fendas, levemente negativa em
      alguns pontos. Descida por caminhada à direita.
- via_movel:
    nome: Juízo Final
    dificuldade: BR_4
    extensao: 25
    conquistadores:
    - André Ilha
    - Lúcia Duarte
    data_abertura: '1984-07-27'
    descricao: Bela fissura que percorre boa parte da via, intercalando com lances
      de boas agarras.
- via_movel:
    nome: Por Favor Me Esqueça
    dificuldade: BR_5
    extensao: 20
    conquistadores:
    - Eduardo Rodrigues (Edu RC)
    - Marcello Goulart
    data_abertura: '2024-08-07'
    descricao: Via bem divertida. Pegar a segunda trilha descendo a estrada a partir
      do portão do Cemonta. Após cerca de 50m abandonar a trilha principal e pegar
      um corte de agua meio fechado pra direita e transpor uns blocos.
---

# Falésias do Lenheiro

Este não é exatamente um setor, é na verdade o corpo rochoso que vai desde o Bloco dos Dois Dedos até os Três Pontões e contém várias vias espalhadas em pequenos setores ou isoladas. Aqui estão também setores de treinamentos militares denominados Paredão 1, 2, 2½, 3 e 4 (este último encontra-se na parte de trás da montanha) e podem ser visualizados no mapa no início deste guia. As rotas de treinamento estão pintadas na rocha com numeração de 1 a 10 e são em geral móveis ou top-rope/rapel de baixa graduação e podem ser usadas por quem se interessar.

![Vista geral das Falésias do Lenheiro](imagens/setor_falesias_do_lenheiro_p0_i3.webp)

## Paredão 2,5

Bloco que faz parte das Falésias do Lenheiro.

## Bloco Oculto

Belo bloco que fica bem escondido na parte alta da falésia e com acesso um pouco complicado, visualizar no mapa no início deste guia. Pode-se acessar pelo Cemonta, percorrendo o Paredão 1 para a esquerda até o final e depois subindo um trepa pedras ou através do Paredão 2, subindo a falésia em diagonal pra direita.