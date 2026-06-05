from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from aresta_api.proto.generated.indice_pb2 import Indice

class DialogoBuscaCroqui(QDialog):
    """
    Diálogo para busca e seleção de croquis oficiais.
    Lê a lista de croquis do arquivo indice.binarypb dentro do repositório sincronizado.
    """
    def __init__(self, storage, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.setWindowTitle("Buscar Croqui Oficial")
        self.setFixedSize(500, 400)
        self.id_selecionado = None
        
        self.layout_principal = QVBoxLayout(self)
        self.layout_principal.setContentsMargins(15, 15, 15, 15)
        self.layout_principal.setSpacing(10)
        
        self.campo_busca = QLineEdit()
        self.campo_busca.setPlaceholderText("Digite para buscar por nome ou ID...")
        self.campo_busca.setStyleSheet("padding: 8px; border: 1px solid #ced4da; border-radius: 4px;")
        self.layout_principal.addWidget(self.campo_busca)
        
        self.lista_croquis = QListWidget()
        self.lista_croquis.setStyleSheet("border: 1px solid #dee2e6; border-radius: 4px; background-color: #ffffff;")
        self.layout_principal.addWidget(self.lista_croquis)
        
        self.layout_botoes = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_confirmar = QPushButton("Confirmar")
        self.btn_confirmar.setDefault(True)
        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
            QPushButton:hover:enabled {
                background-color: #0b5ed7;
            }
        """)
        
        self.layout_botoes.addStretch()
        self.layout_botoes.addWidget(self.btn_cancelar)
        self.layout_botoes.addWidget(self.btn_confirmar)
        self.layout_principal.addLayout(self.layout_botoes)
        
        # Conexões
        self.campo_busca.textChanged.connect(self.filtrar_lista)
        self.lista_croquis.itemSelectionChanged.connect(self.ao_selecionar)
        self.lista_croquis.itemDoubleClicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_confirmar.clicked.connect(self.accept)
        
        self.carregar_indice()

    def carregar_indice(self):
        """
        Carrega os croquis a partir do indice.binarypb no storage.
        """
        if not self.storage:
            return
            
        caminho_repo = self.storage.obter_caminho_base_repo()
        if not caminho_repo:
            return
            
        caminho_indice = caminho_repo / "generated" / "indice.binarypb"
        if not caminho_indice.is_file():
            print(f"[AVISO] Arquivo de índice não encontrado em: {caminho_indice}")
            return
            
        try:
            indice = Indice()
            with open(caminho_indice, "rb") as f:
                indice.ParseFromString(f.read())
                
            self.lista_croquis.clear()
            for resumo in indice.croquis:
                texto = f"{resumo.nome} ({resumo.id})"
                self.lista_croquis.addItem(texto)
        except Exception as e:
            print(f"[ERRO] Falha ao carregar índice: {e}")

    def filtrar_lista(self, texto):
        """
        Filtra os itens da lista baseado no texto de busca.
        """
        for i in range(self.lista_croquis.count()):
            item = self.lista_croquis.item(i)
            ocultar = texto.lower() not in item.text().lower()
            self.lista_croquis.setRowHidden(i, ocultar)

    def ao_selecionar(self):
        """
        Habilita/desabilita o botão confirmar baseado na seleção.
        """
        self.btn_confirmar.setEnabled(self.lista_croquis.currentRow() >= 0)

    def obter_id_selecionado(self):
        """
        Extrai o ID do texto do item selecionado.
        Exemplo: "Nome (id)" -> "id"
        """
        item = self.lista_croquis.currentItem()
        if not item:
            return None
            
        texto = item.text()
        if "(" in texto and texto.endswith(")"):
            return texto.split("(")[-1][:-1]
        return None

    def accept(self):
        self.id_selecionado = self.obter_id_selecionado()
        if self.id_selecionado:
            super().accept()
