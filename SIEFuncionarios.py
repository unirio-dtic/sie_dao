# coding=utf-8
from sie import SIE

__all__ = ["SIEFuncionarioID", "SIEFuncionarios", "SIEDocentes"]

class SIEFuncionarioID(SIE):
    def __init__(self, CPF):
        super(SIEFuncionarioID, self).__init__()
        self.path = "V_FUNCIONARIO_IDS"
        self.CPF = CPF
        self.cacheTime *= 10

    def getFuncionarioIDs(self):
        return self.api.performGETRequest(self.path, params={"CPF": self.CPF}, cached=self.cacheTime).content[0]


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
    def __init__(self):
        super(SIEDocentes, self).__init__()
        self.path = "V_DOCENTES"

    def getDocentes(self):
        params = {
            "SITUACAO_ITEM": 1
        }
        fields = [
            "MATR_EXTERNA",
            "NOME_DOCENTE"
        ]
        return self.api.performGETRequest(self.path, params, fields)