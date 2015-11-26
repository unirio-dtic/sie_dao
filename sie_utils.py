# -*- coding: utf-8 -*-
from datetime import datetime
from deprecate import deprecated

__author__ = 'raulbarbosa'


def encoded_tab_estruturada(encoding):
    """

    :param encoding: um encoding para 'encodar' a string
    :return: uma lista onde cada elemento é uma tupla (item,descricao) e descricao será o parâmetro a ser encodado
    """
    def actualDecorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            lista = fn(self, *args, **kwargs)
            if lista:
                lista = [(item, descricao.encode(encoding)) for (item, descricao) in lista]  # encoda segundo item (texto do banco)
            return lista

        return wrapper

    return actualDecorator


def encode_if_unicode(x):
    return x.encode('utf-8') if type(x) == unicode else x

@deprecated
def dict_encode_if_unicode(dicionario):
    return {campo: encode_if_unicode(dicionario[campo]) for campo in dicionario} if type(dicionario) == dict else {}

def campos_sie_lower(lista):
    """
    Refaz uma lista de Rows vinda da API com os nomes dos campos em letra minuscula
    :param lista:
    :return: lista_final com os campos em minuscula.
    """
    lista_final = []
    for item in lista:
        novo_item = {}
        for k,v in item.iteritems():
            novo_item[encode_if_unicode(k).lower()] = encode_if_unicode(v)
        lista_final.append(novo_item)
    return lista_final


def sie_date_to_str():
    raise NotImplementedError

def sie_str_to_date(campo,format='%Y-%m-%d'):
    return datetime.strptime(campo,format).date()