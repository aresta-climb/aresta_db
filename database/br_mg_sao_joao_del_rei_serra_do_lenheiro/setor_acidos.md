---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
caminho_imagem_capa: imagens/setor_acidos_p1_i2.webp
nome: Ácidos
mapas:
- caminho_imagem_mapa: imagens/setor_acidos_p0_i2.webp
  largura_mapa: 1212
  altura_mapa: 909
  pontos_de_interesse:
  - id: '1'
    label: '1'
    circulo:
      x: 1132
      y: 887
      raio: 21
  - id: '2'
    label: '2'
    circulo:
      x: 1012
      y: 855
      raio: 20
  - id: '3'
    label: '3'
    circulo:
      x: 871
      y: 848
      raio: 20
  - id: '4'
    label: '4'
    circulo:
      x: 753
      y: 793
      raio: 20
  - id: '5'
    label: '5'
    circulo:
      x: 670
      y: 793
      raio: 20
  - id: '6'
    label: '6'
    circulo:
      x: 459
      y: 407
      raio: 20
  - id: '7'
    label: '7'
    circulo:
      x: 323
      y: 440
      raio: 20
  - id: '8'
    label: '8'
    circulo:
      x: 149
      y: 372
      raio: 20
  - id: '9'
    label: '9'
    circulo:
      x: 50
      y: 271
      raio: 20
  - id: setor_bloco_dos_dois_dedos
    label: Dois Dedos
    retangulo:
      x: 1148
      y: 446
      comprimento: 126
      largura: 52
  referencias:
  - escalada: Ácido Clorídrico
    ids:
    - '1'
  - escalada: Ácido Sulfúrico
    ids:
    - '2'
  - escalada: Ácido Lático
    ids:
    - '3'
  - escalada: Olho Clínico
    ids:
    - '4'
  - escalada: Nitroglicerina
    ids:
    - '5'
  - escalada: Carga Explosiva
    ids:
    - '6'
  - escalada: Menina dos Olhos
    ids:
    - '7'
  - escalada: Capitão Nascimento
    ids:
    - '8'
  - escalada: Isolamento Social
    ids:
    - '9'
  - setor: Bloco dos Dois Dedos
    ids:
    - setor_bloco_dos_dois_dedos
escaladas:
- via_esportiva:
    nome: Ácido Clorídrico
    dificuldade: BR_7A
    extensao: 17
    quantidade_protecoes_intermediarias: 6
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Everton Alves
    - Jonatas Lima
    - Jefferson Lara
    descricao: Sua linha tem início em agarras e depois segue por bons abaulados.
      Desborda toda a aresta em diagonal pra esquerda até encontrar o top da Ácido
      Lático. São 6 chapeletas e mais o top.
- via_esportiva:
    nome: Ácido Sulfúrico
    dificuldade: BR_7C
    extensao: 15
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Pedro Naves
    - Bruno Bastos
    data_abertura: '2023-05-22'
    descricao: Linha mais nova do setor. Segue vertical até a quarta chapa onde junta
      com a Clorídrico e termina na Lático.
- via_esportiva:
    nome: Ácido Lático
    dificuldade: BR_7B
    extensao: 12
    destaque: true
    quantidade_protecoes_intermediarias: 5
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - João Felippin
    - Everton Alves
    descricao: Primeira via conquistada no setor e também a mais clássica! Possui
      uma interessante movimentação técnica. Seus lances peculiares com pockets, abaulados
      e lances de equilíbrio fazem dela uma via desafiadora e por isso foi supergraduada
      no início. Divide o mesmo top com a via Ácido Clorídrico. São 5 chapas e mais
      o top.
- via_esportiva:
    nome: Olho Clínico
    dificuldade: BR_7B
    extensao: 12
    quantidade_protecoes_intermediarias: 5
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Dois grampos no top
    conquistadores:
    - Jonatas Lima
    data_abertura: '2013'
    descricao: Esta é uma via que pode se tornar clássica do setor. Uma saída técnica
      passando a lances de oposição até acessar um grande platô, de onde necessita
      boa leitura caso escale à vista nos lances negativos debaixo do teto até fazer
      uma virada em grandes agarras. São 5 chapeletas e mais dois grampos no top.
