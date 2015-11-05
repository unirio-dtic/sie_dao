from sie.tests.base import SIETestCase

__author__ = 'carlosfaruolo'


class TestDocumento(SIETestCase):
    DUMMY_INVALID_ID = 857893245934

    def __init__(self, *args, **kwargs):
        super(TestDocumento, self).__init__(*args, **kwargs)

        from sie.SIEDocumento import SIEDocumentoDAO
        from sie.SIEFuncionarios import SIEFuncionarioID

        self.documento_valido = self.api.get(SIEDocumentoDAO.path).first()
        self.funcionario_dummy = self.api.get(SIEFuncionarioID.path).first()

    def setUp(self):
        from sie.SIEDocumento import SIEDocumentoDAO
        self.dao = SIEDocumentoDAO()

# ======================================================================================================================

    def test_criar_documento_projeto_pesquisa(self):
        from sie.SIEProjetosPesquisa import SIEProjetosPesquisa
        dao_projetos = SIEProjetosPesquisa()
        documento = self.dao.criar_documento(dao_projetos.documento_inicial_padrao(self.funcionario_dummy))
        self.assertIsInstance(documento, dict)
        self.dao.remover_documento(documento)  # clean poopie

    def test_criar_documento_params_vazios(self):
        with self.assertRaises(KeyError):
            from sie.SIEProjetos import SIEProjetos
            dao_projetos = SIEProjetos()
            documento = self.dao.criar_documento(dict())
            # devo tentar apagar o documento?

    def test_obter_documento(self):
        documento = self.dao.obter_documento(2654)
        self.assertIsInstance(documento, dict)

    def test_obter_documento_id_errado(self):
        with self.assertRaises(Exception):
            documento = self.dao.obter_documento(self.DUMMY_INVALID_ID)

    def test_remover_documento(self):
        from sie.SIEProjetosPesquisa import SIEProjetosPesquisa
        dao_projetos = SIEProjetosPesquisa()
        documento = self.dao.criar_documento(dao_projetos.documento_inicial_padrao(self.funcionario_dummy))
        self.dao.remover_documento(documento)
        # test passed

    def test_atualizar_situacao_documento(self):
        self.fail("Test not implemented")  # TODO implement this!

# ======================================================================================================================

    def test_tramitar_documento(self):
        self.fail("Test not implemented")  # TODO implement this!

    def test_tramitar_documento_algum_param_nulo(self):
        self.fail("Test not implemented")  # TODO implement this!

    def test_obter_tramitacao_atual(self):
        self.assertIsInstance(self.dao.obter_tramitacao_atual(self.documento_valido), dict)

    def test_remover_tramitacoes(self):
        self.fail("Test not implemented")  # TODO implement this!

# ======================================================================================================================

    def test_obter_fluxo_inicial(self):
        self.assertIsInstance(self.dao.obter_fluxo_inicial(self.documento_valido), dict)

    def test_obter_fluxo_inicial_doc_vazio(self):
        with self.assertRaises(KeyError):
            self.dao.obter_fluxo_inicial(dict())

    def test_obter_fluxo_tramitacao_atual(self):
        self.assertIsInstance(self.dao.obter_fluxo_tramitacao_atual(self.documento_valido), dict)

    def test_obter_fluxo_tramitacao_atual_doc_vazio(self):
        with self.assertRaises(KeyError):
            self.dao.obter_fluxo_tramitacao_atual(dict())

    def test_obter_proximos_fluxos_tramitacoes_atual(self):
        fluxos = self.dao.obter_proximos_fluxos_tramitacao_validos(self.documento_valido)
        self.assertIsInstance(fluxos, list)
        for obj in fluxos:
            self.assertIsInstance(obj, dict)

# more TODO: implement remaining tests
# remember to implement wrong parameters tests as well
