from gluon import current
import os
import base64

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
    def __init__(self, api=current.api):
        """

        :type api: unirio.api.request.UNIRIOAPIRequest
        :param api: UNIRIO API
        """
        self.api = api
        self.cacheTime = 86400  # Um dia

    @staticmethod
    def handle_blob(arquivo):
        caminho_arquivo = os.path.join(current.request.folder, 'uploads', arquivo)
        fstream = open(caminho_arquivo, mode="rb")
        file_b64 = base64.b64encode(fstream.read())
        fstream.close()
        return file_b64
