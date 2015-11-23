# coding=utf-8

from datetime import date, timedelta
from time import strftime
from deprecate import deprecated

from sie import SIE, SIEException
from unirio.api.exceptions import APIException

__all__ = [
    "SIEDocumentoDAO",
]


class SIEDocumentoDAO(SIE):

    # ******************************** Constantes ***********************************
    # Valores de prioridade de documento

    TRAMITACAO_PRIORIDADE_NORMAL = 2

    # Valores validos para SITUACAO_TRAMIT

    TRAMITACAO_SITUACAO_AGUARDANDO = "T"
    TRAMITACAO_SITUACAO_ENTREGUE = "E"
    TRAMITACAO_SITUACAO_RECEBIDO = "R"

    # Valores validos para IND_RETORNO_OBRIG

    TRAMITACAO_IND_RETORNO_OBRIG_SIM = "S"
    TRAMITACAO_IND_RETORNO_OBRIG_NAO = "N"
    TRAMITACAO_IND_RETORNO_OBRIG_CONFORME_FLUXO = "F"

    # Paths para busca na api

    path = "DOCUMENTOS"
    """ Caminho da API para trabalhar com documentos """

    tramite_path = "TRAMITACOES"
    """ Caminho da API para trabalhar com tramitacoes """

    fluxo_path = "FLUXOS"
    """ Caminho da API para trabalhar com fluxos de tramitacoes """

    # *******************************************************************************

    def __init__(self):
        super(SIEDocumentoDAO, self).__init__()

    def criar_documento(self, operador, novo_documento_params):
        """
        Inclui um novo documento eletronico do SIE e retorna ele. Uma tramitacao inicial ja eh iniciada (exceto se for especificado sem_tramite=True).

        Notas:
        SITUACAO_ATUAL = 1      => Um novo documento sempre se inicia com 1
        TIPO_PROPRIETARIO = 20  => Indica restricao de usuarios
        TIPO_ORIGEM = 20        => Recebe mesmo valor de TIPO_PROPRIETARIO
        SEQUENCIA = 1           => Indica que eh o primeiro passo de tramitacao
        TIPO_PROCEDENCIA = S    => Indica servidor
        TIPO_INTERESSADO = S    => Indica servidor

        IND_ELIMINADO, IND_AGENDAMENTO, IND_RESERVADO,
        IND_EXTRAVIADO, TEMPO_ESTIMADO => Valores fixos (Seguimos documento com recomendacoes da sintese)

        :param novo_documento_params: Um dicionario contendo parametros para criar o documento.
        :type novo_documento_params: dict

        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict

        :return: Um dicionario contendo a entrada da tabela DOCUMENTOS correspondente ao documento criado.
        :rtype: dict
        """

        num_processo_handler = _NumProcessoHandler(self.api, novo_documento_params["ID_TIPO_DOC"], operador)

        # determinando ultimo numero
        num_processo = num_processo_handler.gerar_numero_processo()

        if not novo_documento_params.get("NUM_PROCESSO", None):
            novo_documento_params.update({"NUM_PROCESSO": num_processo})

        try:
            id_documento = self.api.post(self.path, novo_documento_params).insertId
            novo_documento = self.api.get_single_result(self.path, {"ID_DOCUMENTO": id_documento})

            # criando entrada na tabela de tramitacoes (pre-etapa)
            self.__adiciona_registro_inicial_tramitacao(novo_documento)

        except APIException as e:
            num_processo_handler.reverter_ultimo_numero_processo()
            raise e

        return novo_documento

    def obter_documento(self, id_documento):
        """
        Retorna o documento com o id especificado. Caso nao exista, retorna None

        :param id_documento: Identificador unico de uma entrada na tabela DOCUMENTOS
        :type id_documento: int
        :return: Uma dicionario correspondente a uma entrada da tabela DOCUMENTOS
        :rtype: dict
        """
        params = {"ID_DOCUMENTO": id_documento}
        return self.api.get_single_result(self.path, params, cache_time=self.cacheTime)

    def remover_documento(self, documento):
        """
        Dada uma entrada na tabela de DOCUMENTOS, a funcao remove suas tramitacoes e o documento em si

        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        """
        self.remover_tramitacoes(documento)
        response = self.api.delete(self.path, {'ID_DOCUMENTO': documento['ID_DOCUMENTO']})
        if response.affectedRows > 0:
            del documento

    def tramitar_documento(self, operador, documento, fluxo, resolvedor_destino=None):
        """
        Envia o documento seguindo o fluxo especificado.
        Caso o fluxo especificado tenha a flag IND_QUERY='S', ou seja, o tipo_destino e id_destino devem ser obtidos atraves de uma query adicional, eh necessario o especificar o parametro resolvedor_destino com um callable que retorna o TIPO_DESTINO e ID_DESTINO corretos.

        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :param fluxo: Um dicionario referente a uma entrada na tabela FLUXOS
        :type fluxo: dict
        :param resolvedor_destino: Um callable que recebe um parametro "fluxo" e retorna uma tupla (tipo_destino, id_destino)
        :type resolvedor_destino: callable
        """
        # No SIE, tramitar documento eh atualizar a situacao da tramitacao (e outros campos) e definir o fluxo dela
        self._marcar_tramitacao_atual_entregue(operador, documento, fluxo, resolvedor_destino)

    def receber_documento(self, operador, documento):
        """
        Marca o documento como recebido pela instituicao destinataria da tramitacao atual do documento.
        Normalmente esse metodo deve ser usado para emular a abertura da tramitacao atraves da caixa postal do SIE.

        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        """
        self._marcar_tramitacao_atual_recebida(operador, documento)
        self._criar_registro_tramitacao(operador, documento)

    def atualizar_situacao_documento(self, operador, documento, fluxo):
        """
        Atualiza o documento na tabela com os dados do fluxo especificado. Normalmente chamado apos uma tramitacao for concluida.

        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :param fluxo: Um dicionario referente a uma entrada na tabela FLUXOS
        :type fluxo: dict
         """
        documento_atualizado = {
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "SITUACAO_ATUAL": fluxo["SITUACAO_FUTURA"],
            "COD_OPERADOR": operador["ID_USUARIO"],
            "DT_ALTERACAO": date.today(),
            "HR_ALTERACAO": strftime("%H:%M:%S"),
            "CONCORRENCIA": documento["CONCORRENCIA"] + 1
        }
        self.api.put(self.path, documento_atualizado)

    # ========================= Tramitacao ===================================

    def __adiciona_registro_inicial_tramitacao(self, documento):
        """
        Cria um registro na tabela de tramitacoes para esse documento recem-criado.

        Deve ser feito antes de fazer a primeira tramitacao do documento (de preferencia ao criar o documento)

        :rtype: dict
        :return: Um dicionario equivalente a uma entrada da tabela TRAMITACOES
        """

        tramitacao_params = {
            "SEQUENCIA": 1,  # Primeiro passo da tramitacao
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "TIPO_ORIGEM": documento["TIPO_PROPRIETARIO"],
            "ID_ORIGEM": documento["ID_PROPRIETARIO"],
            "TIPO_DESTINO": documento["TIPO_PROPRIETARIO"],
            "ID_DESTINO": documento["ID_PROPRIETARIO"],
            "DT_ENVIO": date.today(),
            "SITUACAO_TRAMIT": SIEDocumentoDAO.TRAMITACAO_SITUACAO_AGUARDANDO,
            "IND_RETORNO_OBRIG": SIEDocumentoDAO.TRAMITACAO_IND_RETORNO_OBRIG_NAO,
            "COD_OPERADOR": documento["COD_OPERADOR"],
            "DT_ALTERACAO": date.today(),
            "HR_ALTERACAO": strftime("%H:%M:%S"),
            "CONCORRENCIA": 0,
            "PRIORIDADE_TAB": 5101,  # Tabela estruturada utilizada para indicar o nivel de prioridade
            "PRIORIDADE_ITEM": SIEDocumentoDAO.TRAMITACAO_PRIORIDADE_NORMAL
        }

        id_tramitacao = self.api.post(self.tramite_path, tramitacao_params).insertId
        tramitacao = self.api.get_single_result(self.tramite_path, {"ID_TRAMITACAO": id_tramitacao})

        return tramitacao

    def _criar_registro_tramitacao(self, operador, documento):
        """
        Cria um registro novo na tabela de tramitacoes para esse documento.

        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :return: Retorna a linha de tramitacao recem criada
        :rtype: dict
        :raises: SIEException
        """

        # pegar a mais recente do documento
        tramitacao_anterior = self.obter_tramitacao_atual(documento)

        # so deveriamos criar um registro novo caso a tramitacao anterior estiver no estado SIEDocumentoDAO.TRAMITACAO_SITUACAO_RECEBIDO
        # essa restricao pode conflitar com dados antigos e incosistentes
        if tramitacao_anterior["SITUACAO_TRAMIT"] != SIEDocumentoDAO.TRAMITACAO_SITUACAO_RECEBIDO:
            raise SIEException("Tramitacao anterior ainda nao foi processada")

        tramitacao_params = {
            "SEQUENCIA": tramitacao_anterior["SEQUENCIA"] + 1,
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "TIPO_ORIGEM": documento["TIPO_PROPRIETARIO"],
            "ID_ORIGEM": documento["ID_PROPRIETARIO"],
            "TIPO_DESTINO": documento["TIPO_PROPRIETARIO"],
            "ID_DESTINO": documento["ID_PROPRIETARIO"],
            "DT_ENVIO": date.today(),
            "SITUACAO_TRAMIT": SIEDocumentoDAO.TRAMITACAO_SITUACAO_AGUARDANDO,
            "IND_RETORNO_OBRIG": SIEDocumentoDAO.TRAMITACAO_IND_RETORNO_OBRIG_NAO,
            "COD_OPERADOR": operador["ID_USUARIO"],
            "DT_ALTERACAO": date.today(),
            "HR_ALTERACAO": strftime("%H:%M:%S"),
            "CONCORRENCIA": 0,
            "PRIORIDADE_TAB": 5101,
            "PRIORIDADE_ITEM": SIEDocumentoDAO.TRAMITACAO_PRIORIDADE_NORMAL
        }

        id_tramitacao = self.api.post(self.tramite_path, tramitacao_params).insertId
        tramitacao = self.api.get_single_result(self.tramite_path, {"ID_TRAMITACAO": id_tramitacao})  # pega uma instancia nova do banco (por seguranca)

        return tramitacao

    def _marcar_tramitacao_atual_entregue(self, operador, documento, fluxo, resolvedor_destino=None):
        """
        Marca a tramitacao atual como entregue, atualiza os campos necessarios e define o fluxo especificado na tramitacao.

        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :param fluxo: Um dicionario referente a uma entrada na tabela FLUXOS
        :type fluxo: dict
        :param resolvedor_destino: eh um callable que resolve o destino dado um fluxo que tenha a flag IND_QUERY='S', ou seja, o tipo_destino e id_destino devem ser obtidos atraves de uma query adicional. O retorno deve ser uma tupla (tipo_destino, id_destino).
        :type resolvedor_destino: callable
        :raises: SIEException
        """

        try:
            # Pega a tramitacao atual
            tramitacao = self.obter_tramitacao_atual(documento)  # Espera uma linha de tramitacao com status 'T'
            funcionario = operador

            if self.__is_destino_fluxo_definido_externamente(fluxo):
                if not resolvedor_destino:
                    raise SIEException("Nao eh possivel tramitar um documento atraves de um fluxo que possui a flag IND_QUERY='S' sem ter especificado uma callable para resolver o destino (id/tipo)")

                tipo_destino, id_destino = resolvedor_destino(fluxo)
                fluxo.update({'TIPO_DESTINO': tipo_destino, 'ID_DESTINO': id_destino})

            # atualizando a tramitacao
            tramitacao.update({
                "TIPO_DESTINO": fluxo["TIPO_DESTINO"],
                "ID_DESTINO": fluxo["ID_DESTINO"],
                "DT_ENVIO": date.today(),
                "DT_VALIDADE": self.__calcular_data_validade(date.today(), fluxo["NUM_DIAS"]),
                "DESPACHO": fluxo["TEXTO_DESPACHO"],
                "DESPACHO_RTF": fluxo["TEXTO_DESPACHO"],
                "SITUACAO_TRAMIT": SIEDocumentoDAO.TRAMITACAO_SITUACAO_ENTREGUE,
                "IND_RETORNO_OBRIG": SIEDocumentoDAO.TRAMITACAO_IND_RETORNO_OBRIG_CONFORME_FLUXO,
                "ID_FLUXO": fluxo["ID_FLUXO"],
                "COD_OPERADOR": funcionario["ID_USUARIO"],
                "DT_ALTERACAO": date.today(),
                "HR_ALTERACAO": strftime("%H:%M:%S"),
                "CONCORRENCIA": tramitacao["CONCORRENCIA"] + 1,
                "ID_USUARIO_INFO": funcionario["ID_USUARIO"],
                "DT_DESPACHO": date.today(),
                "HR_DESPACHO": strftime("%H:%M:%S"),
                "ID_APLIC_ACAO": fluxo["ID_APLIC_ACAO"]
            })

            self.api.put(self.tramite_path, tramitacao)

            try:
                self.atualizar_situacao_documento(operador, documento, fluxo)
            except APIException as e:
                raise SIEException("Nao foi possivel atualizar o documento", e)

        except (APIException, SIEException) as e:
            raise SIEException("Nao foi possivel tramitar o documento", e)

    def _marcar_tramitacao_atual_recebida(self, operador, documento):
        """
        Marca o documento como recebido na tramitacao atual do documento
        Esse metodo deve ser usado para emular a abertura da tramitacao atraves da caixa postal do SIE.

        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :raises: SIEException
        """
        try:
            # Pega a tramitacao atual
            tramitacao = self.obter_tramitacao_atual(documento)
            tramitacao.update({
                "SITUACAO_TRAMIT": SIEDocumentoDAO.TRAMITACAO_SITUACAO_RECEBIDO,
                "COD_OPERADOR": operador["ID_USUARIO"],
                "DT_ALTERACAO": date.today(),
                "HR_ALTERACAO": strftime("%H:%M:%S"),
                "CONCORRENCIA": tramitacao["CONCORRENCIA"] + 1
            })

            self.api.put(self.tramite_path, tramitacao)

        except (APIException, SIEException) as e:
            raise SIEException("Nao foi possivel tramitar o documento", e)

    def obter_tramitacao_atual(self, documento):
        """
        Retorna a tramitacao atual (mais recente) do documento.
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :return: Uma dicionario correspondente a uma entrada da tabela TRAMITACOES
        :rtype : dict
        :raises: SIEException
        """
        try:
            params = {
                "ID_DOCUMENTO": documento['ID_DOCUMENTO'],
                "ORDERBY": "ID_TRAMITACAO",
                "SORT": "DESC"
            }
            # Pega a tramitacao atual
            tramitacao = self.api.get_single_result(self.tramite_path, params)
        except APIException as e:
            raise SIEException("Nao foi possivel obter tramitacao", e)

        return tramitacao

    def remover_tramitacoes(self, documento):
        """
        Dado um documento, a funcao busca e remove suas tramitacoes. Use com cautela.
        
        :type documento: dict
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :raises: SIEException
        """
        try:
            tramitacoes = self.api.get(self.tramite_path, {"ID_DOCUMENTO": documento['ID_DOCUMENTO']}, ['ID_TRAMITACAO'])
            for tramitacao in tramitacoes.content:
                self.api.delete(self.tramite_path, {'ID_TRAMITACAO': tramitacao['ID_TRAMITACAO']})
        except APIException as e:
            print "Nenhuma tramitacao encontrada para o documento %d" % documento['ID_DOCUMENTO']
            raise e

    @staticmethod
    def __is_destino_fluxo_definido_externamente(fluxo):
        return fluxo['IND_QUERY'].strip() == 'S'

    # ========================= Fluxos ===================================

    def obter_fluxo_tramitacao_atual(self, documento):
        """
        Retorna o fluxo de tramitacao atual do documento especificado:

        SELECT F.* FROM FLUXOS F WHERE ID_FLUXO = (SELECT T.* FROM TRAMITACOES WHERE ID_DOCUMENTO = :ID_DOCUMENTO ORDER BY :ID_TRAMITACAO DESC LIMIT 1)

        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
        :type documento: dict
        :rtype : dict
        :return: Uma dicionario correspondente a uma entrada da tabela FLUXOS
        """

        # obter da tabela de tramitacoes pois o fluxo pode ter sido modificado ao longo do tempo
        # isso eh de contraste com obter da tabela de fluxos para termos as opcoes de fluxo mais atualizadas
        tramitacao_atual = self.obter_tramitacao_atual(documento)
        params = {"ID_FLUXO": tramitacao_atual["ID_FLUXO"]}
        return self.api.get_single_result(self.fluxo_path, params)

    def obter_proximos_fluxos_tramitacao_validos(self, documento):
        """
        Retorna os proximos fluxos de tramitacoes validos atualmente para o documento especificado
        :param documento: Um dicionario contendo uma entrada da tabela DOCUMENTOS
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
            "SITUACAO_ATUAL": 1,
            "IND_ATIVO": "S",
        }

        fluxos = self.api.get(self.fluxo_path, params, bypass_no_content_exception=True)

        if len(fluxos) == 0:
            raise SIEException("Nao foi possivel obter o fluxo inical para o tipo de documento especificado.")

        if len(fluxos) > 2:
            raise SIEException("Tipo de documento possui mais de um fluxo inicial definido. Escolha um manualmente.")

        return fluxos.first()

    @staticmethod
    def __calcular_data_validade(data, dias):
        """
        Autodocumentada.

        :type data: date
        :type dias: int
        :rtype: date
        :param data: Data incial
        :param dias: Quantidade de dias
        :return: Retorna a data enviada, acrescida da quantidade de dias
        """
        return data + timedelta(days=dias)


class _NumProcessoHandler(object):
    """ Classe helper para gerar os numeros de processo de documentos. """
    path = "NUMEROS_TIPO_DOC"

    def __init__(self, api, id_tipo_documento, operador, ano=date.today().year):
        """
        :param api: Instancia da API
        :type api: UNIRIOAPIRequest
        :param id_tipo_documento: ID do tipo de documento que esta se lidando
        :type id_tipo_documento: int
        :param operador: Um dicionario referente a uma entrada na view V_FUNCIONARIO_IDS. Corresponde ao operador do sistema.
        :type operador: dict
        :param ano:
        """
        self.api = api
        self.ano = ano
        self.operador = operador
        self.id_tipo_doc = id_tipo_documento

    def gerar_numero_processo(self):
        """
        Gera o proximo numero de processo a ser usado, formado de acordo com a mascara do tipo de documento.

        :rtype: str
        :return: Retorna o NUM_PROCESSO gerado a partir da logica de negocio
        :raise: SIEException
        """
        try:
            try:
                mascara = self.__obter_mascara()
            except APIException as e:
                raise SIEException("Erro obter mascara do tipo documento " + str(self.id_tipo_doc), e)

            if mascara == "pNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("P")

            elif mascara == "eNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("e")

            elif mascara == "xNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("x")

            elif mascara == "dNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                numero = self.__gera_numero_processo_projeto("d")

            elif mascara == "NNNNNN/AAAA":  # TODO usar um parser de mascar em vez dessa gambi
                numero = self.__gera_numero_processo_avaliacao_projeto()
            else:  # interpretar a mascara
                # TODO Criar parser para mascara para entender como gerar o numero do processo de modo generico
                return NotImplementedError
            return numero
        except Exception as e:
            raise SIEException("Erro ao gerar numero de processo.", e)

    def reverter_ultimo_numero_processo(self):
        """ Reverte a geracao do ultimo numero de processo. """

        params = {"ID_TIPO_DOC": self.id_tipo_doc, "ANO_TIPO_DOC": self.ano}
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]
        try:
            numero_tipo_doc = self.api.get_single_result(self.path, params, fields)
            numero = numero_tipo_doc["NUM_ULTIMO_DOC"] - 1
            try:
                self.__atualizar_total_numero_ultimo_documento(numero_tipo_doc, numero)
            except Exception as e:
                raise SIEException("Erro ao reverter geracao de numero de processo.", e)
        except ValueError as e:
            raise SIEException("Nao existem registros de numeros de processo para o tipo de documento " + str(self.id_tipo_doc), e)

    def __obter_mascara(self):
        return self.api.get_single_result("TIPOS_DOCUMENTOS", {"ID_TIPO_DOC": self.id_tipo_doc}, ["MASCARA_TIPO_DOC"])["MASCARA_TIPO_DOC"].strip()  # strip eh necessario pois mascara vem com whitespaces no final(pq???).

    def __proximo_numero_tipo_documento(self):
        """
        O metodo retorna qual sera o proximo NUM_TIPO_DOC que sera utilizado. Caso ja exista
        uma entrada nesta tabela para o ANO_TIPO_DOC e ID_TIPO_DOC, retornara o ultimo numero,
        caso contrario, uma nova entrada sera criada.

        :rtype: int
        :raises: SIEException
        """
        params = {"ID_TIPO_DOC": self.id_tipo_doc, "ANO_TIPO_DOC": self.ano}
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC", "CONCORRENCIA"]

        try:
            numero_tipo_doc = self.api.get_single_result(self.path, params, fields)
            numero = numero_tipo_doc["NUM_ULTIMO_DOC"] + 1
            try:
                self.__atualizar_total_numero_ultimo_documento(numero_tipo_doc, numero)
            except Exception as e:
                raise SIEException("Erro ao gerir numeros de processo.", e)
        except ValueError:
            # caso nao exista uma entrada na tabela, criar uma para comecar a gerir a sequencia de numeros de processo para esse tipo de documento/ano
            self.__atualizar_indicadores_default()
            numero = self.__criar_novo_numero_tipo_documento()

        return numero

    def __atualizar_indicadores_default(self):
        """ O metodo atualiza todos os IND_DEFAULT para N para ID_TIPO_DOC da instancia """

        # TODO checar se precisa do ano tambem como parametro aqui
        numeros_documentos = self.api.get(self.path, {"ID_TIPO_DOC": self.id_tipo_doc}, ["ID_NUMERO_TIPO_DOC"])
        for numero in numeros_documentos.content:
            self.api.put(
                self.path,
                {
                    "ID_NUMERO_TIPO_DOC": numero["ID_NUMERO_TIPO_DOC"],
                    "IND_DEFAULT": "N"
                }
            )

    def __atualizar_total_numero_ultimo_documento(self, numero_tipo_documento, numero):
        """
        Atualiza o contador/sequence do numero de processo do tipo de documento especificado.

        :param numero_tipo_documento: linha da tabela NUMEROS_TIPO_DOC
        :type numero_tipo_documento: dict
        :param numero: valor a ser assinalado
        :type numero: int
        :rtype: None
        """
        id_numero_tipo_documento = numero_tipo_documento["ID_NUMERO_TIPO_DOC"]
        params = {
            "ID_NUMERO_TIPO_DOC": id_numero_tipo_documento,
            "NUM_ULTIMO_DOC": numero,
            "COD_OPERADOR": self.operador,
            "DT_ALTERACAO": date.today(),
            "HR_ALTERACAO": strftime("%H:%M:%S"),
            "CONCORRENCIA": numero_tipo_documento["CONCORRENCIA"] + 1
        }
        self.api.put(self.path, params)

    def __criar_novo_numero_tipo_documento(self):
        """
        Cria uma nova linha na tabela para o tipo de documento usado.
        Nela ficara o contador/sequence do numero de processo do tipo de documento especificado.

        :rtype : int
        :return: NUM_ULTIMO_DOC da insercao
        """
        # num_ultimo_doc retorna 1 para que nao seja necessario chamar novo metodo para atualizar
        num_ultimo_doc = 1
        params = {
            "ID_TIPO_DOC": self.id_tipo_doc,
            "ANO_TIPO_DOC": self.ano,
            "IND_DEFAULT": "S",
            "NUM_ULTIMO_DOC": num_ultimo_doc,
            "COD_OPERADOR": self.operador,
            "DT_ALTERACAO": date.today(),
            "HR_ALTERACAO": strftime("%H:%M:%S"),
            "CONCORRENCIA": 0
        }
        self.api.post(self.path, params)
        return num_ultimo_doc

    @deprecated
    def __gera_numero_processo_projeto(self, tipo):
        """ Codigo especifico para gerar numero de processo de projetos
            OBS: esse metodo eh temporario. Deve-se usar o parser generico. """
        num_ultimo_doc = str(self.__proximo_numero_tipo_documento()).zfill(4)  # NNNN
        num_processo = tipo + ("%s/%d" % (num_ultimo_doc, self.ano))  # _NNNN/AAAA
        return num_processo

    @deprecated
    def __gera_numero_processo_avaliacao_projeto(self):
        """ Codigo especifico para gerar numero de processo de avaliacoes de projeto
            OBS: esse metodo eh temporario. Deve-se usar o parser generico. """
        num_ultimo_doc = str(self.__proximo_numero_tipo_documento()).zfill(6)  # NNNNNN
        num_processo = "%s/%d" % (num_ultimo_doc, self.ano)  # NNNNNN/AAAA
        return num_processo
