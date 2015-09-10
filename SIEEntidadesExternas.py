# -*- coding: utf-8 -*-
from sie import SIE
from unirio.api.apiresult import POSTException
from sie.SIETabEstruturada import SIETabEstruturada
from datetime import date

class SIEEntidadesExternas(SIE):

    COD_TABELA_TIPO_ENTIDADE = 214

    def __init__(self):
        super(SIEEntidadesExternas, self).__init__()
        self.path = 'ENTIDADES_EXTERNAS'

    def cadastra_entidade_externa(self, params):
        """

        :param params: Parâmetros de inserção no banco de dados obrigatórios: 'id_pessoa','desc_ent_externa/nome','doc_identificacao/cpf-cnpj','tipo_entidade_item','uf_item'
        :return: APIPost
        """

        try:
            params.update({
                "TIPO_ENTIDADE_TAB": self.COD_TABELA_TIPO_ENTIDADE,
                "UF_TAB": SIETabEstruturada().COD_TABELA_ESTADOS,
                "DT_CADASTRO": date.today()
            })
            entidade = self.api.post(self.path, params)

        except POSTException:
            entidade = None
        return entidade


    def get_tipos_entidade(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_TIPO_ENTIDADE)

