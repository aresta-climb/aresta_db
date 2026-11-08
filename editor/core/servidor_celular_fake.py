# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from io import BytesIO
from pathlib import Path

import qrcode
from PySide6.QtCore import QObject, Signal


class ServidorCelularFake(QObject):
    """
    Dublê determinístico em memória para ServidorCelular (test-only).
    Evita sondagem de IP via socket para 8.8.8.8:80 e conexões com previa.arestaclimb.com.
    """

    dispositivo_conectado = Signal()

    def __init__(
        self,
        pasta_compilado: Path | str,
        codigo_sessao: str | None = None,
        url_retransmissor_ws: str | None = None,
        jwt_token: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.pasta_compilado: Path = Path(pasta_compilado)
        self.codigo_sessao: str = codigo_sessao or "abcd2345"
        self.url_retransmissor_ws: str | None = url_retransmissor_ws
        self.jwt_token: str | None = jwt_token
        self.porta: int | None = None
        self._servindo: bool = False
        self.conectado: bool = False
        self.recarregamentos_emitidos: list[str] = []

    def solicitar_sessao_servidor(self, url_base: str = "") -> bool:
        """Simula criação instantânea de sessão local sem chamadas HTTP externas."""
        _ = url_base
        return True

    def obter_ip_local(self) -> str:
        """Retorna endereço de loopback sem abrir socket externo."""
        return "127.0.0.1"

    def obter_url_previa_canonica(self) -> str:
        """Retorna URL local determinística para exibição no diálogo."""
        porta_efetiva = self.porta or 8765
        return f"http://127.0.0.1:{porta_efetiva}/{self.codigo_sessao}"

    def gerar_qr_code(self, conteudo: str) -> bytes:
        """Gera imagem PNG de QR Code válida em memória."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(conteudo)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, "PNG")
        return bytes(buffer.getvalue())

    def iniciar(self) -> None:
        """Simula inicialização instantânea na porta local 8765."""
        self._servindo = True
        self.porta = 8765

    def simular_conexao_dispositivo(self) -> None:
        """Marca o servidor como conectado e emite dispositivo_conectado."""
        self.conectado = True
        self.dispositivo_conectado.emit()

    def emitir_recarregamento(self, setor_id: str) -> None:
        """Registra o evento de live-reload em memória."""
        self.recarregamentos_emitidos.append(setor_id)

    def parar(self) -> None:
        """Encerra o estado simulado do servidor."""
        self._servindo = False
        self.conectado = False
