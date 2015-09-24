# -*- coding: utf-8 -*-
__author__ = 'carlos.faruolo'

from . import SIE

__all__ = ["SIEProcesso", "SIEProcessoDados", "SIEProcessoTramitacoes"]


class SIEProcesso(SIE):
    def __init__(self):
        super(SIEProcesso, self).__init__()
        self.path = NotImplementedError
        self.lmin = 0
        self.lmax = 1000

    def getContent(self, params=None):
        """
        :rtype : APIPOSTResponse
        :type params: dict
        """
        if not params:
            params = {}
        limits = {"LMIN": self.lmin, "LMAX": self.lmax}
        for k, v in params.items():
            params[k] = str(params[k]).upper()
        params.update(limits)

        processos = self.api.performGETRequest(self.path, params, cached=86400)
        if processos:
            return processos.content
        else:
            return list()


class SIEProcessoDados(SIEProcesso):
    def __init__(self):
        super(SIEProcessoDados, self).__init__()
        self.path = "V_PROCESSOS_DADOS"

    def getProcessos(self, params=None):
        if not params:
            params = {}
        return self.getContent(params)

    def getProcessoDados(self, ID_DOCUMENTO):
        params = {"ID_DOCUMENTO": ID_DOCUMENTO}
        content = self.getProcessos(params)
        return content[0]


class SIEProcessoTramitacoes(SIEProcesso):
    def __init__(self):
        super(SIEProcessoTramitacoes, self).__init__()
        self.path = "V_PROCESSOS_TRAMITACOES"

    def getTramitacoes(self, NUM_PROCESSO):
        params = {"NUM_PROCESSO": NUM_PROCESSO, "ORDERBY": "DT_ENVIO"}
        return self.getContent(params)
