from unirio.api import UNIRIOAPIRequest, APIServer
from gluon import current
import unittest

__author__ = 'diogomartins'


class SIETestCase(unittest.TestCase):
    API_KEY_VALID = '9287c7e89bc83bbce8f9a28e7d448fa7366ce23f163d2c385966464242e0b387e3a34d0e205cb775d769a44047995075'

    def __init__(self, *args, **kwargs):
        super(SIETestCase, self).__init__(*args, **kwargs)
        self.api = UNIRIOAPIRequest(self.API_KEY_VALID, APIServer.PRODUCTION_DEVELOPMENT, cache=None)
        current.api = self.api
