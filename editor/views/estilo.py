# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import qtawesome as qta
from PyQt6.QtGui import QIcon

class Icones:
    """Centraliza o mapeamento e estilo de ícones do editor usando QtAwesome."""
    
    COR_NORMAL = "#454545"
    COR_DESTAQUE = "#2b579a"
    COR_SUCESSO = "#28a745"
    COR_ERRO = "#dc3545"
    
    # Mapeamento de ações para identificadores do QtAwesome (FontAwesome 5 Solid/Brands)
    MAPA = {
        "logo": "fa5s.mountain",
        "novo": "fa5s.folder-open",
        "salvar": "fa5s.save",
        "desfazer": "fa5s.undo",
        "refazer": "fa5s.redo",
        "exportar": "fa5s.file-export",
        "celular": "fa5s.mobile-alt",
        "publicar": "fa5b.github",
        "github": "fa5b.github",
        "dados": "fa5s.database",
        "imagens": "fa5s.images",
        "mapas": "fa5s.map-marked-alt",
        "betas": "fa5s.video",
        "historico": "fa5s.history",
        "ciencia": "fa5s.flask",
        "lixeira": "fa5s.trash-alt",
        "check": "fa5s.check",
        "lapis": "fa5s.pencil-alt"
    }

    # Estilo CSS para a barra lateral
    QSS_BARRA_LATERAL = """
        QToolBar {
            background-color: #f8f9fa;
            border-right: 1px solid #dee2e6;
            spacing: 0px;
            padding: 0px;
        }
        QToolButton, QToolButton:hover, QToolButton:checked {
            font-family: "Segoe UI", "MS Shell Dlg 2", "Tahoma", "Arial";
            font-size: 8pt;
            font-weight: 600;
            color: #495057;
            border: none;
            margin: 6px 6px 0px 6px;
            padding-top: 4px;
            padding-bottom: 2px;
        }
        QToolButton:hover {
            background-color: #e9ecef;
            border-radius: 6px;
        }
        QToolButton:checked {
            background-color: #dee2e6;
            color: #2b579a;
            border-radius: 6px;
        }
    """

    @classmethod
    def obter(cls, nome: str, cor: str = None, cor_ativa: str = None) -> QIcon:
        """
        Retorna um QIcon estilizado para a ação solicitada.
        
        Args:
            nome: O identificador da ação (ex: 'salvar', 'mapas').
            cor: Cor hexadecimal opcional. Se omitida, usa COR_NORMAL.
            cor_ativa: Cor hexadecimal para o estado hover/active. Se omitida, usa COR_DESTAQUE.
        """
        identificador = cls.MAPA.get(nome)
        if not identificador:
            return QIcon()
        
        cor_final = cor or cls.COR_NORMAL
        cor_ativa_final = cor_ativa or cls.COR_DESTAQUE
        return qta.icon(
            identificador, 
            color=cor_final, 
            color_active=cor_ativa_final,
            color_selected=cor_ativa_final
        )

    @classmethod
    def obter_destaque(cls, nome: str) -> QIcon:
        """Retorna um QIcon com a cor de destaque do sistema."""
        return cls.obter(nome, cor=cls.COR_DESTAQUE)

    @classmethod
    def obter_celular(cls, conectado: bool = False) -> QIcon:
        """
        Retorna o ícone de celular com um indicador de status (círculo) sobreposto.
        """
        cor_status = cls.COR_SUCESSO if conectado else cls.COR_ERRO
        
        # Usando formato de argumentos posicionais para os ícones e a lista 'options' para o estilo de cada camada
        return qta.icon(
            'fa5s.mobile-alt', 
            'fa5s.circle',
            options=[
                {
                    'color': cls.COR_NORMAL, 
                    'color_active': cls.COR_DESTAQUE
                },
                {
                    'color': cor_status, 
                    'scale_factor': 0.4, 
                    'offset': (0.25, 0.25),
                    'color_active': cls.COR_DESTAQUE
                }
            ]
        )
