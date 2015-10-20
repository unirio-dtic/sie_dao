from sie.tests.base import SIETestCase
from unirio.api.result import *
from unirio.api.exceptions import *

__author__ = 'diogomartins'


class TestOrgaosProjsPesquisa(SIETestCase):
    path = 'V_PROJETOS_ORGAOS'
    DUMMY_ID = 999999999999

    def __init__(self, *args, **kwargs):
        super(TestOrgaosProjsPesquisa, self).__init__(*args, **kwargs)
        self.valid = self.api.get(self.path).first()

        from sie.SIEProjetosPesquisa import SIEOrgaosProjsPesquisa
        self.orgaos = SIEOrgaosProjsPesquisa()

    def test_get_valid_orgao(self):
        orgao = self.orgaos.get_orgao(self.valid['ID_ORGAO_PROJETO'])
        self.assertEqual(self.valid, orgao)

    def test_get_invalid_orgao(self):
        orgao = self.orgaos.get_orgao(self.DUMMY_ID)
        self.assertEqual(orgao, {})

    def test_get_orgaoes_valid_projeto(self):
        projeto = self.api.get(TestProjetosPesquisa.path).first()
        orgs = self.orgaos.get_orgaos(projeto['ID_PROJETO'])
        self.assertIsInstance(orgs, list)
        self.assertTrue(len(orgs) >= 1, "Lista deve conter pelo menos um item")

    def test_get_orgaoes_invalid_projeto(self):
        orgs = self.orgaos.get_orgaos(self.DUMMY_ID)
        self.assertIsInstance(orgs, list)
        self.assertTrue(len(orgs) == 0)

    def test_cadastra_orgao_valid_projeto(self):
        projeto = self.api.get(TestProjetosPesquisa.path).first()
        orgao = self.orgaos.get_orgao(projeto['ID_PROJETO'])
        result = self.orgaos.cadastra_orgao(orgao)
        self.assertIsInstance(result, APIPOSTResponse)

    def test_cadastra_orgao_empty_orgao(self):
        with self.assertRaises(APIException):
            self.orgaos.cadastra_orgao({})

    def test_atualizar_orgao_(self):
        #todo respsota deveria ser 422 ou 400
        orgao_copy = self.orgaos.get_orgao(self.valid['ID_ORGAO_PROJETO'])
        result = self.orgaos.atualizar_orgao(orgao_copy)
        self.assertTrue(result)
        updated_orgao = self.orgaos.get_orgao(orgao_copy['ID_ORGAO_PROJETO'])
        self.assertEqual(updated_orgao['NOME'], orgao_copy['NOME'])



class TestParticipantesProjsPesquisa(SIETestCase):
    def setUp(self):
        pass


class TestProjetosPesquisa(SIETestCase):
    path = 'V_PROJETOS_PESQUISA'
    pass


