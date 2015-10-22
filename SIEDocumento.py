# coding=utf-8

from datetime import date, timedelta
from time import strftime
from gluon import current
from deprecate import deprecated

from sie import SIE


__all__ = [
    "SIEDocumentos",
    "SIENumeroTipoDocumento",
    "SIETramitacoes",
    "SIEFluxos"
]


class SIEDocumentos(SIE):
    # ID_TIPO_DOC = 215

    def __init__(self):
        super(SIEDocumentos, self).__init__()
        self.path = "DOCUMENTOS"

    @deprecated
    def proximoNumeroProcesso(self):
        """
        Número do processo é formado através da concatenação de um ID_TIPO_DOC, um sequencial e o ano do documento

        :rtype : str
        :return: Retorna o NUM_PROCESSO gerado a partir da lógica de negócio
        """
        ano = current.session.edicao.dt_inicial_projeto.year
        numeroTipoDoc = SIENumeroTipoDocumento(ano, 215)

        NUM_ULTIMO_DOC = str(numeroTipoDoc.proximo_numero_tipo_documento()).zfill(4)
        return "%d%s/%d" % (215, NUM_ULTIMO_DOC, ano)

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
            novo_documento = self.api.post(self.path, documento)
            try:
                documento.update({"ID_DOCUMENTO": novo_documento.insertId})
                dao_tramitacao = SIETramitacoes(documento)
                nova_tramitacao = dao_tramitacao.criar_tramitacao()

                dao_tramitacao.tramitar_documento(
                    nova_tramitacao,
                    funcionario,
                    SIEFluxos().get_fluxo_do_documento(documento)
                )
                return documento

            except Exception as e:
                session.flash = "Não foi possível criar uma tramitação para o documento %d" % novo_documento.insertId
                raise e
        except Exception:
            # TODO deletaNovoDocumento
            # TODO decrementar proximo_numero_tipo_documento
            if not current.session.flash:
                current.session.flash = "Não foi possível criar um novo documento"

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


class SIENumeroTipoDocumento(SIE):
    def __init__(self, ano, id_tipo_documento):
        super(SIENumeroTipoDocumento, self).__init__()
        self.path = "NUMEROS_TIPO_DOC"
        self.ano = ano
        self.ID_TIPO_DOC = id_tipo_documento

    def proximo_numero_tipo_documento(self):
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
            numero_tipo_doc = self.api.get(self.path, params, fields)
            id_numero_tipo_doc = numero_tipo_doc.content[0]["ID_NUMERO_TIPO_DOC"]
            numero = numero_tipo_doc.content[0]["NUM_ULTIMO_DOC"] + 1
            try:
                self.atualizar_total_numero_ultimo_documento(id_numero_tipo_doc, numero)
            except Exception as e:
                raise e
        except ValueError:
            self.atualizar_indicadores_default()
            numero = self.criar_novo_numero_tipo_documento()

        return numero

    def atualizar_indicadores_default(self):
        """
        O método atualiza todos os IND_DEFAULT para N para ID_TIPO_DOC da instãncia

        """
        numeros_documentos = self.api.get(
            self.path,
            {"ID_TIPO_DOC": self.ID_TIPO_DOC},
            ["ID_NUMERO_TIPO_DOC"]
        )
        for numero in numeros_documentos.content:
            self.api.put(
                self.path,
                {
                    "ID_NUMERO_TIPO_DOC": numero["ID_NUMERO_TIPO_DOC"],
                    "IND_DEFAULT": "N"
                }
            )

    def atualizar_total_numero_ultimo_documento(self, id_numero_tipo_documento, numero):
        self.api.put(
            self.path,
            {
                "ID_NUMERO_TIPO_DOC": id_numero_tipo_documento,
                "NUM_ULTIMO_DOC": numero
            }
        )

    def criar_novo_numero_tipo_documento(self):
        """
        num_ultimo_doc retorna 1 para que não seja necessário chamar novo método para atualizar

        :rtype : int
        :return: NUM_ULTIMO_DOC da inserção
        """
        num_ultimo_doc = 1
        params = {
            "ID_TIPO_DOC": self.ID_TIPO_DOC,
            "ANO_TIPO_DOC": self.ano,
            "IND_DEFAULT": "S",
            "NUM_ULTIMO_DOC": num_ultimo_doc
        }
        self.api.post(self.path, params)
        return num_ultimo_doc


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
                SIEDocumentos().atualizar_situacao_documento(self.documento, fluxo)
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