- via_esportiva:
    nome: Nitroglicerina
    dificuldade: BR_7C
    quantidade_protecoes_intermediarias: 4
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Jonatas Lima
    data_abertura: '2005'
    descricao: Segunda via aberta no setor, extremamente explosiva e com passadas
      esticadas em dinâmicos e lances certeiros minam a resistência do escalador que
      ainda tem que dominar um negativo antes de costurar o top final. São 4 chapas
      e mais duas no top.
- via_esportiva:
    nome: Carga Explosiva
    dificuldade: BR_7C
    quantidade_protecoes_intermediarias: 6
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Jonatas Lima
    - Fabrício Nascimento
    data_abertura: '2012'
    descricao: Essa via possui a mesma saída da via Nitroglicerina, porém após a segunda
      proteção a linha segue para a esquerda em uma escalada horizontal até um pequeno
      teto. Após isso a via segue vertical até a parada. 6 + 2 chapas.
- via_esportiva:
    nome: Menina dos Olhos
    dificuldade: BR_7A
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Jonatas Lima
    - Fabrício Nascimento
    data_abertura: '2012'
    descricao: É uma via curta, porém de rara beleza! Com agarras diferenciadas, como
      buracos bidedos e tridedos, variedade de agarras. Via curta, porém exigente
      apesar da graduação. Aconselha-se sair com a primeira proteção costurada.
- via_esportiva:
    nome: Capitão Nascimento
    dificuldade: BR_8B_BARRA_8C
    extensao: 10
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Jonatas Lima
    - Andréa Carvalho
    data_abertura: '2014'
    descricao: Eis que temos a via mais difícil do setor. Uma via curta, porém praticamente
      todos os lances são de boulder. Seu crux é logo da primeira para a segunda chapa,
      após são lances de boulder mais diluídos, porém mantém uma constância até a
      parada dupla.
- via_esportiva:
    nome: Isolamento Social
    dificuldade: BR_7C_BARRA_8A
    extensao: 8
    quantidade_protecoes_parada: 2
    tipo_ancoragem: Parada dupla
    conquistadores:
    - Pedro Naves
    - Mariana Fiche
    data_abertura: '2021-08-15'
    descricao: Via curta, mas inteira dura. Seus micro-regletes e monodedos com movimentação
      de difícil leitura fazem dela um belo desafio pra escalada à vista. Ao final
      passa pra outra face da rocha à esquerda. Sugere-se entrar com as costuras no
      lugar, pois as agarras de costura são bem ruins.
---

# Setor Ácidos

O setor Ácidos apresenta como característica vias verticais com movimentações surpreendentes, podendo ser utilizados entalamentos, bidedo, calcanhar e movimentos dinâmicos. As linhas necessitam de uma leitura apurada e muita criatividade. Todas as vias são fixas e com parada dupla no top.

Localizado no início da formação rochosa da Serra do Lenheiro ao lado do Bloco dos Dois Dedos, tem como grande vantagem a rápida aproximação, pois encontra-se muito próximo da estrada que sobe para o CEMONTA, é a primeira formação mais vertical do lado esquerdo. Fica na sombra durante toda a tarde, porém totalmente no sol de manhã.

## Dica

Como o setor possui todas as vias acima de sétimo grau, uma opção usada por aqueles que querem escalar algo mais fácil é fazer o início da via Olho Clínico e na metade passar pra Ácido Lático, deve dar algo em torno de sexto grau. Por ser uma linha reta pode ser feita em Top-rope e tem o apelido de Olho Lático.

O setor Ácidos apresenta como característica vias verticais com movimentações surpreendentes, podendo ser utilizados entalamentos, bidedo, calcanhar e movimentos dinâmicos. As linhas necessitam de uma leitura apurada e muita criatividade. Todas as vias são fixas e com parada dupla no top.

Localizado no início da formação rochosa da Serra do Lenheiro ao lado do Bloco dos Dois Dedos, tem como grande vantagem a rápida aproximação, pois encontra-se muito próximo da estrada que sobe para o CEMONTA, é a primeira formação mais vertical do lado esquerdo. Fica na sombra durante toda a tarde, porém totalmente no sol de manhã.