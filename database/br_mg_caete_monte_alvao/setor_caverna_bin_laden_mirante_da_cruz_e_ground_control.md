---
nome: Caverna, Mirante e Ground Control
mapas:
- caminho_imagem_mapa: imagens/setor_caverna_bin_laden_mirante_da_cruz_e_ground_control_p0.webp
  largura_mapa: 2048
  altura_mapa: 1721
  pontos_de_interesse:
  - id: 1ros
    label: 1ros
    box:
      x: 948
      y: 184
      comprimento: 30
      largura: 47
  - id: 2ros
    label: 2ros
    box:
      x: 982
      y: 286
      comprimento: 29
      largura: 46
  - id: 3ros
    label: 3ros
    box:
      x: 904
      y: 256
      comprimento: 30
      largura: 50
  - id: 4ros
    label: 4ros
    box:
      x: 937
      y: 360
      comprimento: 34
      largura: 44
  - id: 5ros
    label: 5ros
    box:
      x: 816
      y: 248
      comprimento: 35
      largura: 50
  - id: 6ros
    label: 6ros
    box:
      x: 912
      y: 182
      comprimento: 31
      largura: 47
  - id: 1az
    label: '1'
    box:
      x: 570
      y: 1194
      comprimento: 27
      largura: 43
  - id: 2az
    label: '2'
    box:
      x: 528
      y: 1362
      comprimento: 38
      largura: 46
  - id: 3az
    label: '3'
    box:
      x: 590
      y: 1407
      comprimento: 39
      largura: 52
  - id: 4az
    label: '4'
    box:
      x: 536
      y: 1508
      comprimento: 28
      largura: 40
  - id: 5az
    label: '5'
    box:
      x: 606
      y: 1494
      comprimento: 37
      largura: 51
  - id: 6az
    label: '6'
    box:
      x: 608
      y: 1575
      comprimento: 35
      largura: 50
  - id: 1rox
    label: 1rox
    box:
      x: 1052
      y: 163
      comprimento: 29
      largura: 50
  - id: 2rox
    label: 2rox
    box:
      x: 1116
      y: 194
      comprimento: 32
      largura: 57
  - id: 3rox
    label: 3rox
    box:
      x: 1172
      y: 196
      comprimento: 37
      largura: 47
  - id: 4rox
    label: 4rox
    box:
      x: 1252
      y: 210
      comprimento: 35
      largura: 47
  - id: 5rox
    label: 5rox
    box:
      x: 1359
      y: 213
      comprimento: 30
      largura: 50
  - id: 6rox
    label: 6rox
    box:
      x: 1456
      y: 218
      comprimento: 34
      largura: 53
  - id: 7rox
    label: 7rox
    box:
      x: 1582
      y: 220
      comprimento: 33
      largura: 50
  - id: 8rox
    label: 8rox
    box:
      x: 1664
      y: 236
      comprimento: 33
      largura: 50
  - id: 9rox
    label: 9rox
    box:
      x: 1730
      y: 303
      comprimento: 32
      largura: 48
  - id: 10rox
    label: 10rox
    box:
      x: 1753
      y: 246
      comprimento: 56
      largura: 46
  - id: 11rox
    label: 11rox
    box:
      x: 1634
      y: 436
      comprimento: 45
      largura: 53
  - id: 12rox
    label: 12rox
    box:
      x: 1543
      y: 438
      comprimento: 50
      largura: 51
setores:
- conteudo:
    nome: Caverna do Bin Laden
    escaladas:
    - via_esportiva:
        nome: Capitã Minhoca
        id_no_mapa: 1ros
        dificuldade: BR_5SUP
        extensao: 22
        quantidade_protecoes_intermediarias: 5
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_multiplas_enfiadas:
        nome: He Man
        id_no_mapa: 2ros
        dificuldade_media: BR_6SUP
        dificuldade_maxima: BR_7B
        quantidade_costuras_intermediarias: 8
        quantidade_equipamentos_parada: 2
        comprimento_total: 65
        numero_enfiadas: 4
        tipo_via_multiplas_enfiadas: TODA_FIXA
        conquistadores:
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_6
            extensao: 18
        - via_esportiva:
            nome: L2
            dificuldade: BR_3
            extensao: 15
        - via_esportiva:
            nome: L3
            dificuldade: BR_7B
            extensao: 15
        - via_esportiva:
            nome: L4
            dificuldade: BR_2SUP
            extensao: 20
            descricao: free
    - via_multiplas_enfiadas:
        nome: Esqueleto
        id_no_mapa: 3ros
        dificuldade_media: BR_6
        dificuldade_maxima: BR_6
        quantidade_costuras_intermediarias: 8
        quantidade_equipamentos_parada: 2
        comprimento_total: 65
        numero_enfiadas: 4
        tipo_via_multiplas_enfiadas: MISTA
        conquistadores:
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_6
            extensao: 18
        - via_esportiva:
            nome: L2
            dificuldade: BR_3
            extensao: 15
        - via_esportiva:
            nome: L3
            dificuldade: BR_6
            extensao: 15
            descricao: mista
        - via_esportiva:
            nome: L4
            dificuldade: BR_2SUP
            extensao: 20
            descricao: free
    - via_esportiva:
        nome: Allahu Akbar
        id_no_mapa: 4ros
        dificuldade: BR_7A
        extensao: 22
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_esportiva:
        nome: Saída à Francesa
        id_no_mapa: 5ros
        dificuldade: BR_8B
        extensao: 24
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
        conquistadores:
        - Pablo Gonçalves
        - Jg
    - via_esportiva:
        nome: Paris em Chamas
        id_no_mapa: 6ros
        dificuldade: BR_10A
        descricao: 10?
        extensao: 24
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
        conquistadores:
        - Pablo Gonçalves
        - Fred Gonçalves
