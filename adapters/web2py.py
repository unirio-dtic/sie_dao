from .base import SIEDAOBaseAdapter
from gluon import current


class Web2pySIEAPIProvider(SIEDAOBaseAdapter):
    @property
    def api(self):
        return current.api

    @property
    def funcionario(self):
        return current.session.funcionario
