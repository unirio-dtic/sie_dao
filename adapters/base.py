import abc


class SIEDAOBaseAdapter(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def api(self):
        """
        :rtype: BaseAPI
        """
        pass

    @abc.abstractproperty
    def funcionario(self):
        """
        :rtype: dict
        """
        pass


class BaseAPI:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get(self, path, params=None, fields=None, cache_time=0, bypass_no_content_exception=False): return NotImplemented

    @abc.abstractmethod
    def post(self, path, params): return NotImplemented

    @abc.abstractmethod
    def put(self, path, params): return NotImplemented

    @abc.abstractmethod
    def delete(self, path, params): return NotImplemented


class BaseAPIResponseObject:
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def response(self): pass

    @abc.abstractproperty
    def request(self): pass


class BaseGETResponse(BaseAPIResponseObject):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def lmin(self): pass

    @abc.abstractproperty
    def lmax(self): pass

    @abc.abstractproperty
    def content(self): pass

    @abc.abstractproperty
    def fields(self): pass

    @abc.abstractmethod
    def first(self): return NotImplemented


class BasePOSTResponse(BaseAPIResponseObject):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def insertId(self): pass


class BasePUTResponse(BaseAPIResponseObject):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def affectedRows(self): pass


class BaseDELETEResponse(BaseAPIResponseObject):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def affectedRows(self): pass