- conteudo:
    nome: Mirante da Cruz
    escaladas:
    - via_esportiva:
        nome: Urubu tá com raiva do boi
        id_no_mapa: 1az
        dificuldade: BR_5SUP
        extensao: 30
        quantidade_protecoes_intermediarias: 7
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
    - via_esportiva:
        nome: Maria Teresa
        id_no_mapa: 2az
        dificuldade: BR_6
        extensao: 26
        quantidade_protecoes_intermediarias: 5
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
    - via_esportiva:
        nome: Uma gota de milagre
        id_no_mapa: 3az
        dificuldade: BR_7A
        extensao: 28
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
    - via_esportiva:
        nome: Quem não chora não mama
        id_no_mapa: 4az
        dificuldade: BR_7B
        extensao: 28
        quantidade_protecoes_intermediarias: 9
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
    - via_esportiva:
        nome: Chapolin
        id_no_mapa: 5az
        dificuldade: BR_7A
        extensao: 30
        quantidade_protecoes_intermediarias: 9
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
    - via_esportiva:
        nome: Desvio na pista
        id_no_mapa: 6az
        dificuldade: BR_7B
        extensao: 30
        quantidade_protecoes_intermediarias: 9
        quantidade_protecoes_parada: 2
        conquistadores:
        - jg
- conteudo:
    nome: Ground Control
    escaladas:
    - via_movel:
        nome: Essa via não é minha
        id_no_mapa: 1rox
        dificuldade: BR_4SUP
        extensao: 70
        conquistadores:
        - Rander Jr Sidnei
    - via_esportiva:
        nome: Vento da Patagônia
        id_no_mapa: 2rox
        dificuldade: BR_5
        extensao: 30
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
        conquistadores:
        - Danilo Steling
    - via_multiplas_enfiadas:
        nome: Mr Bean
        id_no_mapa: 3rox
        dificuldade_media: BR_6SUP
        dificuldade_maxima: BR_7A
        quantidade_costuras_intermediarias: 10
        quantidade_equipamentos_parada: 2
        comprimento_total: 70
        numero_enfiadas: 3
        tipo_via_multiplas_enfiadas: TODA_FIXA
        conquistadores:
        - Pablo Gonçalves
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_6
            extensao: 30
        - via_esportiva:
            nome: L2
            dificuldade: BR_7A
            extensao: 18
        - via_esportiva:
            nome: L3
            dificuldade: BR_2SUP
            extensao: 22
            descricao: free
    - via_esportiva:
        nome: Lagarto de aniversário
        id_no_mapa: 4rox
        dificuldade: BR_6
        extensao: 30
        quantidade_protecoes_intermediarias: 10
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
        descricao: Variante Mr Bean
    - via_esportiva:
        nome: Cavuca tatu
        id_no_mapa: 5rox
        dificuldade: BR_7A
        extensao: 30
        quantidade_protecoes_intermediarias: 10
        quantidade_protecoes_parada: 2
        conquistadores:
        - Jg
    - via_movel:
        nome: Zé colmeia e Dona Flor
        id_no_mapa: 6rox
        dificuldade: BR_4SUP
        extensao: 30
        conquistadores:
        - Sidnei
        - Natita
        descricao: Parada fixa
    - via_esportiva:
        nome: Tirolês
        id_no_mapa: 7rox
        dificuldade: BR_5
        extensao: 30
        quantidade_protecoes_intermediarias: 6
        quantidade_protecoes_parada: 2
    - via_esportiva:
        nome: 10 c
        id_no_mapa: 8rox
        dificuldade: BR_6
        extensao: 30
        quantidade_protecoes_intermediarias: 8
        quantidade_protecoes_parada: 2
        conquistadores:
        - sidnei
        - Jg
    - via_multiplas_enfiadas:
        nome: Sabor Baunilha
        id_no_mapa: 9rox
        dificuldade_media: BR_7B
        dificuldade_maxima: BR_7B
        quantidade_costuras_intermediarias: 10
        quantidade_equipamentos_parada: 2
        comprimento_total: 50
        numero_enfiadas: 2
        conquistadores:
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_7B
            extensao: 30
        - via_esportiva:
            nome: L2
            dificuldade: BR_5SUP
            extensao: 20
            descricao: expo
    - via_movel:
        nome: O charme da Trad
        id_no_mapa: 10rox
        dificuldade: BR_6
        extensao: 60
        conquistadores:
        - Pablo Gonçalves
        - Jg
        descricao: Parada fixa
    - via_multiplas_enfiadas:
        nome: Café Ole
        id_no_mapa: 11rox
        dificuldade_media: BR_5
        dificuldade_maxima: BR_5SUP
        quantidade_costuras_intermediarias: 8
        quantidade_equipamentos_parada: 2
        comprimento_total: 55
        numero_enfiadas: 2
        conquistadores:
        - Jg
        - Ana de Papel
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_4SUP
            extensao: 20
        - via_esportiva:
            nome: L2
            dificuldade: BR_5SUP
            extensao: 35
    - via_multiplas_enfiadas:
        nome: Tio Tonton
        id_no_mapa: 12rox
        dificuldade_media: BR_6SUP
        dificuldade_maxima: BR_7B
        quantidade_costuras_intermediarias: 10
        quantidade_equipamentos_parada: 2
        comprimento_total: 55
        numero_enfiadas: 2
        conquistadores:
        - Jg
        enfiadas:
        - via_esportiva:
            nome: L1
            dificuldade: BR_4SUP
            extensao: 20
        - via_esportiva:
            nome: L2
            dificuldade: BR_6
            descricao: crux 7b
---
# Caverna, Mirante e Ground Control

Este grupo engloba os setores localizados na parte central do Alto Monte Alvão.
