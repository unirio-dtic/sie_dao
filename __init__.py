from gluon import current

__all__ = [
    "SIEAlunos"
    "SIEBolsistas",
    "SIEDocumento",
    "SIEFuncionarios",
    "SIEPessoas",
    "SIEProjetos",
    "SIEServidores",
    "SIETabEstruturada",
]


class SIE(object):
    def __init__(self, api=current.api):
        """

        :type api: unirio.api.apirequest.UNIRIOAPIRequest
        :param api: UNIRIO API
        """
        self.api = api
        self.db = current.db
        self.cacheTime = 86400  # Um dia