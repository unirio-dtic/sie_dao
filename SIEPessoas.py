# -*- coding: utf-8 -*-
from sie import SIE
from unirio.api.apiresult import POSTException

class SIEPessoas(SIE):
    def __init__(self):
        super(SIEPessoas, self).__init__()
        self.path = 'PESSOAS'

    def getPessoa(self, ID_PESSOA):
        params = {
            'ID_PESSOA': ID_PESSOA,
            'LMIN': 0,
            'LMAX': 1
        }
        return self.api.performGETRequest(self.path, params, cached=self.cacheTime).content[0]


    def cadastrar_pessoa(self, params):
        """
        :param params: Parâmetros de inserção no banco de dados obrigatórios: Nome, Nome_UP, Nome Social e Natureza Jurídica
        :return:
        """
        try:
            pessoa = self.api.post(self.path, params)
        except POSTException:
            pessoa = None
        return pessoa


