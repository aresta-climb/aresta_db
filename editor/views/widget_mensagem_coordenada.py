# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Componente visual especializado para a mensagem Coordenada (MensagemFormatoUi.COORDENADA).
Exibe na primeira linha os botões de ação ('Colar', 'Abrir no Maps' e, em Pico.localizacao,
'Gerar Mapa de Pontos') unificados para a mensagem, e na segunda linha os campos de
Latitude e Longitude na mesma linha horizontal.
"""

from typing import Any

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.coordenadas import (
    e7_para_graus,
    gerar_url_google_maps,
    graus_para_e7,
    interpretar_coordenada_individual,
    interpretar_par_coordenadas,
    obter_indicador_cardinal_latitude,
    obter_indicador_cardinal_longitude,
    validar_latitude,
    validar_longitude,
)
from editor.views.widget_campo_coordenada_e7 import DialogoConfirmarCoordenadas


class WidgetMensagemCoordenada(QWidget):
    """
    Widget para edição integrada da mensagem Coordenada.
    Linha 1: Botões 'Colar', 'Abrir no Maps' (e 'Gerar Mapa de Pontos' em Pico.localizacao).
    Linha 2: 'Latitude:' [Input] [Card] | 'Longitude:' [Input] [Card].
    Linha 3 (apenas Pico.localizacao): Indicador de status / warning da malha rodoviária OSM.
    """

    sinal_coordenadas_alteradas = Signal(object, object)  # (lat_e7, lon_e7)

    def __init__(
        self,
        msg: Any,
        controller: Any | None = None,
        model: Any | None = None,
        parent: QWidget | None = None,
        msg_pai: Any | None = None,
        campo_pai: str | None = None,
        cliente_overpass: Any | None = None,
    ) -> None:
        super().__init__(parent)
        self.msg: Any = msg
        self.msg_pai: Any = msg_pai
        self.campo_pai: str | None = campo_pai
        self.controller: Any | None = controller
        self.model: Any | None = model
        self.cliente_overpass: Any | None = cliente_overpass
        self.btn_gerar_malha: QPushButton | None = None
        self.rotulo_status_malha: QLabel | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Linha 1: Ações unificadas
        linha_acoes = QHBoxLayout()
        linha_acoes.setSpacing(8)

        self.btn_colar = QPushButton("Colar")
        self.btn_colar.setToolTip(
            "Colar coordenada ou par (latitude, longitude) da área de transferência"
        )
        self.btn_colar.clicked.connect(self._ao_clicar_colar)

        self.btn_maps = QPushButton("Abrir no Maps")
        self.btn_maps.setToolTip("Abrir localização no Google Maps")
        self.btn_maps.clicked.connect(self.abrir_no_google_maps)

        linha_acoes.addWidget(self.btn_colar)
        linha_acoes.addWidget(self.btn_maps)

        if self._eh_localizacao_pico():
            self.btn_gerar_malha = QPushButton("Gerar Mapa de Pontos")
            self.btn_gerar_malha.setToolTip(
                "Consultar OpenStreetMap e pré-computar o mapa de pontos de estrada para esta localização"
            )
            self.btn_gerar_malha.clicked.connect(self.gerar_malha_pontos_estrada)
            linha_acoes.addWidget(self.btn_gerar_malha)

            self.rotulo_status_malha = QLabel()
            self.rotulo_status_malha.setWordWrap(True)

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
        if self.rotulo_status_malha is not None:
            layout.addWidget(self.rotulo_status_malha)

        self.edit_lat.textChanged.connect(self._ao_alterar_texto_lat)
        self.edit_lat.editingFinished.connect(self._confirmar_edicao_lat)

        self.edit_lon.textChanged.connect(self._ao_alterar_texto_lon)
        self.edit_lon.editingFinished.connect(self._confirmar_edicao_lon)

        if self.model and hasattr(self.model, "dado_alterado"):
            self.model.dado_alterado.connect(self._on_model_dado_alterado)

        self._carregar_da_mensagem()

    def _eh_localizacao_pico(self) -> bool:
        return (
            self.msg_pai is not None
            and self.campo_pai == "localizacao"
            and getattr(getattr(self.msg_pai, "DESCRIPTOR", None), "name", None) == "Pico"
        )

    def _resolver_msg_atual(self) -> Any:
        if self.msg_pai is not None and self.campo_pai:
            self.msg = getattr(self.msg_pai, self.campo_pai)
        return self.msg

    def _on_model_dado_alterado(self, msg: Any, campo_nome: str) -> None:
        from editor.models.readonly_proxy import ReadOnlyProxy

        if campo_nome == "malha_estrada":
            self._atualizar_status_malha_pico()
            return

        msg_atual = self._resolver_msg_atual()
        unwrapped_msg = (
            object.__getattribute__(msg_atual, "_obj")
            if isinstance(msg_atual, ReadOnlyProxy)
            else msg_atual
        )
        unwrapped_target = (
            object.__getattribute__(msg, "_obj") if isinstance(msg, ReadOnlyProxy) else msg
        )
        if unwrapped_msg is unwrapped_target or msg_atual == msg:
            if campo_nome in ("latitude", "longitude"):
                self._carregar_da_mensagem()

    def _obter_has_field(self, msg: Any, field_name: str) -> bool:
        if hasattr(msg, "HasField"):
            return bool(msg.HasField(field_name))
        return getattr(msg, field_name, None) is not None

    def _carregar_da_mensagem(self) -> None:
        msg = self._resolver_msg_atual()
        lat = getattr(msg, "latitude", None) if self._obter_has_field(msg, "latitude") else None
        lon = getattr(msg, "longitude", None) if self._obter_has_field(msg, "longitude") else None
        self.definir_valores(lat, lon)

    def definir_valores(self, lat_e7: int | None, lon_e7: int | None) -> None:
        self.edit_lat.blockSignals(True)
        self.edit_lon.blockSignals(True)

        if lat_e7 is None:
            self.edit_lat.setText("")
            self.rotulo_cardinal_lat.setText("")
        else:
            graus_lat = e7_para_graus(lat_e7)
            self.edit_lat.setText(
                "0" if graus_lat == 0.0 else f"{graus_lat:.7f}".rstrip("0").rstrip(".")
            )
            self._atualizar_rotulo_lat(graus_lat)

        if lon_e7 is None:
            self.edit_lon.setText("")
            self.rotulo_cardinal_lon.setText("")
        else:
            graus_lon = e7_para_graus(lon_e7)
            self.edit_lon.setText(
                "0" if graus_lon == 0.0 else f"{graus_lon:.7f}".rstrip("0").rstrip(".")
            )
            self._atualizar_rotulo_lon(graus_lon)

        self.btn_maps.setEnabled(lat_e7 is not None or lon_e7 is not None)

        self.edit_lat.blockSignals(False)
        self.edit_lon.blockSignals(False)
        self._atualizar_status_malha_pico()

    def obter_latitude_e7(self) -> int | None:
        txt = self.edit_lat.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            val = float(txt)
            return graus_para_e7(val) if validar_latitude(val) else None
        except ValueError:
            return None

    def obter_longitude_e7(self) -> int | None:
        txt = self.edit_lon.text().strip().replace(",", ".")
        if not txt:
            return None
        try:
            val = float(txt)
            return graus_para_e7(val) if validar_longitude(val) else None
        except ValueError:
            return None

    def obter_latitude_graus(self) -> float | None:
        e7 = self.obter_latitude_e7()
        return e7_para_graus(e7) if e7 is not None else None

    def obter_longitude_graus(self) -> float | None:
        e7 = self.obter_longitude_e7()
        return e7_para_graus(e7) if e7 is not None else None

    def _ao_alterar_texto_lat(self, texto: str) -> None:
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

    def _ao_alterar_texto_lon(self, texto: str) -> None:
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

    def _atualizar_rotulo_lat(self, val: float) -> None:
        sigla, nome = obter_indicador_cardinal_latitude(val)
        self.rotulo_cardinal_lat.setText(nome if not sigla else f"{sigla} ({nome})")

    def _atualizar_rotulo_lon(self, val: float) -> None:
        sigla, nome = obter_indicador_cardinal_longitude(val)
        self.rotulo_cardinal_lon.setText(nome if not sigla else f"{sigla} ({nome})")

    def _atualizar_estado_maps(self) -> None:
        lat = self.obter_latitude_e7()
        lon = self.obter_longitude_e7()
        self.btn_maps.setEnabled(lat is not None or lon is not None)
        self._atualizar_status_malha_pico()

    def _atualizar_status_malha_pico(self) -> None:
        if self.btn_gerar_malha is None or self.rotulo_status_malha is None:
            return

        lat_e7 = self.obter_latitude_e7()
        lon_e7 = self.obter_longitude_e7()
        coordenadas_validas = (
            lat_e7 is not None and lon_e7 is not None and (lat_e7 != 0 or lon_e7 != 0)
        )
        self.btn_gerar_malha.setEnabled(coordenadas_validas)
        if not coordenadas_validas:
            self.rotulo_status_malha.setText("")
            self.rotulo_status_malha.setVisible(False)
            return

        from scripts.gerar_malha_estrada_lib import malha_estrada_pico_atualizada

        if (
            malha_estrada_pico_atualizada(self.msg_pai)
            and self.msg_pai.malha_estrada.latitude_referencia_e7 == lat_e7
            and self.msg_pai.malha_estrada.longitude_referencia_e7 == lon_e7
        ):
            qtd_nos = len(self.msg_pai.malha_estrada.nos)
            self.rotulo_status_malha.setText(
                f"✅ Mapa de pontos de estrada gerado ({qtd_nos} nós)."
            )
            self.rotulo_status_malha.setStyleSheet("color: #2e7d32; font-size: 11px;")
        else:
            self.rotulo_status_malha.setText(
                "⚠️ Mapa de pontos de estrada não gerado para esta localização."
            )
            self.rotulo_status_malha.setStyleSheet(
                "color: #ef6c00; font-size: 11px; font-weight: bold;"
            )
        self.rotulo_status_malha.setVisible(True)

    def gerar_malha_pontos_estrada(self) -> bool:
        """Consulta a Overpass API e persiste os nós da malha rodoviária em Pico.malha_estrada."""
        lat_e7 = self.obter_latitude_e7()
        lon_e7 = self.obter_longitude_e7()
        if not self._eh_localizacao_pico() or lat_e7 is None or lon_e7 is None:
            return False

        from scripts.gerar_malha_estrada_lib import (
            ClienteOverpass,
            construir_malha_estrada_pico_proto,
        )

        cliente = self.cliente_overpass if self.cliente_overpass is not None else ClienteOverpass()
        try:
            nova_malha = construir_malha_estrada_pico_proto(lat_e7, lon_e7, cliente)
        except Exception:
            self._atualizar_status_malha_pico()
            return False

        if self.controller is not None:
            self.controller.alterar_campo(self.msg_pai, "malha_estrada", nova_malha)
        else:
            self.msg_pai.malha_estrada.CopyFrom(nova_malha)

        self._atualizar_status_malha_pico()
        return True

    def _sincronizar_malha_apos_edicao_pico(self) -> None:
        if not self._eh_localizacao_pico():
            return
        if (
            self.cliente_overpass is not None
            and self.obter_latitude_e7() is not None
            and self.obter_longitude_e7() is not None
        ):
            self.gerar_malha_pontos_estrada()
        else:
            self._atualizar_status_malha_pico()

    def _confirmar_edicao_lat(self) -> None:
        msg = self._resolver_msg_atual()
        lat_novo = self.obter_latitude_e7()
        lat_antigo = (
            getattr(msg, "latitude", None) if self._obter_has_field(msg, "latitude") else None
        )
        if lat_novo != lat_antigo:
            if self.controller:
                self.controller.alterar_primitivo(
                    msg, "latitude", lat_antigo, lat_novo, pode_mesclar=True
                )
            else:
                if lat_novo is None:
                    if hasattr(msg, "ClearField"):
                        msg.ClearField("latitude")
                else:
                    msg.latitude = lat_novo
            self.sinal_coordenadas_alteradas.emit(lat_novo, self.obter_longitude_e7())
            self._sincronizar_malha_apos_edicao_pico()

    def _confirmar_edicao_lon(self) -> None:
        msg = self._resolver_msg_atual()
        lon_novo = self.obter_longitude_e7()
        lon_antigo = (
            getattr(msg, "longitude", None) if self._obter_has_field(msg, "longitude") else None
        )
        if lon_novo != lon_antigo:
            if self.controller:
                self.controller.alterar_primitivo(
                    msg, "longitude", lon_antigo, lon_novo, pode_mesclar=True
                )
            else:
                if lon_novo is None:
                    if hasattr(msg, "ClearField"):
                        msg.ClearField("longitude")
                else:
                    msg.longitude = lon_novo
            self.sinal_coordenadas_alteradas.emit(self.obter_latitude_e7(), lon_novo)
            self._sincronizar_malha_apos_edicao_pico()

    def _ao_clicar_colar(self) -> None:
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
                msg = self._resolver_msg_atual()
                lat_final = dialogo.obter_latitude()
                lon_final = dialogo.obter_longitude()
                lat_e7 = graus_para_e7(lat_final)
                lon_e7 = graus_para_e7(lon_final)

                lat_antigo = (
                    getattr(msg, "latitude", None)
                    if self._obter_has_field(msg, "latitude")
                    else None
                )
                lon_antigo = (
                    getattr(msg, "longitude", None)
                    if self._obter_has_field(msg, "longitude")
                    else None
                )

                self.definir_valores(lat_e7, lon_e7)

                if self.controller:
                    if lat_antigo != lat_e7:
                        self.controller.alterar_primitivo(msg, "latitude", lat_antigo, lat_e7)
                    if lon_antigo != lon_e7:
                        self.controller.alterar_primitivo(msg, "longitude", lon_antigo, lon_e7)
                else:
                    msg.latitude = lat_e7
                    msg.longitude = lon_e7

                self.sinal_coordenadas_alteradas.emit(lat_e7, lon_e7)
                self._sincronizar_malha_apos_edicao_pico()
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

    def abrir_no_google_maps(self) -> None:
        lat = self.obter_latitude_graus()
        lon = self.obter_longitude_graus()
        if lat is None and lon is None:
            return
        url = gerar_url_google_maps(lat or 0.0, lon or 0.0)
        QDesktopServices.openUrl(QUrl(url))
