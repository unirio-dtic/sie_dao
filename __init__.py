from gluon import current
import os
import base64
import abc

from sie.adapters.web2py import Web2pySIEAPIProvider

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


class SIEException(Exception):
    """ Bad things happens. """
    def __init__(self, msg, cause=None, *args, **kwargs):
        """
        An exception when using the SIE DAO.
        :type msg: str
        :type cause: BaseException
        """
        super(SIEException, self).__init__(*args, **kwargs)
        self.msg = msg
        self.cause = cause

    def __str__(self):
        return self.msg + "\n\tCaused by " + str(type(self.cause)) + ": " + str(self.cause) + "\n\t"


class SIE(object):
    __metaclass__ = abc.ABCMeta
    cacheTime = 86400

    def __init__(self):
        self.__adapter = Web2pySIEAPIProvider()
        self.api = self.__adapter.api
        self.funcionario = self.__adapter.funcionario

    @staticmethod
    def handle_blob(arquivo):
        caminho_arquivo = os.path.join(current.request.folder, 'uploads', arquivo)
        fstream = open(caminho_arquivo, mode="rb")
        file_b64 = base64.b64encode(fstream.read())
        fstream.close()
        return file_b64
