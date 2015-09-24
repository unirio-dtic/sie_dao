# coding=utf-8
from datetime import date, timedelta
from time import strftime
from gluon import current
from deprecator import deprecate

from sie import SIE


__all__ = [
    "SIEDocumentos",
    "SIENumeroTipoDocumento",
    "SIETramitacoes",
    "SIEFluxos"
]


class SIEDocumentos(SIE):
    ID_TIPO_DOC = 215

    def __init__(self):
        super(SIEDocumentos, self).__init__()
        self.path = "DOCUMENTOS"

    @deprecate
    def proximoNumeroProcesso(self):
        """
        Número do processo é formado através da concatenação de um ID_TIPO_DOC, um sequencial e o ano do documento

        :rtype : str
        :return: Retorna o NUM_PROCESSO gerado a partir da lógica de negócio
        """
        ano = current.session.edicao.dt_inicial_projeto.year
        numeroTipoDoc = SIENumeroTipoDocumento(ano, self.ID_TIPO_DOC)

        NUM_ULTIMO_DOC = str(numeroTipoDoc.proximoNumeroTipoDocumento()).zfill(4)
        return "%d%s/%d" % (self.ID_TIPO_DOC, NUM_ULTIMO_DOC, ano)


    def criar_documento(self, tipo_doc, num_processo, funcionario):
        """
        SITUACAO_ATUAL = 1      => Um novo documento sempre se inicia com 1
        TIPO_PROPRIETARIO = 20  => Indica restrição de usuários
        TIPO_ORIGEM = 20        => Recebe mesmo valor de TIPO_PROPRIETARIO
        SEQUENCIA = 1           => Indica que é o primeiro passo de tramitação
        TIPO_PROCEDENCIA = S    => Indica servidor
        TIPO_INTERESSADO = S    => Indica servidor

        IND_ELIMINADO, IND_AGENDAMENTO, IND_RESERVADO,
        IND_EXTRAVIADO, TEMPO_ESTIMADO => Valores fixos (Seguimos documento com recomendações da síntese)

        :rtype : dict
        :return: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        documento = {
            "ID_TIPO_DOC": tipo_doc,
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
        try:
            novoDocumento = self.api.performPOSTRequest(self.path, documento)
            try:
                documento.update({"ID_DOCUMENTO": novoDocumento.insertId})
                tramitacao = SIETramitacoes(documento)
                novaTramitacao = tramitacao.criarTramitacao()

                tramitacao.tramitarDocumento(
                    novaTramitacao,
                    funcionario,
                    SIEFluxos().getFluxoFromDocumento(documento)
                )
                return documento

            except Exception as e:
                session.flash = "Não foi possível criar uma tramitação para o documento %d" % novoDocumento.insertId
                raise e
        except Exception:
            # TODO deletaNovoDocumento
            # TODO decrementar proximoNumeroTipoDocumento
            if not current.session.flash:
                current.session.flash = "Não foi possível criar um novo documento"

    @deprecate
    def criarDocumento(self, funcionario):
        """
        ID_TIPO_DOC = 215       => Projetos de Ensino
        SITUACAO_ATUAL = 1      => Um novo documento sempre se inicia com 1
        TIPO_PROPRIETARIO = 20  => Indica restrição de usuários
        TIPO_ORIGEM = 20        => Recebe mesmo valor de TIPO_PROPRIETARIO
        SEQUENCIA = 1           => Indica que é o primeiro passo de tramitação
        TIPO_PROCEDENCIA = S    => Indica servidor
        TIPO_INTERESSADO = S    => Indica servidor

        IND_ELIMINADO, IND_AGENDAMENTO, IND_RESERVADO,
        IND_EXTRAVIADO, TEMPO_ESTIMADO => Valores fixos (Seguimos documento com recomendações da síntese)

        :rtype : dict
        :return: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        documento = {
            "ID_TIPO_DOC": 215,
            "ID_PROCEDENCIA": funcionario["ID_CONTRATO_RH"],
            "ID_PROPRIETARIO": funcionario["ID_USUARIO"],
            "ID_CRIADOR": funcionario["ID_USUARIO"],
            "NUM_PROCESSO": self.proximoNumeroProcesso(),
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
        try:
            novoDocumento = self.api.performPOSTRequest(self.path, documento)
            try:
                documento.update({"ID_DOCUMENTO": novoDocumento.insertId})
                tramitacao = SIETramitacoes(documento)
                novaTramitacao = tramitacao.criarTramitacao()

                tramitacao.tramitarDocumento(
                    novaTramitacao,
                    funcionario,
                    SIEFluxos().getFluxoFromDocumento(documento)
                )
                return documento

            except Exception as e:
                session.flash = "Não foi possível criar uma tramitação para o documento %d" % novoDocumento.insertId
                raise e
        except Exception:
            # TODO deletaNovoDocumento
            # TODO decrementar proximoNumeroTipoDocumento
            if not current.session.flash:
                current.session.flash = "Não foi possível criar um novo documento"

    def atualizarSituacaoDocumento(self, documento, fluxo):
        novoDocumento = {
            "ID_DOCUMENTO": documento["ID_DOCUMENTO"],
            "SITUACAO_ATUAL": fluxo["SITUACAO_FUTURA"]
        }
        self.api.performPUTRequest(self.path, novoDocumento)

    def getDocumento(self, ID_DOCUMENTO):
        """

        :type ID_DOCUMENTO: int
        :param ID_DOCUMENTO: Identificador único de uma entrada na tabela DOCUMENTOS
        :rtype : dict
        :return: Uma dicionário correspondente a uma entrada da tabela DOCUMENTOS
        """
        params = {
            "ID_DOCUMENTO": ID_DOCUMENTO,
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.performGETRequest(self.path, params, cached=self.cacheTime).content[0]

    def removerDocumento(self, documento):
        """
        Dada uma entrada na tabela de DOCUMENTOS, a função remove suas tramitações e o documento em si

        :type documento: dict
        :param documento: Um dicionário contendo uma entrada da tabela DOCUMENTOS
        """
        SIETramitacoes(documento).removerTramitacoes()
        response = self.api.performDELETERequest(self.path, {'ID_DOCUMENTO': documento['ID_DOCUMENTO']})
        if response.affectedRows > 0:
            del documento

class SIENumeroTipoDocumento(SIE):
    def __init__(self, ano, ID_TIPO_DOC):
        super(SIENumeroTipoDocumento, self).__init__()
        self.path = "NUMEROS_TIPO_DOC"
        self.ano = ano
        self.ID_TIPO_DOC = ID_TIPO_DOC

    def proximoNumeroTipoDocumento(self):
        """
        O método retorna qual será o próximo NUM_TIPO_DOC que será utilizado. Caso já exista
        uma entrada neta tabela para o ANO_TIPO_DOC e ID_TIPO_DOC, retornará o ultimo número,
        caso contrário, uma nova entrada será criada.

        :rtype : int
        """
        params = {
            "ID_TIPO_DOC": self.ID_TIPO_DOC,
            "ANO_TIPO_DOC": self.ano
        }
        fields = ["ID_NUMERO_TIPO_DOC", "NUM_ULTIMO_DOC"]
        try:
            numero_tipo_doc = self.api.performGETRequest(self.path, params, fields)
            ID_NUMERO_TIPO_DOC = numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"]
            numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] + 1
            try:
                self.atualizarTotalNumeroUltimoDocumento(ID_NUMERO_TIPO_DOC, numero)
            except Exception as e:
                raise e
        except ValueError:
            self.atualizarIndicadoresDefault()
            numero = self.criarNovoNumeroTipoDocumento()

        return numero

    def atualizarIndicadoresDefault(self):
        """
        O método atualiza todos os IND_DEFAULT para N para ID_TIPO_DOC da instãncia

        """
        numerosDocumentos = self.api.performGETRequest(
            self.path,
            {"ID_TIPO_DOC": self.ID_TIPO_DOC},
            ["ID_NUMERO_TIPO_DOC"]
        )
        for numero in numerosDocumentos.content:
            self.api.performPUTRequest(
                self.path,
                {
                    "ID_NUMERO_TIPO_DOC": numero["ID_NUMERO_TIPO_DOC"],
                    "IND_DEFAULT": "N"
                }
            )

    def atualizarTotalNumeroUltimoDocumento(self, ID_NUMERO_TIPO_DOC, numero):
        self.api.performPUTRequest(
            self.path,
            {
                "ID_NUMERO_TIPO_DOC": ID_NUMERO_TIPO_DOC,
                "NUM_ULTIMO_DOC": numero
            }
        )

    def criarNovoNumeroTipoDocumento(self):
        """

        NUM_ULTIMO_DOC retorna 1 para que não seja necessário chamar novo método para atualizar
        :rtype : int
        :return: NUM_ULTIMO_DOC da inserção
        """
        NUM_ULTIMO_DOC = 1
        params = {
            "ID_TIPO_DOC": self.ID_TIPO_DOC,
            "ANO_TIPO_DOC": self.ano,
            "IND_DEFAULT": "S",
            "NUM_ULTIMO_DOC": NUM_ULTIMO_DOC
        }
        self.api.performPOSTRequest(self.path, params)
        return NUM_ULTIMO_DOC


class SIETramitacoes(SIE):
    def __init__(self, documento):
        """

        :type documento: dict
        :param documento: Dicionário equivalente a uma entrada da tabela DOCUMENTOS
        """
        super(SIETramitacoes, self).__init__()
        self.path = "TRAMITACOES"
        self.documento = documento

    def criarTramitacao(self):
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
            {"ID_TRAMITACAO": self.api.performPOSTRequest(self.path, tramitacao).insertId}
        )

        return tramitacao

    def _calcularDataValidade(self, data, dias):
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

    def tramitarDocumento(self, tramitacao, funcionario, fluxo):
        """
        A regra de negócios diz que uma tramitação muda a situação atual de um documento para uma situação futura
        determinada pelo seu fluxo. Isso faz com que seja necessário que atulizemos as tabelas `TRAMITACOES` e
        `DOCUMENTOS`

        :type funcionario: dict
        :type documento: dict
        :type tramitacao: dict
        :type fluxo: dict
        :param tramitacao: Um dicionário referente a uma entrada na tabela TRAMITACOES
        :param documento: Um dicionário referente a uma entrada na tabela DOCUMENTOS
        :param funcionario: Um dicionário referente a uma entrada na view V_FUNCIONARIO_IDS
        :param fluxo: Um dicionário referente a uma entrada na tabela FLUXOS

        :rtype : dict

        """
        try:
            novaTramitacao = {
                        "ID_TRAMITACAO": tramitacao["ID_TRAMITACAO"],
                        "TIPO_DESTINO": fluxo["TIPO_DESTINO"],
                        "ID_DESTINO": fluxo["ID_DESTINO"],
                        "DT_ENVIO": date.today(),
                        "DT_VALIDADE": self._calcularDataValidade(date.today(), fluxo["NUM_DIAS"]),
                        "DESPACHO": fluxo["TEXTO_DESPACHO"],
                        "SITUACAO_TRAMIT": "E",
                        "ID_RETORNO_OBRIG": "F",
                        "ID_FLUXO": fluxo["ID_FLUXO"],
                        "ID_USUARIO_INFO": funcionario["ID_USUARIO"],
                        "DT_DESPACHO": date.today(),
                        "HR_DESPACHO": strftime("%H:%M:%S")
            }
            self.api.performPUTRequest(self.path, novaTramitacao)
            try:
                SIEDocumentos().atualizarSituacaoDocumento(self.documento, fluxo)
            except Exception:
                current.session.flash = "Não foi possível atualizar o documento"
        except Exception:
            if not current.session.flash:
                current.session.flash = "Não foi possível atualizar tramitação"

    def removerTramitacoes(self):
        """
        Dado um documento, a função busca e remove suas tramitações.

        :param ID_DOCUMENTO: Identificador único de uma entrada na tabela DOCUMENTOS
        """
        try:
            tramitacoes = self.api.performGETRequest(self.path, {"ID_DOCUMENTO": self.documento['ID_DOCUMENTO']}, ['ID_TRAMITACAO'])
            for tramitacao in tramitacoes.content:
                self.api.performDELETERequest(self.path, {'ID_TRAMITACAO': tramitacao['ID_TRAMITACAO']})
        except ValueError:
            print "Nenhuma tramitação encontrada para o documento %d" % self.documento['ID_DOCUMENTO']


class SIEFluxos(SIE):
    #TODO escrever a documentação O que é um fluxo? O que essa classe faz?
    def __init__(self):
        """
        O fluxo é a movimentação de documentos durante uma tramitação.

        """
        super(SIEFluxos, self).__init__()
        self.path = "FLUXOS"

    def getFluxoFromDocumento(self, documento):
        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_ATUAL": documento["SITUACAO_ATUAL"],
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.performGETRequest(self.path, params).content[0]

    def getProximosFluxosFromDocumento(self, documento):
        params = {
            "ID_TIPO_DOC": documento["ID_TIPO_DOC"],
            "SITUACAO_FUTURA": documento["SITUACAO_FUTURA"],
            "IND_ATIVO": "S",
            "LMIN": 0,
            "LMAX": 1
        }
        return self.api.performGETRequest(self.path, params).content[0]