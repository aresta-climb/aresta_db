# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para a mensagem Coordenada (MensagemFormatoUi.COORDENADA).
Exibe na primeira linha os botões de ação ('Colar' e 'Abrir no Maps') unificados para a mensagem,
e na segunda linha os campos de Latitude e Longitude na mesma linha horizontal.
"""

from typing import Optional
from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QDialog,
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
from editor.views.widget_campo_coordenada_e7 import DialogoConfirmarCoordenadas


class WidgetMensagemCoordenada(QWidget):
    """
    Widget para edição integrada da mensagem Coordenada.
    Linha 1: Botões 'Colar' e 'Abrir no Maps'.
    Linha 2: 'Latitude:' [Input] [Card] | 'Longitude:' [Input] [Card].
    """
    sinal_coordenadas_alteradas = pyqtSignal(object, object)  # (lat_e7, lon_e7)

    def __init__(self, msg, controller=None, model=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.msg = msg
        self.controller = controller
        self.model = model

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Linha 1: Ações unificadas
        linha_acoes = QHBoxLayout()
        linha_acoes.setSpacing(8)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setToolTip("Colar coordenada ou par (latitude, longitude) da área de transferência")
        self.btn_colar.clicked.connect(self._ao_clicar_colar)

        self.btn_maps = QPushButton("Abrir no Maps")
        self.btn_maps.setToolTip("Abrir localização no Google Maps")
        self.btn_maps.clicked.connect(self.abrir_no_google_maps)

        linha_acoes.addWidget(self.btn_colar)
        linha_acoes.addWidget(self.btn_maps)
        linha_acoes.addStretch()

        # Linha 2: Inputs de Latitude e Longitude na mesma linha
        linha_campos = QHBoxLayout()
        linha_campos.setSpacing(8)

        lbl_lat = QLabel("Latitude:")
        self.edit_lat = QLineEdit()
        self.edit_lat.setPlaceholderText("Opcional")
        self.edit_lat.setMaximumWidth(130)

        self.rotulo_cardinal_lat = QLabel()
        self.rotulo_cardinal_lat.setMinimumWidth(65)

        lbl_lon = QLabel("Longitude:")
        self.edit_lon = QLineEdit()
        self.edit_lon.setPlaceholderText("Opcional")
        self.edit_lon.setMaximumWidth(130)

        self.rotulo_cardinal_lon = QLabel()
        self.rotulo_cardinal_lon.setMinimumWidth(65)

        linha_campos.addWidget(lbl_lat)
        linha_campos.addWidget(self.edit_lat)
        linha_campos.addWidget(self.rotulo_cardinal_lat)
        linha_campos.addSpacing(12)
        linha_campos.addWidget(lbl_lon)
        linha_campos.addWidget(self.edit_lon)
        linha_campos.addWidget(self.rotulo_cardinal_lon)
        linha_campos.addStretch()

        layout.addLayout(linha_acoes)
        layout.addLayout(linha_campos)

        self.edit_lat.textChanged.connect(self._ao_alterar_texto_lat)
        self.edit_lat.editingFinished.connect(self._confirmar_edicao_lat)

        self.edit_lon.textChanged.connect(self._ao_alterar_texto_lon)
        self.edit_lon.editingFinished.connect(self._confirmar_edicao_lon)

        if self.model and hasattr(self.model, "dado_alterado"):
            self.model.dado_alterado.connect(self._on_model_dado_alterado)

        self._carregar_da_mensagem()

    def _on_model_dado_alterado(self, msg, campo_nome):
        from editor.models.readonly_proxy import ReadOnlyProxy
        unwrapped_msg = object.__getattribute__(self.msg, "_obj") if isinstance(self.msg, ReadOnlyProxy) else self.msg
        unwrapped_target = object.__getattribute__(msg, "_obj") if isinstance(msg, ReadOnlyProxy) else msg
        if unwrapped_msg is unwrapped_target or self.msg == msg:
            if campo_nome in ("latitude", "longitude"):
                self._carregar_da_mensagem()

    def _obter_has_field(self, msg, field_name: str) -> bool:
        if hasattr(msg, "HasField"):
            return msg.HasField(field_name)
        return getattr(msg, field_name, None) is not None

    def _carregar_da_mensagem(self):
        lat = getattr(self.msg, "latitude", None) if self._obter_has_field(self.msg, "latitude") else None
        lon = getattr(self.msg, "longitude", None) if self._obter_has_field(self.msg, "longitude") else None
        self.definir_valores(lat, lon)

    def definir_valores(self, lat_e7: Optional[int], lon_e7: Optional[int]):
        self.edit_lat.blockSignals(True)
        self.edit_lon.blockSignals(True)

        if lat_e7 is None:
            self.edit_lat.setText("")
            self.rotulo_cardinal_lat.setText("")
        else:
            graus_lat = e7_para_graus(lat_e7)
            self.edit_lat.setText("0" if graus_lat == 0.0 else f"{graus_lat:.7f}".rstrip("0").rstrip("."))
            self._atualizar_rotulo_lat(graus_lat)

        if lon_e7 is None:
            self.edit_lon.setText("")
            self.rotulo_cardinal_lon.setText("")
        else:
            graus_lon = e7_para_graus(lon_e7)
            self.edit_lon.setText("0" if graus_lon == 0.0 else f"{graus_lon:.7f}".rstrip("0").rstrip("."))
            self._atualizar_rotulo_lon(graus_lon)

        self.btn_maps.setEnabled(lat_e7 is not None or lon_e7 is not None)

        self.edit_lat.blockSignals(False)
        self.edit_lon.blockSignals(False)

    def obter_latitude_e7(self) -> Optional[int]:
        txt = self.edit_lat.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            val = float(txt)
            return graus_para_e7(val) if validar_latitude(val) else None
        except ValueError:
            return None

    def obter_longitude_e7(self) -> Optional[int]:
        txt = self.edit_lon.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            val = float(txt)
            return graus_para_e7(val) if validar_longitude(val) else None
        except ValueError:
            return None

    def obter_latitude_graus(self) -> Optional[float]:
        e7 = self.obter_latitude_e7()
        return e7_para_graus(e7) if e7 is not None else None

    def obter_longitude_graus(self) -> Optional[float]:
        e7 = self.obter_longitude_e7()
        return e7_para_graus(e7) if e7 is not None else None

    def _ao_alterar_texto_lat(self, texto: str):
        txt = texto.strip().replace(",", ".")
        if not txt:
            self.rotulo_cardinal_lat.setText("")
            self._atualizar_estado_maps()
            return
        try:
            val = float(txt)
            if validar_latitude(val):
                self._atualizar_rotulo_lat(val)
                self._atualizar_estado_maps()
            else:
                self.rotulo_cardinal_lat.setText("Inválido")
                self._atualizar_estado_maps()
        except ValueError:
            self.rotulo_cardinal_lat.setText("Inválido")
            self._atualizar_estado_maps()

    def _ao_alterar_texto_lon(self, texto: str):
        txt = texto.strip().replace(",", ".")
        if not txt:
            self.rotulo_cardinal_lon.setText("")
            self._atualizar_estado_maps()
            return
        try:
            val = float(txt)
            if validar_longitude(val):
                self._atualizar_rotulo_lon(val)
                self._atualizar_estado_maps()
            else:
                self.rotulo_cardinal_lon.setText("Inválido")
                self._atualizar_estado_maps()
        except ValueError:
            self.rotulo_cardinal_lon.setText("Inválido")
            self._atualizar_estado_maps()

    def _atualizar_rotulo_lat(self, val: float):
        sigla, nome = obter_indicador_cardinal_latitude(val)
        self.rotulo_cardinal_lat.setText(nome if not sigla else f"{sigla} ({nome})")

    def _atualizar_rotulo_lon(self, val: float):
        sigla, nome = obter_indicador_cardinal_longitude(val)
        self.rotulo_cardinal_lon.setText(nome if not sigla else f"{sigla} ({nome})")

    def _atualizar_estado_maps(self):
        lat = self.obter_latitude_e7()
        lon = self.obter_longitude_e7()
        self.btn_maps.setEnabled(lat is not None or lon is not None)

    def _confirmar_edicao_lat(self):
        lat_novo = self.obter_latitude_e7()
        lat_antigo = getattr(self.msg, "latitude", None) if self._obter_has_field(self.msg, "latitude") else None
        if lat_novo != lat_antigo:
            if self.controller:
                self.controller.alterar_primitivo(self.msg, "latitude", lat_antigo, lat_novo)
            else:
                if lat_novo is None:
                    if hasattr(self.msg, "ClearField"):
                        self.msg.ClearField("latitude")
                else:
                    self.msg.latitude = lat_novo
            self.sinal_coordenadas_alteradas.emit(lat_novo, self.obter_longitude_e7())

    def _confirmar_edicao_lon(self):
        lon_novo = self.obter_longitude_e7()
        lon_antigo = getattr(self.msg, "longitude", None) if self._obter_has_field(self.msg, "longitude") else None
        if lon_novo != lon_antigo:
            if self.controller:
                self.controller.alterar_primitivo(self.msg, "longitude", lon_antigo, lon_novo)
            else:
                if lon_novo is None:
                    if hasattr(self.msg, "ClearField"):
                        self.msg.ClearField("longitude")
                else:
                    self.msg.longitude = lon_novo
            self.sinal_coordenadas_alteradas.emit(self.obter_latitude_e7(), lon_novo)

    def _ao_clicar_colar(self):
        clipboard = QApplication.clipboard()
        texto = clipboard.text() if clipboard else ""
        if texto:
            self.processar_texto_colado(texto)

    def processar_texto_colado(self, texto: str) -> bool:
        par = interpretar_par_coordenadas(texto)
        if par:
            lat, lon = par
            dialogo = DialogoConfirmarCoordenadas(lat, lon, parent=self)
            if dialogo.exec() == QDialog.DialogCode.Accepted:
                lat_final = dialogo.obter_latitude()
                lon_final = dialogo.obter_longitude()
                lat_e7 = graus_para_e7(lat_final)
                lon_e7 = graus_para_e7(lon_final)

                lat_antigo = getattr(self.msg, "latitude", None) if self._obter_has_field(self.msg, "latitude") else None
                lon_antigo = getattr(self.msg, "longitude", None) if self._obter_has_field(self.msg, "longitude") else None

                self.definir_valores(lat_e7, lon_e7)

                if self.controller:
                    if lat_antigo != lat_e7:
                        self.controller.alterar_primitivo(self.msg, "latitude", lat_antigo, lat_e7)
                    if lon_antigo != lon_e7:
                        self.controller.alterar_primitivo(self.msg, "longitude", lon_antigo, lon_e7)
                else:
                    self.msg.latitude = lat_e7
                    self.msg.longitude = lon_e7

                self.sinal_coordenadas_alteradas.emit(lat_e7, lon_e7)
                return True
            return False

        individual = interpretar_coordenada_individual(texto)
        if individual is not None:
            txt_upper = texto.upper()
            is_lon_cardinal = any(c in txt_upper for c in ("W", "O", "E", "L", "OESTE", "LESTE"))
            is_lat_cardinal = any(c in txt_upper for c in ("N", "S", "NORTE", "SUL"))
            tem_foco_lon = self.edit_lon.hasFocus() or (QApplication.focusWidget() == self.edit_lon)

            if is_lon_cardinal and validar_longitude(individual):
                self.edit_lon.setText(str(individual))
                self._confirmar_edicao_lon()
                return True
            elif is_lat_cardinal and validar_latitude(individual):
                self.edit_lat.setText(str(individual))
                self._confirmar_edicao_lat()
                return True
            elif tem_foco_lon and validar_longitude(individual):
                self.edit_lon.setText(str(individual))
                self._confirmar_edicao_lon()
                return True
            elif abs(individual) > 90.0 and validar_longitude(individual):
                self.edit_lon.setText(str(individual))
                self._confirmar_edicao_lon()
                return True
            elif validar_latitude(individual):
                self.edit_lat.setText(str(individual))
                self._confirmar_edicao_lat()
                return True

        return False

    def abrir_no_google_maps(self):
        lat = self.obter_latitude_graus()
        lon = self.obter_longitude_graus()
        if lat is None and lon is None:
            return
        url = gerar_url_google_maps(lat or 0.0, lon or 0.0)
        QDesktopServices.openUrl(QUrl(url))
