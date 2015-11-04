# coding=utf-8

from datetime import date, timedelta
from time import strftime
from gluon import current
from deprecate import deprecated

from sie import SIE
from unirio.api.exceptions import APIException

__all__ = [
    "SIEDocumentoDAO",
]


class SIEDocumentoDAO(SIE):
    # ID_TIPO_DOC = 215  # sou uma gambi esquecida

    path = "DOCUMENTOS"
    """ Caminho da API para trabalhar com documentos """

    tramite_path = "TRAMITACOES"
    """ Caminho da API para trabalhar com tramitações """

    fluxo_path = "FLUXOS"

    def __init__(self):
        super(SIEDocumentoDAO, self).__init__()

    def criar_documento(self, novo_documento_params):
        """
        Inclui um novo documento eletronico do SIE e retorna ele. Uma tramitação inicial já é iniciada (exceto se for especificado sem_tramite=True).

        Notas:
        SITUACAO_ATUAL = 1      => Um novo documento sempre se inicia com 1
        TIPO_PROPRIETARIO = 20  => Indica restrição de usuários
        TIPO_ORIGEM = 20        => Recebe mesmo valor de TIPO_PROPRIETARIO
        SEQUENCIA = 1           => Indica que é o primeiro passo de tramitação
        TIPO_PROCEDENCIA = S    => Indica servidor
        TIPO_INTERESSADO = S    => Indica servidor

        IND_ELIMINADO, IND_AGENDAMENTO, IND_RESERVADO,
        IND_EXTRAVIADO, TEMPO_ESTIMADO => Valores fixos (Seguimos documento com recomendações da síntese)

        :param novo_documento_params: Um dicionario contendo parametros para criar o documento.
        :type  novo_documento_params: dict

        :rtype : dict
        :return: Um dicionário contendo a entrada da tabela DOCUMENTOS correspondente ao documento criado.
        """

        #2

        # num_processo_handler = self._NumProcessoHandler(self, id_tipo_doc, current.session.edicao.dt_inicial_projeto.year)
        num_processo_handler = _NumProcessoHandler(self.api, novo_documento_params["ID_TIPO_DOC"])

        # determinando ultimo numero
        num_processo = num_processo_handler.gerar_numero_processo()

        novo_documento_params.update({"NUM_PROCESSO": num_processo})

        try:
            id_documento = self.api.post(self.path, novo_documento_params).insertId
            novo_documento = self.api.get(self.path, {"ID_DOCUMENTO": id_documento}).first()
            # criando entrada na tabela de tramitacões (pre-etapa)
            self.__adiciona_registro_inicial_tramitacao(novo_documento)
        except APIException as e:
            # TODO decrementar proximo_numero_tipo_documento
            num_processo_handler.reverter_ultimo_numero_processo()
            raise e

        return novo_documento

    def obter_documento(self, id_documento):
        """

        :type id_documento: int
        :param id_documento: Identificador único de uma entrada na tabela DOCUMENTOS
        :rtype : dict
        :return: Uma dicionário correspondente a uma entrada da tabela DOCUMENTOS
        """
        params = {
            "ID_DOCUMENTO": id_documento,
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.get(self.path, params, cache_time=self.cacheTime).first()

    def remover_documento(self, documento):
        """
        Dada uma entrada na tabela de DOCUMENTOS, a função remove suas tramitações e o documento em si

        :type documento: dict
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        self.remover_tramitacoes(documento)
        response = self.api.delete(self.path, {'ID_DOCUMENTO': documento['ID_DOCUMENTO']})
        if response.affectedRows > 0:
            del documento

    def atualizar_situacao_documento(self, documento, fluxo):
        novo_documento = {
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "SITUACAO_ATUAL": fluxo["SITUACAO_FUTURA"]
        }
        self.api.put(self.path, novo_documento)

    # ========================= Tramitacao ===================================

# TODO checar com o alex se esse registro inicial é padrão ou varia de acordo com o tipo de documento
    def __adiciona_registro_inicial_tramitacao(self, documento):
        """
        Cria um registro na tabela de tramitações para esse documento.

        Deve ser feito antes de fazer a primeira tramitacao do documento (de preferencia ao criar o documento)

        SEQUENCIA = 1           => Primeiro passo da tramitação
        PRIORIDADE_TAB = 5101   => Tabela estruturada utilizada para indicar o nível de prioridade
        PRIORIDADE_ITEM = 2     => Prioridade normal
        SITUACAO_TRAMIT = T     => Indica que o documento não foi enviado ainda para tramitação (aguardando)
        IND_RETORNO_OBRIG = N   => Valor fixo, conforme documento da Síntese

        :rtype : dict
        :return: Um dicionário equivalente a uma entrada da tabela TRAMITACOES
        """
        tramitacao_params = {
            "SEQUENCIA": 1,
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "TIPO_ORIGEM": documento["TIPO_PROPRIETARIO"],
            "ID_ORIGEM": documento["ID_PROPRIETARIO"],
            "TIPO_DESTINO": documento["TIPO_PROPRIETARIO"],
            "ID_DESTINO": documento["ID_PROPRIETARIO"],
            "DT_ENVIO": date.today(),
            "SITUACAO_TRAMIT": "T",
            "IND_RETORNO_OBRIG": "N",
            "PRIORIDADE_TAB": 5101,
        }

        id_tramitacao = self.api.post(self.tramite_path, tramitacao_params).insertId
        tramitacao = self.api.get(self.tramite_path, {"ID_TRAMITACAO": id_tramitacao}).first()

        return tramitacao

    def tramitar_documento(self, documento, funcionario, fluxo=None, resolvedor_destino=None):
        """
        Tramita um documento de acordo com o fluxo especificado.

        A regra de negócios diz que uma tramitação muda a situação atual de um documento para uma situação futura
        determinada pelo seu fluxo. Isso faz com que seja necessário que atulizemos as tabelas `TRAMITACOES` e
        `DOCUMENTOS`

        Caso o fluxo não seja especificado (ou None), a chamada corresponde às etapas especificadas no documento enviado pela consultoria Síntese a respeito da primeira tramitação de um projeto.
        Nesse caso, com a tramitação criada por uma etapa de criar documento, ela é alterada com algumas informações para entrega.

        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :param funcionario: Um dicionário referente a uma entrada na view V_FUNCIONARIO_IDS
        :type funcionario: dict
        :param fluxo: Um dicionário referente a uma entrada na tabela FLUXOS
        :type fluxo: dict
        :param resolvedor_destino é um callable que resolve o destino dado um fluxo que tenha a flag IND_QUERY='S', ou seja, o tipo_destino e id_destino devem ser obtidos através de uma query adicional. O retorno deve ser uma tupla (tipo_destino, id_destino).

        :rtype : dict
        """
        if not fluxo:
            fluxo = self.obter_fluxo_inicial(documento)

        try:
            # Pega a tramitacao atual
            tramitacao = self.obter_tramitacao_atual(documento)
        except APIException as e:
            current.session.flash = "Não foi possível atualizar tramitação"
            raise e

        try:
            # Se IND_QUERY é S, temos que alterar o tipo_destino e o id_destino do fluxo (não é o destino do fluxo cadastrado).
            if fluxo['IND_QUERY'].strip() == 'S':
                print("Fluxo possui flag IND_QUERY='S'. Usar resolvedor_destino para atualizar o tipo_destino e id_destino")
                if not resolvedor_destino:
                    msg = "Tentando tramitar um documento através de um fluxo que possui a flag IND_QUERY='S' sem ter especificado resolvedor_destino! Parar."
                    current.session.flash = msg
                    print(msg)
                    raise RuntimeError
                (tipo_destino, id_destino) = resolvedor_destino(fluxo)
                fluxo.update({'TIPO_DESTINO': tipo_destino, 'ID_DESTINO': id_destino})

            nova_tramitacao = {
                "ID_TRAMITACAO": tramitacao["ID_TRAMITACAO"],
                "TIPO_DESTINO": fluxo["TIPO_DESTINO"],
                "ID_DESTINO": fluxo["ID_DESTINO"],
                "DT_ENVIO": date.today(),
                "DT_VALIDADE": self.__calcular_data_validade(date.today(), fluxo["NUM_DIAS"]),
                "DESPACHO": fluxo["TEXTO_DESPACHO"],
                "SITUACAO_TRAMIT": "E",  # TODO Certo seria só virar E quando alguém abrisse tal documento/projeto?
                "IND_RETORNO_OBRIG": "F",
                "ID_FLUXO": fluxo["ID_FLUXO"],
                "ID_USUARIO_INFO": funcionario["ID_USUARIO"],
                "DT_DESPACHO": date.today(),
                "HR_DESPACHO": strftime("%H:%M:%S")
            }

            self.api.put(self.tramite_path, nova_tramitacao)
            try:
                self.atualizar_situacao_documento(documento, fluxo)
            except APIException as e:
                current.session.flash = "Não foi possível atualizar o documento"
                raise e

        except APIException as e:
            if not current.session.flash:
                current.session.flash = "Não foi possível atualizar tramitação"
            raise e

    def obter_tramitacao_atual(self, documento):
        """
        Retorna a tramitacao atual (mais recente) do documento.
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :return: Uma dicionário correspondente a uma entrada da tabela TRAMITACOES
        :rtype : dict
        """
        try:
            params = {
                "ID_DOCUMENTO": documento['ID_DOCUMENTO'],
                "ORDERBY": "ID_TRAMITACAO",
                "SORT": "DESC"
            }
            # Pega a tramitacao atual
            tramitacao = self.api.get(self.tramite_path,params ).first()
        except APIException as e:
            current.session.flash = "Não foi possível atualizar tramitação"
            raise e
        return tramitacao

    def remover_tramitacoes(self, documento):
        """
        Dado um documento, a função busca e remove suas tramitações. Use com cautela.
        :type documento: dict
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        try:
            tramitacoes = self.api.get(self.tramite_path, {"ID_DOCUMENTO": documento['ID_DOCUMENTO']}, ['ID_TRAMITACAO'])
            for tramitacao in tramitacoes.content:
                self.api.delete(self.tramite_path, {'ID_TRAMITACAO': tramitacao['ID_TRAMITACAO']})
        except APIException as e:
            print "Nenhuma tramitação encontrada para o documento %d" % documento['ID_DOCUMENTO']
            raise e

    # ========================= Fluxos ===================================

    # TODO checar com o alex se esse fluxo inicial é padrão ou varia de acordo com o tipo de documento
    def obter_fluxo_inicial(self, documento):
        """
        Retorna o fluxo de acordo com a query para pegar o fluxo inicial de uma tramitacao:

        “SELECT F.* FROM FLUXOS F WHERE F.SITUACAO_ATUAL = 1 AND F.IND_ATIVO = ‘S’ AND F.ID_TIPO_DOC =
        :ID_TIPO_DOC”

        :param documento:
        :return:
        """
        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_ATUAL": documento["SITUACAO_ATUAL"], # TODO Hardcodar 1?
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.get(self.fluxo_path, params).first()

    def obter_fluxo_tramitacao_atual(self, documento):  # TODO verificar se isto é util
        """
        Retorna o fluxo de tramitacao atual do documento especificado:

        SELECT F.* FROM FLUXOS F WHERE ID_FLUXO = (SELECT T.* FROM TRAMITACOES WHERE ID_DOCUMENTO = :ID_DOCUMENTO ORDER BY :ID_TRAMITACAO DESC LIMIT 1)

        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :rtype : dict
        :return: Uma dicionário correspondente a uma entrada da tabela FLUXOS
        """

        # obter da tabela de tramitacoes pois o fluxo pode ter sido modificado ao longo do tempo
        # isso é de contraste com obter da tabela de fluxos para termos as opcoes de fluxo mais atualizadas
        tramitacao_atual = self.obter_tramitacao_atual(documento)
        params = {
            "ID_FLUXO": tramitacao_atual["ID_FLUXO"],
            "LMIN": 0,  # sera necessario?
            "LMAX": 1   # sera necessario?
        }
        return self.api.get(self.fluxo_path, params).first()

    def obter_proximos_fluxos_tramitacao_validos(self, documento):
        """
        Retorna os proximos fluxos de tramitacoes validos atualmente para o documento especificado
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :return: dicionarios com os fluxos
        :rtype: APIResultObject
        """

        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_ATUAL": documento["SITUACAO_FUTURA"],
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 99999999
        }
        return self.api.get(self.fluxo_path, params)

    @staticmethod
    def __calcular_data_validade(data, dias):
        """
        Autodocumentada.

        :type data: date
        :type dias: int
        :rtype : date
        :param data: Data incial
        :param dias: Quantidade de dias
        :return: Retorna a data enviada, acrescida da quantidade de dias
        """
        return data + timedelta(days=dias)

