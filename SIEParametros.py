__author__ = 'raul'

from sie import SIE

class SIEParametrosDAO(SIE):

    def __init__(self):
        super(SIEParametrosDAO, self).__init__()

    def parametros_prod_inst(self):
        return self.api.get("PAR_PROD_INST",{},cache_time=100000).first()