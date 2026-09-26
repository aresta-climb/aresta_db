# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Optional, Dict, Any

import qtawesome as qta
from PySide6.QtGui import QIcon


class Icones:
    """Centraliza o mapeamento e estilo de ícones do editor usando QtAwesome."""
    
    COR_NORMAL: str = "#454545"
    COR_DESTAQUE: str = "#2b579a"
    COR_SUCESSO: str = "#28a745"
    COR_ERRO: str = "#dc3545"
    COR_MUTED: str = "#777777"
    
    # Mapeamento de ações para identificadores do QtAwesome (FontAwesome 5 Solid/Brands)
    MAPA: Dict[str, str] = {
        "logo": "fa5s.mountain",
        "novo": "fa5s.folder-open",
        "salvar": "fa5s.save",
        "desfazer": "fa5s.undo",
        "refazer": "fa5s.redo",
        "exportar": "fa5s.file-export",
        "celular": "fa5s.mobile-alt",
        "publicar": "fa5s.paper-plane",
        "enviar": "fa5s.paper-plane",
        "nuvem": "fa5s.cloud-upload-alt",
        "externo": "fa5s.external-link-alt",
        "github": "fa5b.github",
        "dados": "fa5s.database",
        "imagens": "fa5s.images",
        "mapas": "fa5s.map-marked-alt",
        "betas": "fa5s.video",
        "historico": "fa5s.history",
        "ciencia": "fa5s.flask",
        "lixeira": "fa5s.trash-alt",
        "check": "fa5s.check",
        "lapis": "fa5s.pencil-alt",
        "inverter": "fa5s.exchange-alt"
    }

    # Estilo CSS para botão de remoção discreto (ghost icon)
    QSS_BOTAO_REMOVER_DISCRETO: str = """
        QPushButton {
            border: none;
            background-color: transparent;
            padding: 4px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #fee2e2;
        }
    """

    # Estilo CSS para container emoldurado de coleções repetidas
    QSS_CONTAINER_REPEATED_INTEGRADO: str = """
        QFrame#ContainerRepeatedIntegrado {
            border: 1px solid #d0d7de;
            border-radius: 6px;
            background-color: #ffffff;
        }
    """

    # Estilo CSS para o botão de adicionar no rodapé de coleções repetidas
    QSS_BOTAO_RODAPE_ADICIONAR: str = """
        QPushButton {
            background-color: #f6f8fa;
            color: #2b579a;
            border: 1px solid #d0d7de;
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: bold;
            font-size: 9pt;
        }
        QPushButton:hover {
            background-color: #eef3f9;
            border-color: #2b579a;
            color: #1a3b68;
        }
    """

    # Estilo CSS para a barra lateral
    QSS_BARRA_LATERAL: str = """
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

    # Estilo CSS para QToolTip prevenindo o bug de tooltip preto no Windows
    QSS_TOOLTIP: str = """
        QToolTip {
            color: #212529;
            background-color: #ffffff;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 4px 6px;
            font-size: 11px;
            font-family: "Segoe UI", "MS Shell Dlg 2", sans-serif;
        }
    """

    @classmethod
    def obter(cls, nome: str, cor: Optional[str] = None, cor_ativa: Optional[str] = None) -> QIcon:
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
        
        res = qta.icon(
            identificador, 
            color=cor_final, 
            color_active=cor_ativa_final,
            color_selected=cor_ativa_final
        )
        return res if isinstance(res, QIcon) else QIcon(res)

    @classmethod
    def obter_destaque(cls, nome: str) -> QIcon:
        """Retorna um QIcon com a cor de destaque do sistema."""
        return cls.obter(nome, cor=cls.COR_DESTAQUE)

    @classmethod
    def obter_lixeira(cls, cor: Optional[str] = None) -> QIcon:
        """Retorna o ícone de lixeira em vermelho para indicar ação de remoção clara."""
        cor_final = cor or cls.COR_ERRO
        return cls.obter("lixeira", cor=cor_final, cor_ativa=cls.COR_ERRO)

    @classmethod
    def obter_celular(cls, conectado: bool = False) -> QIcon:
        """
        Retorna o ícone de celular com um indicador de status (círculo) sobreposto.
        """
        cor_status = cls.COR_SUCESSO if conectado else cls.COR_ERRO
        
        # Usando formato de argumentos posicionais para os ícones e a lista 'options' para o estilo de cada camada
        res = qta.icon(
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
        return res if isinstance(res, QIcon) else QIcon(res)


def configurar_tema_claro_aplicacao(app: Optional[Any] = None) -> None:
    """
    Configura a aplicação Qt para operar estritamente sob o esquema de cores claro (Light Mode).
    Previne que o modo escuro do sistema operacional corrompa o contraste da interface gráfica
    e garante que o QToolTip renderize com cores claras e legíveis.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPalette, QColor

    instancia = app or QApplication.instance()
    if not isinstance(instancia, QApplication):
        return

    try:
        if hasattr(instancia, "styleHints") and hasattr(instancia.styleHints(), "setColorScheme"):
            instancia.styleHints().setColorScheme(Qt.ColorScheme.Light)
    except Exception:
        pass

    try:
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#212529"))
        instancia.setPalette(pal)
    except Exception:
        pass

    folha_atual = instancia.styleSheet() or ""
    if "QToolTip" not in folha_atual:
        nova_folha = (folha_atual + "\n" + Icones.QSS_TOOLTIP).strip()
        instancia.setStyleSheet(nova_folha)
