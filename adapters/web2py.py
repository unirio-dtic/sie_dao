from .base import SIEDAOBaseAdapter
from gluon import current
import os
import base64


class Web2pySIEAPIProvider(SIEDAOBaseAdapter):
    @property
    def api(self):
        return current.api

    @property
    def funcionario(self):
        return current.session.funcionario

    @staticmethod
    def handle_blob(arquivo):
        caminho_arquivo = os.path.join(current.request.folder, 'uploads', arquivo)
        fstream = open(caminho_arquivo, mode="rb")
        file_b64 = base64.b64encode(fstream.read())
        fstream.close()
        return file_b64
