from sie.tests.base import SIETestCase

__author__ = 'carlosfaruolo'


class TestDocumento(SIETestCase):

    def __init__(self, *args, **kwargs):
        super(TestDocumento, self).__init__(*args, **kwargs)
        from sie.SIEDocumento import SIEDocumentoDAO

    def setUp(self):
        from sie.SIEDocumento import SIEDocumentoDAO
        self.dao = SIEDocumentoDAO()

    def test_obter_documento(self):
        documento = self.dao.obter_documento(2654)
        self.assertIsInstance(documento, dict)

    def test_falhar_em_obter_documento(self):
        with self.assertRaises(Exception):
            documento = self.dao.obter_documento(3463445687964795689578057846798)

