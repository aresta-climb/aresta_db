# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para exibição e edição de coordenadas geográficas
no formato E7 no editor do Aresta.
Utiliza campo de texto simples (QLineEdit) sem botões de incremento (spinbox)
e com suporte a estado nulo/vazio (onde 0 é uma coordenada válida).
"""

from enum import Enum
from typing import Optional, Callable
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialog,
    QDialogButtonBox,
    QApplication,
)

from editor.core.coordenadas import (
    graus_para_e7,
    e7_para_graus,
    obter_indicador_cardinal_latitude,
    obter_indicador_cardinal_longitude,
    validar_latitude,
    validar_longitude,
    gerar_url_google_maps,
    interpretar_coordenada_individual,
    interpretar_par_coordenadas,
)


class TipoCoordenada(Enum):
    LATITUDE = "latitude"
    LONGITUDE = "longitude"


class DialogoConfirmarCoordenadas(QDialog):
    """
    Diálogo para confirmação de par de coordenadas detectado via colagem inteligente.
    Permite visualizar a interpretação e inverter os eixos (Latitude <-> Longitude).
    """
    def __init__(self, latitude: float, longitude: float, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Coordenadas Coladas")
        self.setModal(True)
        self._lat = latitude
        self._lon = longitude

        layout = QVBoxLayout(self)

        info_label = QLabel("Foram detectadas as seguintes coordenadas. Verifique e confirme:")
        layout.addWidget(info_label)

        campos_layout = QHBoxLayout()
        self.edit_lat = QLineEdit()
        self.edit_lat.setText(self._formatar_graus(self._lat))

        self.edit_lon = QLineEdit()
        self.edit_lon.setText(self._formatar_graus(self._lon))

        col_lat = QVBoxLayout()
        col_lat.addWidget(QLabel("Latitude:"))
        col_lat.addWidget(self.edit_lat)

        col_lon = QVBoxLayout()
        col_lon.addWidget(QLabel("Longitude:"))
        col_lon.addWidget(self.edit_lon)

        self.btn_inverter = QPushButton("⇄ Inverter")
        self.btn_inverter.setToolTip("Inverter Latitude e Longitude")
        self.btn_inverter.clicked.connect(self.inverter_eixos)

        campos_layout.addLayout(col_lat)
        campos_layout.addWidget(self.btn_inverter)
        campos_layout.addLayout(col_lon)
        layout.addLayout(campos_layout)

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    @staticmethod
    def _formatar_graus(graus: float) -> str:
        return "0" if graus == 0.0 else f"{graus:.7f}".rstrip("0").rstrip(".")

    def inverter_eixos(self):
        lat_texto = self.edit_lat.text()
        lon_texto = self.edit_lon.text()
        self.edit_lat.setText(lon_texto)
        self.edit_lon.setText(lat_texto)

    def obter_latitude(self) -> float:
        try:
            return float(self.edit_lat.text().replace(",", "."))
        except ValueError:
            return self._lat

    def obter_longitude(self) -> float:
        try:
            return float(self.edit_lon.text().replace(",", "."))
        except ValueError:
            return self._lon


class WidgetCampoCoordenadaE7(QWidget):
    """
    Widget de edição de coordenadas geográficas em formato E7.
    Usa QLineEdit direto (sem setas de spinbox) e trata campo vazio como None,
    sendo 0 um valor numérico válido (Equador / Meridiano de Greenwich).
    """
    valor_alterado_e7 = Signal(object)  # Optional[int]

    def __init__(
        self,
        tipo: TipoCoordenada = TipoCoordenada.LATITUDE,
        valor_e7: Optional[int] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.tipo = tipo
        self._valor_e7: Optional[int] = None
        self._coord_contexto_e7: Optional[int] = None
        self.ao_receber_par_coordenadas: Optional[Callable[[int, int], None]] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.edit_texto = QLineEdit()
        self.edit_texto.setPlaceholderText("Opcional")
        self.edit_texto.setMaximumWidth(150)

        self.rotulo_cardinal = QLabel()
        self.rotulo_cardinal.setMinimumWidth(80)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setToolTip("Colar coordenada ou par (latitude, longitude) da área de transferência")
        self.btn_colar.clicked.connect(self._ao_clicar_colar)

        self.btn_maps = QPushButton("Abrir no Maps")
        self.btn_maps.setToolTip("Abrir ponto no Google Maps")
        self.btn_maps.clicked.connect(self.abrir_no_google_maps)

        layout.addWidget(self.edit_texto, stretch=1)
        layout.addWidget(self.rotulo_cardinal)
        layout.addWidget(self.btn_colar)
        layout.addWidget(self.btn_maps)

        self.edit_texto.textChanged.connect(self._ao_alterar_texto)
        self.edit_texto.editingFinished.connect(self.confirmar_edicao)

        self.definir_valor_e7(valor_e7)

    def definir_longitude_contexto(self, lon_e7: Optional[int]):
        """Define a coordenada parceira (ex: longitude para latitude) para abrir no Google Maps."""
        self._coord_contexto_e7 = lon_e7

    def definir_latitude_contexto(self, lat_e7: Optional[int]):
        """Define a coordenada parceira (ex: latitude para longitude) para abrir no Google Maps."""
        self._coord_contexto_e7 = lat_e7

    def obter_valor_graus(self) -> Optional[float]:
        if self._valor_e7 is None:
            return None
        return e7_para_graus(self._valor_e7)

    def obter_valor_e7(self) -> Optional[int]:
        return self._valor_e7

    def definir_valor_graus(self, graus: Optional[float]):
        if graus is None:
            self.definir_valor_e7(None)
        else:
            self.definir_valor_e7(graus_para_e7(graus))

    def definir_valor_e7(self, valor_e7: Optional[int]):
        self._valor_e7 = valor_e7
        self.edit_texto.blockSignals(True)
        if valor_e7 is None:
            self.edit_texto.setText("")
            self.rotulo_cardinal.setText("")
            self.btn_maps.setEnabled(False)
        else:
            graus = e7_para_graus(valor_e7)
            texto_fmt = "0" if graus == 0.0 else f"{graus:.7f}".rstrip("0").rstrip(".")
            self.edit_texto.setText(texto_fmt)
            self._atualizar_rotulo_cardinal(graus)
            self.btn_maps.setEnabled(True)
        self.edit_texto.blockSignals(False)

    def _ao_alterar_texto(self, texto: str):
        txt = texto.strip().replace(",", ".")
        if not txt:
            self._valor_e7 = None
            self.rotulo_cardinal.setText("")
            self.btn_maps.setEnabled(False)
            return

        try:
            val = float(txt)
            valido = validar_latitude(val) if self.tipo == TipoCoordenada.LATITUDE else validar_longitude(val)
            if valido:
                self._valor_e7 = graus_para_e7(val)
                self._atualizar_rotulo_cardinal(val)
                self.btn_maps.setEnabled(True)
            else:
                self._valor_e7 = None
                self.rotulo_cardinal.setText("Inválido")
                self.btn_maps.setEnabled(False)
        except ValueError:
            self._valor_e7 = None
            self.rotulo_cardinal.setText("Inválido")
            self.btn_maps.setEnabled(False)

    def _atualizar_rotulo_cardinal(self, valor_graus: float):
        if self.tipo == TipoCoordenada.LATITUDE:
            sigla, nome = obter_indicador_cardinal_latitude(valor_graus)
        else:
            sigla, nome = obter_indicador_cardinal_longitude(valor_graus)

        if not sigla:
            self.rotulo_cardinal.setText(nome)
        else:
            self.rotulo_cardinal.setText(f"{sigla} ({nome})")

    def confirmar_edicao(self):
        self.valor_alterado_e7.emit(self._valor_e7)

    def _ao_clicar_colar(self):
        clipboard = QApplication.clipboard()
        texto = clipboard.text() if clipboard else ""
        if texto:
            self.processar_texto_colado(texto)

    def processar_texto_colado(self, texto: str) -> bool:
        """Processa texto colado, suportando tanto valor individual quanto par (Lat, Lon)."""
        par = interpretar_par_coordenadas(texto)
        if par:
            lat, lon = par
            dialogo = DialogoConfirmarCoordenadas(lat, lon, parent=self)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                lat_final = dialogo.obter_latitude()
                lon_final = dialogo.obter_longitude()
                lat_e7 = graus_para_e7(lat_final)
                lon_e7 = graus_para_e7(lon_final)
                if self.tipo == TipoCoordenada.LATITUDE:
                    self.definir_valor_e7(lat_e7)
                    self.confirmar_edicao()
                else:
                    self.definir_valor_e7(lon_e7)
                    self.confirmar_edicao()

                if self.ao_receber_par_coordenadas:
                    self.ao_receber_par_coordenadas(lat_e7, lon_e7)
                return True
            return False

        individual = interpretar_coordenada_individual(texto)
        if individual is not None:
            if self.tipo == TipoCoordenada.LATITUDE and validar_latitude(individual):
                self.definir_valor_graus(individual)
                self.confirmar_edicao()
                return True
            elif self.tipo == TipoCoordenada.LONGITUDE and validar_longitude(individual):
                self.definir_valor_graus(individual)
                self.confirmar_edicao()
                return True

        return False

    def abrir_no_google_maps(self):
        if self._valor_e7 is None:
            return
        lat = (
            e7_para_graus(self._valor_e7)
            if self.tipo == TipoCoordenada.LATITUDE
            else (
                e7_para_graus(self._coord_contexto_e7)
                if self._coord_contexto_e7 is not None
                else 0.0
            )
        )
        lon = (
            e7_para_graus(self._valor_e7)
            if self.tipo == TipoCoordenada.LONGITUDE
            else (
                e7_para_graus(self._coord_contexto_e7)
                if self._coord_contexto_e7 is not None
                else 0.0
            )
        )
        url = gerar_url_google_maps(lat, lon)
        QDesktopServices.openUrl(QUrl(url))
