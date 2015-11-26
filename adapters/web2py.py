# coding=utf-8
from .base import SIEDAOBaseAdapter
from gluon import current
import os
import base64
import copy


class Web2pySIEAPIProvider(SIEDAOBaseAdapter):
    def __init__(self):
        """
        Sobreescreve métodos post, put e delete para os métodos privadados que inserem COD_OPERADOR em parâmetros
        """
        self.__override_api_methods()

    @property
    def api(self):
        # Cria copia idêntica do objeto que servirá para acesso público
        return copy.copy(self.__default_api)

    @property
    def __default_api(self):
        return current.api

    @property
    def usuario(self):
        return current.session.usuario

    @staticmethod
    def handle_blob(arquivo):
        caminho_arquivo = os.path.join(current.request.folder, 'uploads', arquivo)
        fstream = open(caminho_arquivo, mode="rb")
        file_b64 = base64.b64encode(fstream.read())
        fstream.close()
        return file_b64

    def __post(self, path, params):
        params.update({'COD_OPERADOR': self.usuario['ID_USUARIO']})
        return self.__default_api.post(path, params)

    def __put(self, path, params):
        params.update({'COD_OPERADOR': self.usuario['ID_USUARIO']})
        return self.__default_api.put(path, params)

    def __delete(self, path, params):
        params.update({'COD_OPERADOR': self.usuario['ID_USUARIO']})
        return self.__default_api.delete(path, params)

    def __override_api_methods(self):
        self.api.post = self.__post
        self.api.put = self.__put
        self.api.delete = self.__delete
