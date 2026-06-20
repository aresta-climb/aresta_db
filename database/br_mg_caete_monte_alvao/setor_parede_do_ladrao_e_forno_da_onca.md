---
nome: Parede do Ladrão e Forno da Onça
mapas:
- caminho_imagem_mapa: imagens/setor_parede_do_ladrao_e_forno_da_onca_p0.webp
  largura_mapa: 2048
  altura_mapa: 1712
  pontos_de_interesse:
  - id: 1am
    label: 1am
    box:
      x: 106
      y: 728
      comprimento: 28
      largura: 41
  - id: 2am
    label: 2am
    box:
      x: 167
      y: 840
      comprimento: 36
      largura: 47
  - id: 3am
    label: 3am
    box:
      x: 159
      y: 720
      comprimento: 34
      largura: 43
  - id: 4am
    label: 4am
    box:
      x: 238
      y: 756
      comprimento: 29
      largura: 39
  - id: 5am
    label: 5am
    box:
      x: 255
      y: 670
      comprimento: 28
      largura: 41
  - id: 6am
    label: 6am
    box:
      x: 678
      y: 711
      comprimento: 35
      largura: 48
  - id: 1az
    label: 1az
    box:
      x: 852
      y: 728
      comprimento: 26
      largura: 39
  - id: 2az
    label: 2az
    box:
      x: 1000
      y: 684
      comprimento: 29
      largura: 35
  - id: 3az
    label: 3az
    box:
      x: 1141
      y: 642
      comprimento: 32
      largura: 42
  - id: 4az
    label: 4az
    box:
      x: 1426
      y: 748
      comprimento: 32
      largura: 43
  - id: 5az
    label: 5az
    box:
      x: 1512
      y: 688
      comprimento: 31
      largura: 44
  - id: 6az
    label: 6az
    box:
      x: 1614
      y: 572
      comprimento: 33
      largura: 44
  - id: 7az
    label: 7az
    box:
      x: 1752
      y: 558
      comprimento: 32
      largura: 47
  referencias:
  - escalada: Cuidado Ketely
    ids:
    - 1am
  - escalada: You will survive
    ids:
    - 2am
  - escalada: Cara ou Coroa
    ids:
    - 3am
  - escalada: French CanCan
    ids:
    - 4am
  - escalada: On the road again
    ids:
    - 5am
  - escalada: Incrível mas verdadeiro
    ids:
    - 6am
  - escalada: Bouder com leite
    ids:
    - 1az
  - escalada: Chipie chipie
    ids:
    - 2az
  - escalada: Bambi
    ids:
    - 3az
  - escalada: Ana Thor
    ids:
    - 4az
  - escalada: Au bout des doigts
    ids:
    - 5az
  - escalada: Boom Boom
    ids:
    - 6az
  - escalada: Petit Pichou
    ids:
    - 7az
setores:
- conteudo:
    nome: Forno da Onça
    escaladas:
    - via_esportiva:
        nome: Cuidado Ketely
        dificuldade: BR_6
        extensao: 24
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_esportiva:
        nome: You will survive
        dificuldade: BR_7A
        extensao: 20
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_esportiva:
        nome: Cara ou Coroa
        dificuldade: BR_6
        extensao: 22
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_esportiva:
        nome: French CanCan
        dificuldade: BR_6SUP
        extensao: 28
        quantidade_protecoes_intermediarias: 5
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_esportiva:
        nome: On the road again
        dificuldade: BR_6SUP
        extensao: 18
        quantidade_protecoes_intermediarias: 5
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_multiplas_enfiadas:
        nome: Incrível mas verdadeiro
        dificuldade_media: BR_6
        dificuldade_maxima: BR_6
        quantidade_costuras_intermediarias: 12
        quantidade_equipamentos_parada: 2
        comprimento_total: 50
        numero_enfiadas: 2
        tipo_via_multiplas_enfiadas: MISTA
        conquistadores:
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_4
            extensao: 15
        - via_esportiva:
            nome: L2
            dificuldade: BR_6
            extensao: 35
            descricao: mista
- conteudo:
    nome: Parede do Ladrão
    escaladas:
    - via_esportiva:
        nome: Bouder com leite
        dificuldade: BR_5
        extensao: 25
        quantidade_protecoes_intermediarias: 4
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: Chipie chipie
        dificuldade: BR_4SUP
        extensao: 23
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: Bambi
        dificuldade: BR_4
        extensao: 20
        quantidade_protecoes_intermediarias: 4
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: Ana Thor
        dificuldade: BR_7C
        extensao: 15
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: Au bout des doigts
        dificuldade: BR_7B
        extensao: 22
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 3
        conquistadores:
        - Pablo Gonçalves
        - Jg
        descricao: Base no platô superior
    - via_esportiva:
        nome: Boom Boom
        dificuldade: BR_6SUP
        extensao: 28
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: Petit Pichou
        dificuldade: BR_6SUP
        extensao: 28
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
---
# Parede do Ladrão e Forno da Onça

Estes setores estão localizados lado a lado no Alto Monte Alvão.
