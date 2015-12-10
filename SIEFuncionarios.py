# coding=utf-8
from sie import SIE

__all__ = ["SIEFuncionarioID", "SIEFuncionarios", "SIEDocentes"]


class SIEFuncionarioID(SIE):
    path = "V_FUNCIONARIO_IDS"

    def __init__(self):
        super(SIEFuncionarioID, self).__init__()
        self.cacheTime *= 10

    def getFuncionarioIDs(self, cpf):
        return self.api.get(self.path, params={"CPF": cpf}, cache_time=self.cacheTime).content[0]


class SIEFuncionarios(SIE):
    path = "FUNCIONARIOS" # TODO Isso tá me enganando. Não existe consulta a essa tabela!

    def __init__(self):
        """ """

        super(SIEFuncionarios, self).__init__()

    def getEscolaridade(self, ID_FUNCIONARIO):
        """


        :rtype : dict
        :param ID_FUNCIONARIO: Identificador único de funcionário na tabela FUNCIONARIOS
        :return: Um dicionário contendo chaves relativas a escolaridade
        :raise e:
        """
        try:
            return self.api.get(
                self.path,
                {"ID_FUNCIONARIO": ID_FUNCIONARIO},
                ["ESCOLARIDADE_ITEM", "ESCOLARIDADE_TAB"]
            ).content[0]
        except ValueError as e:
            session.flash = "Não foi possível encontrar o funcionário."
            raise e

    def get_funcionario(self, cpf):
        return self.api.get("V_FUNCIONARIOS", params={"CPF": cpf}, cache_time=self.cacheTime).content[0]


class SIEDocentes(SIE):
    path = "V_DOCENTES"

    COD_ATIVO = 1

    def __init__(self):
        super(SIEDocentes, self).__init__()

    def getDocentes(self):
        params = {
            "SITUACAO_ITEM": self.COD_ATIVO
        }
        fields = [
            "MATR_EXTERNA",
            "NOME_DOCENTE"
        ]
        return self.api.get(self.path, params, fields)

    def get_docente(self,cpf):
        params = {
            "SITUACAO_ITEM": self.COD_ATIVO,
            "CPF":cpf
        }
        fields = [
            "MATR_EXTERNA",
            "NOME_DOCENTE"
        ]

        return self.api.get_single_result(self.path,params,cache_time=10000)


