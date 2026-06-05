from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QEvent

class MonitorInatividade(QObject):
    """Monitora a inatividade do usuário através de eventos de input do Qt."""
    inatividade_detectada = pyqtSignal()
    
    def __init__(self, timeout_ms=10000, parent=None):
        super().__init__(parent)
        self.timeout_ms = timeout_ms
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._ao_estourar_tempo)
        
    def iniciar(self):
        """Inicia o monitoramento."""
        self.timer.start(self.timeout_ms)
        
    def parar(self):
        """Para o monitoramento."""
        self.timer.stop()
        
    def resetar(self):
        """Reinicia a contagem do timer."""
        if self.timer.isActive():
            self.timer.start(self.timeout_ms)
            
    def _ao_estourar_tempo(self):
        """Emite o sinal quando o tempo de inatividade é atingido."""
        self.inatividade_detectada.emit()
        
    def eventFilter(self, objeto, evento):
        """Filtra eventos da aplicação para detectar atividade do usuário."""
        # Consideramos apenas cliques de mouse ou teclas pressionadas como interação
        # Mover o mouse (MouseMove) NÃO reseta o timer conforme requisitos
        if evento.type() in [QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress]:
            self.resetar()
            
        return super().eventFilter(objeto, evento)
