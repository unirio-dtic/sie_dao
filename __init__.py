# coding=utf-8
from .adapters import ADAPTER
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

    def __init__(self, adapter=ADAPTER):
        """
        :type adapter: SIEDAOBaseAdapter
        """
        self.__adapter = adapter()
        # Só precisam estar aqui para auxiliar no autocomplete da IDE. __getattr__ é equivalente
        self.api = self.__adapter.api
        self.funcionario = self.__adapter.funcionario

    def __getattr__(self, item):
        return self.__adapter.__getattr__(item)
