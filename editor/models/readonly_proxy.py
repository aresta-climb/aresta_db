# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from typing import Any, Iterator
from google.protobuf.message import Message


class ReadOnlyProxy:
    """
    Wrapper proxy recursivo que impede mutações diretas em mensagens Protobuf.
    Qualquer tentativa de atribuir valor ou chamar métodos mutadores gera um RuntimeError.
    """
    def __init__(self, obj: Any) -> None:
        object.__setattr__(self, "_obj", obj)

    def __getattr__(self, name: str) -> Any:
        val = getattr(self._obj, name)
        
        if isinstance(val, Message):
            return ReadOnlyProxy(val)
            
        # Verifica se é um repeated container do protobuf (que tem append, add, insert, etc)
        type_name = type(val).__name__
        if "Repeated" in type_name and "Container" in type_name:
            return ReadOnlyListProxy(val)
            
        if type_name == "ExtensionDict":
            return ReadOnlyExtensionProxy(val)
            
        return val

    def __setattr__(self, name: str, value: Any) -> None:
        raise RuntimeError(
            f"Violação de Arquitetura MVC: Proibido alterar o atributo '{name}' "
            "diretamente na View! Use os Comandos para modificar o Model."
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ReadOnlyProxy):
            return bool(self._obj == other._obj)
        return bool(self._obj == other)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def obter_id_nativo(self) -> int:
        """Retorna o id() do objeto original encapsulado."""
        return id(self._obj)


class ReadOnlyListProxy:
    def __init__(self, lst: Any) -> None:
        self._lst: Any = lst
        
    def __getitem__(self, index: int) -> Any:
        val = self._lst[index]
        if isinstance(val, Message):
            return ReadOnlyProxy(val)
        return val

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ReadOnlyListProxy):
            return bool(self._lst == other._lst)
        return bool(self._lst == other)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def obter_id_nativo(self) -> int:
        """Retorna o id() da lista original encapsulada."""
        return id(self._lst)
        
    def __len__(self) -> int:
        return len(self._lst)
        
    def __iter__(self) -> Iterator[Any]:
        for item in self._lst:
            if isinstance(item, Message):
                yield ReadOnlyProxy(item)
            else:
                yield item

    def __getattr__(self, name: str) -> Any:
        # Impede chamadas a append, pop, etc
        if name in ("append", "pop", "remove", "insert", "clear", "extend", "add", "sort", "reverse"):
            raise RuntimeError(
                f"Violação de Arquitetura MVC: Proibido chamar '{name}' "
                "diretamente na View! Use os Comandos para modificar o Model."
            )
        return getattr(self._lst, name)

    def __setitem__(self, index: int, value: Any) -> None:
        raise RuntimeError(
            "Violação de Arquitetura MVC: Proibido atribuir itens diretamente na View! "
            "Use os Comandos para modificar o Model."
        )

    def __delitem__(self, index: int) -> None:
        raise RuntimeError(
            "Violação de Arquitetura MVC: Proibido deletar itens diretamente na View! "
            "Use os Comandos para modificar o Model."
        )


class ReadOnlyExtensionProxy:
    def __init__(self, ext_dict: Any) -> None:
        self._ext_dict: Any = ext_dict
        
    def __getitem__(self, key: Any) -> Any:
        val = self._ext_dict[key]
        if isinstance(val, Message):
            return ReadOnlyProxy(val)
        return val
        
    def __setitem__(self, key: Any, value: Any) -> None:
        raise RuntimeError(
            "Violação de Arquitetura MVC: Proibido alterar a extensão diretamente na View! "
            "Use os Comandos para modificar o Model."
        )
        
    def __delitem__(self, key: Any) -> None:
        raise RuntimeError(
            "Violação de Arquitetura MVC: Proibido deletar a extensão diretamente na View! "
            "Use os Comandos para modificar o Model."
        )
        
    def __contains__(self, key: Any) -> bool:
        return key in self._ext_dict


def _copia_segura(valor: Any) -> Any:
    """
    Helper function para uso interno (models e commands).
    Faz a cópia profunda de Proxies ou Mensagens Protobuf reais.
    Retorna o valor original para tipos primitivos.
    """
    if isinstance(valor, ReadOnlyProxy):
        valor = object.__getattribute__(valor, "_obj")
    elif isinstance(valor, ReadOnlyListProxy):
        # Para listas proxy, retornamos uma lista Python contendo cópias profundas
        return [_copia_segura(item) for item in valor]
        
    if isinstance(valor, Message):
        dup = type(valor)()
        dup.CopyFrom(valor)
        return dup
        
    return valor

