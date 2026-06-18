---
name: mapa_corrigir_pontos_de_interesse 
description: Processa pontos de interesse de um mapa, corrigindo sua localização na imagem.
---

# Corrigir pontos de interesse de um mapa 

Um mapa é uma imagem que representa graficamente de maneira reduzida e simplificada os pontos de interesse de um setor de escalada, incluindo vias, boulders, trilhas, acesso, etc. O objetivo dessa skill é corrigir a localização dos pontos de interesse já preenchidos no arquivo JSON.

Para essa skill, você receberá:
* O caminho de uma imagem que representa um mapa de um setor de escalada dentro da pasta `imagens` de um pico de escalada
* Um arquivo `raw_mapas/<imagem>.json` contendo metadados e pontos de interesse sobre a imagem.

Você trabalhará apenas com essa imagem com o arquivo JSON correspondente.

## 1. Conferindo os pontos de interesse

Os pontos de interesse já estão marcados no arquivo JSON. Por exemplo, para o exemplo abaixo, há três pontos de interesse a serem atualizados, "01", "Mesa" e "Seta_Estacionamento":

```json
{
  "dimensoes_imagem": { "largura": 1108, "altura": 1241 },
  "pontos_de_interesse": [
    { "id": "01", "label": "Via 01", "circular": { "x": 684, "y": 824, "raio": 16 } },
    { "id": "Mesa", "label": "Mesa", "box": { "x": 876, "y": 547, "comprimento": 48, "largura": 25 } },
    { "id": "Setor_Diagonal", "label": "Setor Diagonal", "box": { "x": 1167, "y": 637, "comprimento": 265, "largura": 25, "angulo_graus_x100": 3000 } }
  ]
}
```

## 2. Script para verificação da localização dos pontos de interesse 

Para confirmar que cada ponto de interesse está na posição correta, você possui um script que gera uma imagem com as bounding boxes dos pontos de interesse marcados em vermelho. Para gerar a imagem processada, execute o script `python scripts/visualizar_mapa_processado.py --imagem=<caminho_da_imagem> --pontos_json=<caminho_do_json>`. O resultado será uma imagem ao lado do arquivo JSON, `raw_mapas/<arquivo_json>_processado.webp`.

## 3. Acertando a posição das bounding boxes dos pontos de interesse 

> [!IMPORTANT]
> **Loop de Iteração Visual (Execute até acertar)**
> É possível que as bounding boxes necessitem ajustes manuais finos. Faça os ajustes abaixo em loop sem interrupção até atingir um enquadramento **perfeito**:
> 
> 1. Use `run_command`: `python scripts/visualizar_mapa_processado.py --imagem=<caminho_da_imagem> --pontos_json=<caminho_do_json>` para cuspir a imagem processada. **Você tem autonomia para rodar isto quantas vezes precisar.** *Nota:* Se o script der erro de "JSONDecodeError" ou similar, isso significa que você estragou a sintaxe do JSON. Corrija a sintaxe com prioridade máxima antes de continuar!
> 2. Use `view_file` na imagem recém gerada `_processado.webp` para visualizá-la.
> 3. Observe a caixa (ou círculo) vermelho. Ele está perfeitamente delimitando APENAS o texto/label do ponto correspondente? Se não estiver:
> 4. Ajuste os valores literais no arquivo `.json`:
>    * **x, y**: Mova o **centro** do item para alinhar com o texto.
>    * **comprimento, largura / raio**: Ajuste as dimensões para que fiquem justas ao redor do texto.
>    * **angulo_graus_x100**: Caso o texto esteja inclinado no mapa, ajuste o ângulo para que a caixa rotacione e se alinhe perfeitamente.
> 5. Repita o passo 1 até que todos os textos estejam perfeitamente enquadrados.
> 
> Não se preocupe em trabalhar rápido, foque na exatidão finíssima.

## 4 Conferência nos pontos de interesse

Faça uma última conferência, **um ponto de interesse de cada vez**, para garantir que **todas** as marcações vermelhas estão perfeitamente enquadrando os textos/labels dos pontos de interesse correspondentes no mapa. Caso algum não estiver perfeito, volte à etapa 3 para ajustar apenas esses pontos de interesse, sem mexer nos outros que já estão corretos. Repita isso até que **todos** os pontos estejam enquadrando perfeitamente os textos/labels dos pontos de interesse.

## 5. Quando usar essa habilidade

Use essa habilidade quando precisar corrigir os pontos de interesse de um mapa de um setor de escalada.