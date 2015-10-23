from sie.tests.base import SIETestCase

__author__ = 'diogomartins'


class TestTabEstruturada(SIETestCase):
    COD_TABELA_INVALIDO = 9999999999
    ITEM_TABELA_INVALIDO = 9999999999

    def __init__(self, *args, **kwargs):
        super(TestTabEstruturada, self).__init__(*args, **kwargs)

        from sie.SIETabEstruturada import SIETabEstruturada
        self.valid_entry = self.api.get(SIETabEstruturada.path, {"ITEM_TABELA_MIN": 1}).first()

    def setUp(self):
        from sie.SIETabEstruturada import SIETabEstruturada
        self.tab = SIETabEstruturada()

    def test_descricao_de_item_valido(self):
        descricao = self.tab.descricaoDeItem(self.valid_entry['ITEM_TABELA'], self.valid_entry['COD_TABELA'])
        self.assertEqual(descricao, self.valid_entry['DESCRICAO'])

    def test_descricao_de_item_invalido(self):
        with self.assertRaises(AttributeError):
            self.tab.descricaoDeItem(self.ITEM_TABELA_INVALIDO, self.COD_TABELA_INVALIDO)

    def test_items_de_codigo_valido(self):
        items = self.tab.itemsDeCodigo(self.valid_entry['COD_TABELA'])
        self.assertIsInstance(items, list)
        for item in items:
            if item['ITEM_TABELA'] == self.valid_entry['ITEM_TABELA']:
                self.assertEqual(item['DESCRICAO'], self.valid_entry['DESCRICAO'])

    def test_items_de_codigo_invalido(self):
        with self.assertRaises(AttributeError):
            self.tab.itemsDeCodigo(self.COD_TABELA_INVALIDO)
