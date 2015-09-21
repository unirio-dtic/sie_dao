# coding=utf-8
from sie import SIE

__all__ = ["SIEFuncionarioID", "SIEFuncionarios", "SIEDocentes"]

class SIEFuncionarioID(SIE):
    def __init__(self):
        super(SIEFuncionarioID, self).__init__()
        self.path = "V_FUNCIONARIO_IDS"
        self.cacheTime *= 10

    def getFuncionarioIDs(self, cpf):
        return self.api.performGETRequest(self.path, params={"CPF": cpf}, cached=self.cacheTime).content[0]


class SIEFuncionarios(SIE):
    def __init__(self):
        """


        """
        super(SIEFuncionarios, self).__init__()
        self.path = "FUNCIONARIOS"

    def getEscolaridade(self, ID_FUNCIONARIO):
        """


        :rtype : dict
        :param ID_FUNCIONARIO: Identificador único de funcionário na tabela FUNCIONARIOS
        :return: Um dicionário contendo chaves relativas a escolaridade
        :raise e:
        """
        try:
            return self.api.performGETRequest(
                self.path,
                {"ID_FUNCIONARIO": ID_FUNCIONARIO},
                ["ESCOLARIDADE_ITEM", "ESCOLARIDADE_TAB"]
            ).content[0]
        except ValueError as e:
            session.flash = "Não foi possível encontrar o funcionário."
            raise e

class SIEDocentes(SIE):

    COD_ATIVO = 1

    def __init__(self):
        super(SIEDocentes, self).__init__()
        self.path = "V_DOCENTES"

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

        try:
            res = self.api.get(self.path, params, cached=self.cacheTime)
            return res.content if res is not None else []
        except ValueError:
            return []
