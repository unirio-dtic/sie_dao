from sie.tests.base import SIETestCase

__author__ = 'carlosfaruolo'


class TestDocumento(SIETestCase):
    DUMMY_INVALID_ID = 857893245934

    def __init__(self, *args, **kwargs):
        super(TestDocumento, self).__init__(*args, **kwargs)

        from sie.SIEDocumento import SIEDocumentoDAO

        self.documento_valido = self.api.get(SIEDocumentoDAO.path).first()

    def setUp(self):
        from sie.SIEDocumento import SIEDocumentoDAO
        self.dao = SIEDocumentoDAO()

    def test_obter_documento(self):
        documento = self.dao.obter_documento(2654)
        self.assertIsInstance(documento, dict)

    def test_obter_documento_id_errado(self):
        with self.assertRaises(Exception):
            documento = self.dao.obter_documento(self.DUMMY_INVALID_ID)

    # TODO fazer esses abaixo:

    def test_obter_tramitacao_atual(self):
        self.fail()

    # criar_documento()

    def test_criar_documento(self):
        self.fail()

    def test_criar_documento_tipo_errado(self):
        self.fail()

    def test_obter_fluxo_tramitacao_atual(self):
        self.fail()

    def test_obter_proximos_fluxos_tramitacoes_atual(self):
        self.fail()

    # more TODO ...
