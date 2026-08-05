---
# SPDX-License-Identifier: ODbL-1.0
# Copyright (c) Aresta Contributors
mapas:
- caminho_imagem_mapa: imagens/mapas_gerais_p0.webp
  largura_mapa: 2048
  altura_mapa: 1447
  pontos_de_interesse:
  - id: malibu
    label: Malibu
    poligono:
      coordenadas:
      - 938
      - 1064
      - 977
      - 1076
      - 971
      - 1097
      - 966
      - 1099
      - 943
      - 1094
  - id: terra_do_nunca
    label: Terra do Nunca
    poligono:
      coordenadas:
      - 726
      - 906
      - 758
      - 901
      - 785
      - 913
      - 804
      - 940
      - 795
      - 981
      - 779
      - 982
      - 748
      - 961
      - 729
      - 929
  - id: mirante_da_cruz
    label: Mirante da Cruz
    poligono:
      coordenadas:
      - 677
      - 813
      - 698
      - 795
      - 736
      - 877
      - 693
      - 887
      - 686
      - 834
  - id: curto_e_grosso
    label: Curto e Grosso
    poligono:
      coordenadas:
      - 823
      - 970
      - 914
      - 1036
      - 923
      - 1051
      - 906
      - 1072
      - 903
      - 1067
      - 892
      - 1064
      - 865
      - 1040
      - 845
      - 1039
      - 809
      - 1008
  - id: ground_control
    label: Ground Control
    poligono:
      coordenadas:
      - 733
      - 736
      - 750
      - 741
      - 802
      - 743
      - 803
      - 761
      - 753
      - 765
      - 724
      - 754
  - id: forno_da_onca
    label: Forno da Onça
    poligono:
      coordenadas:
      - 808
      - 748
      - 818
      - 742
      - 831
      - 742
      - 846
      - 748
      - 849
      - 767
      - 845
      - 776
      - 836
      - 778
      - 830
      - 772
      - 816
      - 778
      - 809
      - 766
  - id: caverna_do_bin_laden
    label: Caverna do Bin Laden
    retangulo:
      x: 714
      y: 758
      comprimento: 55
      largura: 8
      angulo_graus_x100: -5973
  - id: parede_do_ladrao
    label: Parede do Ladrão
    poligono:
      coordenadas:
      - 857
      - 774
      - 853
      - 746
      - 877
      - 740
      - 914
      - 737
      - 919
      - 764
  - id: vale_gaules
    label: Vale Gaules
    poligono:
      coordenadas:
      - 673
      - 681
      - 669
      - 648
      - 734
      - 637
      - 722
      - 659
  referencias:
  - setor: Vale Gaules
    ids:
    - vale_gaules
  - ids:
    - caverna_do_bin_laden
    - mirante_da_cruz
    - ground_control
    grupo: Caverna, Mirante e Ground Control
  - ids:
    - parede_do_ladrao
    - forno_da_onca
    grupo: Parede do Ladrão e Forno da Onça
  - ids:
    - terra_do_nunca
    - curto_e_grosso
    - malibu
    grupo: Curto e Grosso, Malibu e Terra do Nunca
---