class _NumProcessoHandler(object):
    """ Classe helper para gerar os numeros de processo de documentos. """
    path = "NUMEROS_TIPO_DOC"

    def __init__(self, api, id_tipo_documento, ano=date.today().year):
        self.api = api
        self.ano = ano
        self.id_tipo_doc = id_tipo_documento

    def gerar_numero_processo(self):
        """
        Gera o próximo número de processo a ser usado, formado de acordo com a mascara do tipo de documento.

        :rtype : str
        :return: Retorna o NUM_PROCESSO gerado a partir da lógica de negócio
        """
        try:
            mascara = self.__obter_mascara()

            if mascara == "pNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("P")

            elif mascara == "eNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("e")

            elif mascara == "xNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("x")

            elif mascara == "dNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("d")

            else:  # interpretar a mascara
                # TODO Criar parser para mascara para entender como gerar o numero do processo de modo generico
                return NotImplementedError
            return numero
        except Exception as e:
            current.session.flash = "Erro ao gerar numero de processo."
            raise e

    def reverter_ultimo_numero_processo(self):  # TODO testar isso
        """ Reverte a geração do último numero de processo. """

        params = {"ID_TIPO_DOC": self.id_tipo_doc, "ANO_TIPO_DOC": self.ano}
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]
        try:
            numero_tipo_doc = self.api.get(self.path, params, fields)
            numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] - 1
            try:
                self.__atualizar_total_numero_ultimo_documento(numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"], numero)
            except Exception as e:
                current.session.flash = "Erro ao reverter geração de numero de processo."
                raise e
        except ValueError as e:
            current.session.flash = "Não existem registros de numeros de processo para o tipo de documento " + str(self.id_tipo_doc)
            raise e

    def __obter_mascara(self):
        return self.api.get("TIPOS_DOCUMENTOS", {"ID_TIPO_DOC": self.id_tipo_doc}, ["MASCARA_TIPO_DOC"]).first()["MASCARA_TIPO_DOC"].strip() # strip é necessário pois máscara vem com whitespaces no final(pq???).

    def __proximo_numero_tipo_documento(self):
        """
        O método retorna qual será o próximo NUM_TIPO_DOC que será utilizado. Caso já exista
        uma entrada nesta tabela para o ANO_TIPO_DOC e ID_TIPO_DOC, retornará o ultimo número,
        caso contrário, uma nova entrada será criada.

        :rtype : int
        """

        params = {"ID_TIPO_DOC": self.id_tipo_doc, "ANO_TIPO_DOC": self.ano}
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]

        try:
            numero_tipo_doc = self.api.get(self.path, params, fields)
            id_numero_tipo_doc = numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"]
            numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] + 1
            try:
                self.__atualizar_total_numero_ultimo_documento(id_numero_tipo_doc, numero)
            except Exception as e:
                current.session.flash = "Erro ao gerir numeros de processo."
                raise e
        except ValueError:
            # caso não exista uma entrada na tabela, criar uma para começar a gerir a sequencia de numeros de processo para esse tipo de documento/ano
            self.__atualizar_indicadores_default()
            numero = self.__criar_novo_numero_tipo_documento()

        return numero

    def __atualizar_indicadores_default(self):
        """ O método atualiza todos os IND_DEFAULT para N para ID_TIPO_DOC da instãncia """

        # TODO checar se precisa do ano também como parametro aqui
        numeros_documentos = self.api.get(self.path, {"ID_TIPO_DOC": self.id_tipo_doc}, ["ID_NUMERO_TIPO_DOC"])
        for numero in numeros_documentos.content:
            self.api.put(
                self.path,
                {
                    "ID_NUMERO_TIPO_DOC": numero["ID_NUMERO_TIPO_DOC"],
                    "IND_DEFAULT": "N"
                }
            )

    def __atualizar_total_numero_ultimo_documento(self, id_numero_tipo_documento, numero):
        """ Atualiza o contador/sequence do numero de processo do tipo de documento especificado
        :param id_numero_tipo_documento: id do tipo de documento
        :param numero: valor a ser assinalado
        """

        self.api.put(
            self.path,
            {
                "ID_NUMERO_TIPO_DOC": id_numero_tipo_documento,
                "NUM_ULTIMO_DOC": numero
            }
        )

    def __criar_novo_numero_tipo_documento(self):
        """
        num_ultimo_doc retorna 1 para que não seja necessário chamar novo método para atualizar

        :rtype : int
        :return: NUM_ULTIMO_DOC da inserção
        """
        num_ultimo_doc = 1
        params = {
            "ID_TIPO_DOC": self.id_tipo_doc,
            "ANO_TIPO_DOC": self.ano,
            "IND_DEFAULT": "S",
            "NUM_ULTIMO_DOC": num_ultimo_doc
        }
        self.api.post(self.path, params)
        return num_ultimo_doc

    @deprecated
    def __gera_numero_processo_projeto(self, tipo):
        """ Codigo especifico para gerar numero de processo de projetos
            OBS: esse metodo é temporario. Deve-se usar o parser generico. """
        num_ultimo_doc = str(self.__proximo_numero_tipo_documento()).zfill(4)  # NNNN
        num_processo =  tipo + ("%s/%d" % (num_ultimo_doc, self.ano))  # _NNNN/AAAA
        return num_processo
