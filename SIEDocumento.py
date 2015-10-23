# coding=utf-8

from datetime import date, timedelta
from time import strftime
from gluon import current
from deprecate import deprecated

from sie import SIE


__all__ = [
    "SIEDocumentoDAO",
    "SIETramitacoes",
    "SIEFluxos"
]


class SIEDocumentoDAO(SIE):
    # ID_TIPO_DOC = 215

    def __init__(self):
        super(SIEDocumentoDAO, self).__init__()
        self.path = "DOCUMENTOS"

    def criar_documento(self, id_tipo_doc, funcionario, sem_tramite=False):
        """
        Inclui um novo documento eletronico do SIE e retorna ele. Uma tramitação inicial já é iniciada (exceto se for especificado sem_tramite=True).

        SITUACAO_ATUAL = 1      => Um novo documento sempre se inicia com 1
        TIPO_PROPRIETARIO = 20  => Indica restrição de usuários
        TIPO_ORIGEM = 20        => Recebe mesmo valor de TIPO_PROPRIETARIO
        SEQUENCIA = 1           => Indica que é o primeiro passo de tramitação
        TIPO_PROCEDENCIA = S    => Indica servidor
        TIPO_INTERESSADO = S    => Indica servidor

        IND_ELIMINADO, IND_AGENDAMENTO, IND_RESERVADO,
        IND_EXTRAVIADO, TEMPO_ESTIMADO => Valores fixos (Seguimos documento com recomendações da síntese)

        :param id_tipo_doc: O id do tipo de documento. (Informação na tabela TIPOS_DOCUMENTOS)
        :type  id_tipo_doc: int

        :param funcionario: Um dicionário referente a uma entrada na view V_FUNCIONARIO_IDS
        :type  funcionario: dict

        :param sem_tramite: Flag para indicar se é para ignorar a criação de um tramite inicial.
        :type  sem_tramite: bool

        :rtype : dict
        :return: Um dicionário contendo a entrada da tabela DOCUMENTOS correspondente ao documento criado.
        """

        params = {"ID_TIPO_DOC": id_tipo_doc, "ANO_TIPO_DOC": date.today().year}
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]

        num_processo_handler = self._NumProcessoHandler(self, date.today().year, id_tipo_doc)

        # determinando ultimo numero

        # num_processo = self._NumProcessoAux(self, current.session.edicao.dt_inicial_projeto.year, id_tipo_doc).gerar_numero_processo()
        num_processo = num_processo_handler.gerar_numero_processo()

        novo_documento = {
            "ID_TIPO_DOC": id_tipo_doc,
            "ID_PROCEDENCIA": funcionario["ID_CONTRATO_RH"],
            "ID_PROPRIETARIO": funcionario["ID_USUARIO"],
            "ID_CRIADOR": funcionario["ID_USUARIO"],
            "NUM_PROCESSO": num_processo,
            "TIPO_PROCEDENCIA": "S",
            "TIPO_INTERESSADO": "S",
            "ID_INTERESSADO": funcionario["ID_CONTRATO_RH"],
            "SITUACAO_ATUAL": 1,
            "TIPO_PROPRIETARIO": 20,
            "TIPO_ORIGEM": 20,
            "DT_CRIACAO": date.today(),
            "IND_ELIMINADO": "N",
            "IND_AGENDAMENTO": "N",
            "IND_RESERVADO": "N",
            "IND_EXTRAVIADO": "N",
            "TEMPO_ESTIMADO": 1,
            "SEQUENCIA": 1
        }

        # noinspection PyBroadException
        try:
            # cria o documento usando a API
            novo_documento = self.api.post(self.path, novo_documento)

            # atualiza id da instancia
            novo_documento.update({"ID_DOCUMENTO": novo_documento.insertId})

        except Exception as e:
            # TODO deletaNovoDocumento

            # TODO decrementar proximo_numero_tipo_documento
            num_processo_handler.reverter_ultimo_numero_processo()

            if not current.session.flash:
                current.session.flash = "Não foi possível criar um novo documento"
                raise e

        # se nao for para tramitar, paramos por aqui
        if sem_tramite:
            return novo_documento

        try:
            # obtendo um dao das tramitacoes
            dao_tramitacao = SIETramitacoes(novo_documento)

            # criando tramitacao
            nova_tramitacao = dao_tramitacao.criar_tramitacao()

            # tramitando o documento criando
            dao_tramitacao.tramitar_documento(
                nova_tramitacao,
                funcionario,
                SIEFluxos().get_fluxo_do_documento(novo_documento)
            )
            return novo_documento

        except Exception as e:
            session.flash = "Não foi possível criar uma tramitação para o documento %d" % novo_documento.insertId
            raise e

    def atualizar_situacao_documento(self, documento, fluxo):
        novo_documento = {
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "SITUACAO_ATUAL": fluxo["SITUACAO_FUTURA"]
        }
        self.api.put(self.path, novo_documento)

    def get_documento(self, id_documento):
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
        return self.api.get(self.path, params, cache_time=self.cacheTime).content[0]

    def remover_documento(self, documento):
        """
        Dada uma entrada na tabela de DOCUMENTOS, a função remove suas tramitações e o documento em si

        :type documento: dict
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        SIETramitacoes(documento).remover_tramitacoes()
        response = self.api.delete(self.path, {'ID_DOCUMENTO': documento['ID_DOCUMENTO']})
        if response.affectedRows > 0:
            del documento

    class _NumProcessoHandler(object):
        def __init__(self, dao, ano, id_tipo_documento):
            self.dao = dao
            self.ano = ano
            self.id_tipo_doc = id_tipo_documento
            self.path = "NUMEROS_TIPO_DOC"

        def gerar_numero_processo(self):
            """
            Gera o próximo número de processo a ser usado, formado de acordo com a mascara do tipo de documento.

            :rtype : str
            :return: Retorna o NUM_PROCESSO gerado a partir da lógica de negócio
            """
            try:
                mascara = self.dao.api.get("TIPOS_DOCUMENTOS", {"ID_TIPO_DOC": self.id_tipo_doc}, ["MASCARA_TIPO_DOC"]).content[0]["MASCARA_TIPO_DOC"]

                if mascara == "pNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                    self.__gera_numero_processo_projeto("p")

                elif mascara == "eNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                    self.__gera_numero_processo_projeto("e")

                elif mascara == "xNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                    self.__gera_numero_processo_projeto("x")

                elif mascara == "dNNNN/AAAA":  # TODO usar o parser de mascara ao inves dessa gambi
                    self.__gera_numero_processo_projeto("d")

                else:  # interpretar a mascara
                    # TODO Criar parser para mascara para entender como gerar o numero do processo de modo generico
                    return None

            except Exception as e:
                current.session.flash = "Erro ao gerir numeros de processo."
                raise e

        def reverter_ultimo_numero_processo(self):  # TODO testar isso
            """ Reverte a geração do último numero de processo. """

            params = {"ID_TIPO_DOC": self.id_tipo_doc, "ANO_TIPO_DOC": self.ano}
            fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]
            try:
                numero_tipo_doc = self.dao.api.get(self.path, params, fields)
                numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] - 1
                try:
                    self.__atualizar_total_numero_ultimo_documento(numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"], numero)
                except Exception as e:
                    current.session.flash = "Erro ao reverter geração de numero de processo."
                    raise e
            except ValueError as e:
                current.session.flash = "Não existem registros de numeros de processo para o tipo de documento " + str(self.id_tipo_doc)
                raise e

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
                numero_tipo_doc = self.dao.api.get(self.path, params, fields)
                id_numero_tipo_doc = numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"]
                numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] + 1
                try:
                    self.__atualizar_total_numero_ultimo_documento(id_numero_tipo_doc, numero)
                except Exception as e:
                    current.session.flash = "Erro ao gerir numeros de processo."
                    raise e
            except ValueError:
                self.__atualizar_indicadores_default()
                numero = self.__criar_novo_numero_tipo_documento()

            return numero

        def __atualizar_indicadores_default(self):
            """
            O método atualiza todos os IND_DEFAULT para N para ID_TIPO_DOC da instãncia

            """
            numeros_documentos = self.dao.api.get(self.path, {"ID_TIPO_DOC": self.id_tipo_doc}, ["ID_NUMERO_TIPO_DOC"])
            for numero in numeros_documentos.content:
                self.dao.api.put(
                    self.path,
                    {
                        "ID_NUMERO_TIPO_DOC": numero["ID_NUMERO_TIPO_DOC"],
                        "IND_DEFAULT": "N"
                    }
                )

        def __atualizar_total_numero_ultimo_documento(self, id_numero_tipo_documento, numero):
            self.dao.api.put(
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
            self.dao.api.post(self.path, params)
            return num_ultimo_doc

        @deprecated
        def __gera_numero_processo_projeto(self, tipo):
            """ Codigo especifico para gerar numero de processo de projetos
                OBS: esse metodo é temporario. Deve-se usar o parser generico. """
            num_ultimo_doc = str(self.__proximo_numero_tipo_documento()).zfill(4)  # NNNN
            return tipo + ("%s/%d" % (num_ultimo_doc, self.ano))  # _NNNN/AAAA


class SIETramitacoes(SIE):
    def __init__(self, documento):
        """
        :type documento: dict
        :param documento: Dicionário equivalente a uma entrada da tabela DOCUMENTOS
        """
        super(SIETramitacoes, self).__init__()
        self.path = "TRAMITACOES"
        self.documento = documento

    def criar_tramitacao(self):
        """
        SEQUENCIA = 1           => Primeiro passo da tramitação
        PRIORIDADE_TAB = 5101   => Tabela estruturada utilizada para indicar o nível de prioridade
        PRIORIDADE_ITEM = 2     => Prioridade normal
        SITUACAO_TRAMIT = T     => Indica que o documento não foi enviado ainda para tramitação (aguardando)
        IND_RETORNO_OBRIG = N   => Valor fixo, conforme documento da Síntese

        :rtype : dict
        :return: Um dicionário equivalente a uma entrada da tabela TRAMITACOES
        """
        tramitacao = {
            "SEQUENCIA": 1,
            "ID_DOCUMENTO": self.documento["ID_DOCUMENTO"],
            "TIPO_ORIGEM": self.documento["TIPO_PROPRIETARIO"],
            "ID_ORIGEM": self.documento["ID_PROPRIETARIO"],
            "TIPO_DESTINO": self.documento["TIPO_PROPRIETARIO"],
            "ID_DESTINO": self.documento["ID_PROPRIETARIO"],
            "DT_ENVIO": date.today(),
            "SITUACAO_TRAMIT": "T",
            "IND_RETORNO_OBRIG": "N",
            "PRIORIDADE_TAB": 5101,
        }

        tramitacao.update(
            {"ID_TRAMITACAO": self.api.post(self.path, tramitacao).insertId}
        )

        return tramitacao

    def _calcular_data_validade(self, data, dias):
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

    def tramitar_documento(self, tramitacao, funcionario, fluxo):
        """
        A regra de negócios diz que uma tramitação muda a situação atual de um documento para uma situação futura
        determinada pelo seu fluxo. Isso faz com que seja necessário que atulizemos as tabelas `TRAMITACOES` e
        `DOCUMENTOS`

        :type funcionario: dict
        :type tramitacao: dict
        :type fluxo: dict
        :param tramitacao: Um dicionário referente a uma entrada na tabela TRAMITACOES
        :param funcionario: Um dicionário referente a uma entrada na view V_FUNCIONARIO_IDS
        :param fluxo: Um dicionário referente a uma entrada na tabela FLUXOS

        :rtype : dict

        """
        try:
            nova_tramitacao = {
                "ID_TRAMITACAO": tramitacao["ID_TRAMITACAO"],
                "TIPO_DESTINO": fluxo["TIPO_DESTINO"],
                "ID_DESTINO": fluxo["ID_DESTINO"],
                "DT_ENVIO": date.today(),
                "DT_VALIDADE": self._calcular_data_validade(date.today(), fluxo["NUM_DIAS"]),
                "DESPACHO": fluxo["TEXTO_DESPACHO"],
                "SITUACAO_TRAMIT": "E",
                "ID_RETORNO_OBRIG": "F",
                "ID_FLUXO": fluxo["ID_FLUXO"],
                "ID_USUARIO_INFO": funcionario["ID_USUARIO"],
                "DT_DESPACHO": date.today(),
                "HR_DESPACHO": strftime("%H:%M:%S")
            }
            self.api.put(self.path, nova_tramitacao)
            try:
                SIEDocumentoDAO().atualizar_situacao_documento(self.documento, fluxo)
            except Exception:
                current.session.flash = "Não foi possível atualizar o documento"
        except Exception:
            if not current.session.flash:
                current.session.flash = "Não foi possível atualizar tramitação"

    def remover_tramitacoes(self):
        """
        Dado um documento, a função busca e remove suas tramitações.

        :param ID_DOCUMENTO: Identificador único de uma entrada na tabela DOCUMENTOS
        """
        try:
            tramitacoes = self.api.get(self.path, {"ID_DOCUMENTO": self.documento['ID_DOCUMENTO']}, ['ID_TRAMITACAO'])
            for tramitacao in tramitacoes.content:
                self.api.delete(self.path, {'ID_TRAMITACAO': tramitacao['ID_TRAMITACAO']})
        except ValueError:
            print "Nenhuma tramitação encontrada para o documento %d" % self.documento['ID_DOCUMENTO']


class SIEFluxos(SIE):
    # TODO escrever a documentação O que é um fluxo? O que essa classe faz?
    def __init__(self):
        """
        O fluxo é a movimentação de documentos durante uma tramitação.

        """
        super(SIEFluxos, self).__init__()
        self.path = "FLUXOS"

    def get_fluxo_do_documento(self, documento):
        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_ATUAL": documento["SITUACAO_ATUAL"],
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.get(self.path, params).content[0]

    def get_proximos_fluxos_do_documento(self, documento):
        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_FUTURA": documento["SITUACAO_FUTURA"],
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.get(self.path, params).content[0]
