from sie import SIE


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