class ContextoUIPath:
    """
    Classe utilitária para analisar strings globais de contexto de foco na UI.
    A string (URI) segue o formato: page:<pagina>/<restante>
    Ex: 'page:dados/node:root/node:Croqui/expando:Picos'
    Ex: 'page:mapas/file:setor_principal.md'
    """
    def __init__(self, raw_path: str):
        self.raw_path = raw_path if raw_path else ""
        self._pagina = None
        self._caminho_local_arvore = ""
        self._arquivo_mapa = None

        self._parse()

    def _parse(self):
        if not self.raw_path:
            return

        partes = self.raw_path.split("/", 1)
        primeira_parte = partes[0]

        if primeira_parte.startswith("page:"):
            self._pagina = primeira_parte.split(":", 1)[1]
            if len(partes) > 1:
                resto = partes[1]
                if self._pagina == "mapas":
                    if resto.startswith("file:"):
                        self._arquivo_mapa = resto.split(":", 1)[1]
                else:
                    self._caminho_local_arvore = resto
        else:
            # Caso não tenha prefixo de página, assume que o path inteiro é o caminho da árvore local.
            self._caminho_local_arvore = self.raw_path

    @property
    def pagina(self) -> str:
        return self._pagina

    @property
    def caminho_local_arvore(self) -> str:
        return self._caminho_local_arvore

    @property
    def arquivo_mapa(self) -> str:
        return self._arquivo_mapa
