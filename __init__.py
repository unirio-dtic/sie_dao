from gluon import current
import os
import base64
import abc

__all__ = [
    "SIEAlunos"
    "SIEBolsistas",
    "SIEDocumento",
    "SIEFuncionarios",
    "SIEPessoas",
    "SIEProjetos",
    "SIEServidores",
    "SIETabEstruturada",
    "SIEProcesso"
]


class SIE(object):
    __metaclass__ = abc.ABCMeta
    cacheTime = 86400

    @property
    def api(self):
        return current.api

    @staticmethod
    def handle_blob(arquivo):
        caminho_arquivo = os.path.join(current.request.folder, 'uploads', arquivo)
        fstream = open(caminho_arquivo, mode="rb")
        file_b64 = base64.b64encode(fstream.read())
        fstream.close()
        return file_b64
