# -*- coding: utf-8 -*-
from unirio.api.exceptions import APIException, NoContentException
from sie.SIETabEstruturada import SIETabEstruturada
from sie.SIEProjetos import SIEProjetos, SIEParticipantesProjs, SIEArquivosProj, SIEOrgaosProjetos
from sie.SIEDocumento import SIEDocumentos, SIENumeroTipoDocumento
from sie.sie_utils import campos_sie_lower
from pydal.objects import Row
from datetime import date, datetime


class SIEProjetosPesquisa(SIEProjetos):
    """
    Classe que representa os projetos de pesquisa
    """

    COD_TABELA_FUNDACOES = 6025  # Fundações
    COD_TABELA_FUNCOES_PROJ = 6003  # Funções Projeto
    COD_TABELA_FUNCOES_ORGAOS = 6006
    COD_TABELA_TITULACAO = 168  # Titulação
    COD_TABELA_TIPO_EVENTO = 6028  # => Tipos de Eventos
    COD_TABELA_TIPO_PUBLICO_ALVO = 6002  # => Público alvo
    COD_TABELA_AVALIACAO_PROJETOS_INSTITUICAO = 6010  # => Avaliação dos projetos da Instituição
    COD_TABELA_SITUACAO = 6011

    ITEM_FUNDACOES_NAO_SE_APLICA = 1  # => Não se aplica
    ITEM_TIPO_EVENTO_NAO_SE_APLICA = 1  # => Não se aplica
    ITEM_TIPO_PUBLICO_3_GRAU = 8  # => 3o grau
    ITEM_AVALIACAO_PROJETOS_INSTITUICAO_PENDENTE = 1  # => Não-avaliado
    ITEM_CLASSIFICACAO_PROJETO_PESQUISA = 39718
    ITEM_SITUACAO_TRAMITE_REGISTRO = 8
    # TODO Ter estes parâmetros HARD-CODED é uma limitação.
    ITEM_FUNCOES_PROJ_CANDIDATO_BOLSISTA = 50
    ITEM_FUNCOES_PROJ_DESCR = 0
    ITEM_FUNCOES_PROJ_COORDENADOR = 1
    ITEM_FUNCOES_PROJ_BOLSISTA = 3
    ITEM_FUNCOES_PROJ_NAO_DEFINIDA = 20

    ITEM_FUNCOES_ORGAOS_RESPONSAVEL = 5
    ITEM_FUNCOES_ORGAOS_AGENCIA_FOMENTO = 4
    ITEM_ESTADO_REGULAR = 1

    SITUACAO_ATIVO = 'A'
    ACESSO_PARTICIPANTES_APENAS_COORDENADOR = 'N'
    NAO_PAGA_BOLSA = 'N'

    def __init__(self):
        super(SIEProjetosPesquisa, self).__init__()
        self.TIPO_DOCUMENTO = 217

    def registrar_projeto(self, projeto, funcionario):
        novo_documento = self.criar_documento_projeto(funcionario)
        projeto.update({
            "ID_DOCUMENTO": novo_documento["ID_DOCUMENTO"],
            "NUM_PROCESSO": novo_documento["NUM_PROCESSO"],

        })

        # put PROJETO_ID

    def get_agencia_fomento(self, id_projeto):
        """

        :param id_projeto: int/string representando a id de um projeto do qual se quer a agência de fomento
        :return: None se não existe agencia de fomento para o projeto ou a "row" vinda do banco.
        """
        params = {
            'ID_PROJETO': id_projeto,
            'FUNCAO_ORG_ITEM': self.ITEM_FUNCOES_ORGAOS_AGENCIA_FOMENTO,
            'LMIN': 0,
            'LMAX': 1,
            'ORDERBY': 'ID_ORGAO_PROJETO ASC'
        }

        try:
            return self.api.get("V_PROJETOS_ORGAOS", params, cache_time=0).first()
        except NoContentException:
            return {}

    def get_projeto_as_row(self, id_projeto):
        """
        Este método retorna um dicionário contendo os dados referentes ao projeto convertidos para o formato compatível
        com o web2py.
        :param id_projeto: integer, id do projeto
        :return: gluon.pydal.objects.Row contendo as informações, None caso não exista projeto com a id informada/erro.
        """
        if id_projeto:
            projeto_bd = self.get_projeto(id_projeto)
            if projeto_bd:
                termo = SIEArquivosProj().get_termo_outorga(id_projeto)
                ata = SIEArquivosProj().get_ata_departamento(id_projeto)
                arquivo_proj = SIEArquivosProj().get_arquivo_projeto(id_projeto)
                agencia_fomento = self.get_agencia_fomento(id_projeto)

                projeto = {
                    'titulo': projeto_bd[u'TITULO'].encode('utf-8'),
                    'resumo': projeto_bd[u'RESUMO'].encode('utf-8'),
                    'keyword_1': projeto_bd[u'PALAVRA_CHAVE01'].encode('utf-8'),
                    'keyword_2': projeto_bd[u'PALAVRA_CHAVE02'].encode('utf-8'),
                    'keyword_3': projeto_bd[u'PALAVRA_CHAVE03'].encode('utf-8') if projeto_bd[
                                                                                       u'PALAVRA_CHAVE03'] is not None else "",
                    'keyword_4': projeto_bd[u'PALAVRA_CHAVE04'].encode('utf-8') if projeto_bd[
                                                                                       u'PALAVRA_CHAVE04'] is not None else "",
                    "financeiro_apoio_financeiro": bool(agencia_fomento),
                # TODO Lógica cheia de gambiarra de lidar com fundações.
                    "carga_horaria": projeto_bd[u'CARGA_HORARIA'],
                    "financeiro_termo_outorga": termo,  # TODO
                    "financeiro_valor_previsto": agencia_fomento["VL_CONTRIBUICAO"] if agencia_fomento else "",
                    "financeiro_agencia_fomento": agencia_fomento["NOME"].encode(
                        'utf-8').strip() if agencia_fomento else "",
                    "financeiro_id_orgao_projeto": agencia_fomento["ID_ORGAO_PROJETO"] if agencia_fomento else "",
                    "financeiro_id_origem": agencia_fomento["ID_ORIGEM"] if agencia_fomento else "",
                    "financeiro_origem": agencia_fomento["ORIGEM"] if agencia_fomento else "",
                    "ata_departamento": ata,  # TODO
                    "arquivo_projeto": arquivo_proj,  # TODO
                    'vigencia_inicio': datetime.strptime(projeto_bd[u'DT_INICIAL'], '%Y-%m-%d').date(),
                    'vigencia_final': datetime.strptime(projeto_bd[u'DT_CONCLUSAO'], '%Y-%m-%d').date(),
                    'id': projeto_bd[u"ID_PROJETO"]
                }
                projeto = Row(**projeto)
            else:
                projeto = None
        else:
            projeto = None
        return projeto

    def from_form(self, form):
        """
        Converte as informações do form nas colunas referentes à tabela no SIE
        :param form: o formulário
        :return: tupla projeto (dict), e tem_apoio_financeiro (boolean)
        """
        tem_apoio_financeiro = form.vars['financeiro_apoio_financeiro']
        projeto = {
            # 'CARGA_HORARIA'
            'DT_CONCLUSAO': form.vars['vigencia_final'],
            'DT_INICIAL': form.vars['vigencia_inicio'],
            'FUNDACAO_ITEM': self.ITEM_FUNDACOES_NAO_SE_APLICA,
        # TODO Lógica gambiarra de lidar com fundações: Item é sempre jogado como não se aplica. Existe uma linha na tabela de órgãos que substitui esse campo
            'PALAVRA_CHAVE01': form.vars['keyword_1'],
            'PALAVRA_CHAVE02': form.vars['keyword_2'],
            'PALAVRA_CHAVE03': form.vars['keyword_3'],
            'PALAVRA_CHAVE04': form.vars['keyword_4'],
            'RESUMO': form.vars['resumo'],
            'TITULO': form.vars['titulo'],
            'VL_PREVISTO': form.vars['financeiro_valor_previsto'],
        }

        if form.vars.id:  # se tem id
            projeto.update({
                "ID_PROJETO": form.vars.id
            })

        return projeto, tem_apoio_financeiro

    def get_projeto(self, id_projeto):
        """
        Este método retorna um dicionário contendo os dados referentes ao projeto no banco de dados.
        :param id_projeto: integer, id do projeto
        :return: dicionário contendo as informações, None caso não exista projeto com a id informada/erro.
        """
        return super(SIEProjetosPesquisa, self).getProjeto(id_projeto)

    def criar_projeto(self, projeto):
        """
        :type projeto: dict
        :param projeto: Um projeto a ser inserido no banco
        :type funcionario: dict
        :param funcionario: Dicionário de IDS de um funcionário
        :return: Um dicionário contendo a entrada uma nova entrada da tabela PROJETOS
        """

        projeto_padrao = {
            "EVENTO_TAB": self.COD_TABELA_TIPO_EVENTO,
            "EVENTO_ITEM": self.ITEM_TIPO_EVENTO_NAO_SE_APLICA,
            "TIPO_PUBLICO_TAB": self.COD_TABELA_TIPO_PUBLICO_ALVO,
            "TIPO_PUBLICO_ITEM": self.ITEM_TIPO_PUBLICO_3_GRAU,
            "ACESSO_PARTICIP": self.ACESSO_PARTICIPANTES_APENAS_COORDENADOR,
            "PAGA_BOLSA": self.NAO_PAGA_BOLSA,
            "AVALIACAO_TAB": self.COD_TABELA_AVALIACAO_PROJETOS_INSTITUICAO,
            "AVALIACAO_ITEM": self.ITEM_AVALIACAO_PROJETOS_INSTITUICAO_PENDENTE,
            'ID_CLASSIFICACAO': self.ITEM_CLASSIFICACAO_PROJETO_PESQUISA,
            'SITUACAO_TAB': self.COD_TABELA_SITUACAO,
            'SITUACAO_ITEM': self.ITEM_SITUACAO_TRAMITE_REGISTRO,
            'FUNDACAO_TAB': self.COD_TABELA_FUNDACOES, "DT_REGISTRO": date.today()
        }

        projeto.update(projeto_padrao)

        try:
            novo_projeto = self.api.post(self.path, projeto)
            projeto.update({'id_projeto': novo_projeto.insertId})
        except APIException:
            projeto = None
        return projeto

    def atualizar_projeto(self, projeto):
        try:
            retorno = self.api.put(self.path, projeto)
            if retorno and int(retorno.affectedRows) == 1:
                return True
            return False
        except APIException:
            return False

    def criar_documento_projeto(self, funcionario):
        num_processo = self.proximo_numero_processo()
        return SIEDocumentos().criar_documento(self.TIPO_DOCUMENTO, num_processo, funcionario)

    def proximo_numero_processo(self):
        """
        Número do processo é formado através da concatenação de um ID_TIPO_DOC, um sequencial e o ano do documento

        :rtype : str
        :return: Retorna o NUM_PROCESSO gerado a partir da lógica de negócio
        """
        ano = date.today().year
        numero_tipo_doc = SIENumeroTipoDocumento(ano, self.TIPO_DOCUMENTO)
        num_ultimo_doc = str(numero_tipo_doc.proximoNumeroTipoDocumento()).zfill(4)  # NNNN

        return "P%s/%d" % (num_ultimo_doc, ano)  # PNNNN/AAAA

    def get_lista_opcoes_titulacao(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_TITULACAO)

    def get_lista_fundacoes(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        # TODO Constantes?
        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_FUNDACOES, (0, 1,))

    def get_lista_funcoes_orgaos(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        funcoes_proibidas = (
            0,
            self.ITEM_FUNCOES_ORGAOS_RESPONSAVEL
        )

        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_FUNCOES_ORGAOS, funcoes_proibidas)

    def get_lista_funcoes_projeto_pesquisa(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        funcoes_proibidas = (
            self.ITEM_FUNCOES_PROJ_BOLSISTA,
            self.ITEM_FUNCOES_PROJ_CANDIDATO_BOLSISTA,
            self.ITEM_FUNCOES_PROJ_COORDENADOR,
            self.ITEM_FUNCOES_PROJ_DESCR,
            self.ITEM_FUNCOES_PROJ_NAO_DEFINIDA
        )

        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_FUNCOES_PROJ, funcoes_proibidas)

    def get_membros_comunidade_like(self, query):
        params = {"LMIN": 0,
                  "LMAX": 99999,
                  "NOME": query,
                  }

        # fields = ['NOME','ID_PESSOA','MATRICULA','DESCRICAO_VINCULO']
        try:
            res = self.api.get("V_PROJETOS_PESSOAS", params, cache_time=0)
            return res.content if res is not None else []
        except ValueError:
            return []

    def get_orgaos_like(self, query):
        params = {"LMIN": 0,
                  "LMAX": 99999,
                  "NOME_UNIDADE": query,
                  }

        # fields = ['NOME_UNIDADE','ID_ORIGEM','ORIGEM']
        try:
            res = self.api.get("V_ORGAOS_PROJ", params, cache_time=0)
            return res.content if res is not None else []
        except ValueError:
            return []

    def get_orgao(self, id_origem, origem):

        params = {"LMIN": 0,
                  "LMAX": 1,
                  "ID_ORIGEM": id_origem,
                  "ORIGEM": origem
                  }

        try:
            res = self.api.get("V_ORGAOS_PROJ", params, cache_time=self.cacheTime)
            return res.content[0] if res is not None else {}
        except ValueError:
            return {}

    def get_membro_comunidade(self, id_pessoa, matricula):

        params = {"LMIN": 0,
                  "LMAX": 1,
                  "ID_PESSOA": id_pessoa,
                  }
        if matricula:
            params.update({
                "MATRICULA": matricula
            })

        try:
            res = self.api.get("V_PROJETOS_PESSOAS", params, cache_time=0)
            return res.content[0] if res is not None else {}
        except ValueError:
            return {}

    def get_projetos(self, cpf_coordenador=None):

        params = {
            "LMIN": 0,
            "LMAX": 9999,
            'ID_CLASSIFICACAO': self.ITEM_CLASSIFICACAO_PROJETO_PESQUISA,

        }

        if cpf_coordenador:
            params.update({
                "CPF_COORDENADOR": cpf_coordenador
            })

        try:
            res = self.api.get("V_PROJETOS_PESQUISA", params, cache_time=0)
            return res.content if res is not None else []
        except ValueError:
            return []

    def get_coordenador(self, id_projeto):
        """
        Retorna dicionário com o participantes de id_participante
        :return: dict com informações dos participantes, None caso contrário.
        """
        params = {"LMIN": 0,
                  "LMAX": 1,
                  "ID_PROJETO": id_projeto,
                  "FUNCAO_ITEM": SIEProjetosPesquisa.ITEM_FUNCOES_PROJ_COORDENADOR
                  }
        try:
            res = self.api.get("V_PROJETOS_PARTICIPANTES", params, cache_time=0)
            return res.content[0] if res is not None else None
        except ValueError:
            return None

    def get_relatorios_docente(self, cpf):
        """
        Retorna os relatorios docentes de um projeto
        :param cpf: cpf do coordenador
        :return:
        """
        pass


class SIEOrgaosProjsPesquisa(SIEOrgaosProjetos):
    COD_SITUACAO_ATIVO = "A"

    def __init__(self):
        super(SIEOrgaosProjsPesquisa, self).__init__()

    def get_orgao_as_row(self, id_orgao_projeto):
        # todo Gera dependencia de pydal. Isso realmente deveria estar aqui?
        if id_orgao_projeto:
            orgao_bd = self.get_orgao(id_orgao_projeto)
            if orgao_bd:
                orgao_dict = {
                    'nome': orgao_bd[u'NOME'].encode('utf-8'),
                    'descricao_origem': "UNIRIO" if orgao_bd[u"ORIGEM"] == "ID_UNIDADE" else "Externo",
                    'funcao_orgao': orgao_bd[u"FUNCAO_ORG_ITEM"],
                    "valor": orgao_bd[u'VL_CONTRIBUICAO'],
                    'participacao_inicio': datetime.strptime(orgao_bd[u'DT_INICIAL'], '%Y-%m-%d').date(),
                    'participacao_fim': datetime.strptime(orgao_bd[u'DT_FINAL'], '%Y-%m-%d').date(),
                    'observacao': orgao_bd[u'OBS_ORG_PROJETO'].encode('utf-8'),
                    'id': orgao_bd[u"ID_ORGAO_PROJETO"]
                }
                orgao_row = Row(**orgao_dict)
                return orgao_row
        return None

    def get_orgao(self, id_orgao_projeto):
        params = {"LMIN": 0,
                  "LMAX": 1,
                  "ID_ORGAO_PROJETO": id_orgao_projeto,
                  }
        try:
            return self.api.get("V_PROJETOS_ORGAOS", params).first()
        except NoContentException:
            return {}

    def from_form(self, form):
        """
        Converte as colunas do form em colunas referentes a tabela no SIE.
        :param form:
        :return:
        """

        sie_row = {
            "FUNCAO_ORG_ITEM": form.vars.funcao_orgao,
            "DT_INICIAL": form.vars.participacao_inicio,
            "DT_FINAL": form.vars.participacao_fim,
            "VL_CONTRIBUICAO": form.vars.valor,
            "OBS_ORG_PROJETO": form.vars.observacao

        }

        return sie_row

    def cadastra_orgao(self, orgao):
        """

        :param orgao: Um órgão é composto dos seguintes campos:
            'ID_PROJETO',
            ID_UNIDADE ou ID_ENT_EXTERNA,
            "FUNCAO_ORG_ITEM",
            "DT_INICIAL",
            "DT_FINAL",
            "VL_CONTRIBUICAO",
            "OBS_ORG_PROJETO"
        :return: APIPostResponse em caso de sucesso, None c.c.
        :raises: unirio.api.exceptions.APIException
        """
        orgao.update({
            'FUNCAO_ORG_TAB': SIEProjetosPesquisa.COD_TABELA_FUNCOES_ORGAOS,
            'SITUACAO': self.COD_SITUACAO_ATIVO
        })
        return self.api.post(self.path, orgao)

    def get_orgaos(self, id_projeto):
        """
        Retorna dicionário com todos os orgaos do projeto
        :return: dict com informações dos orgaos
        """

        params = {"LMIN": 0,
                  "LMAX": 999,
                  "ID_PROJETO": id_projeto,
                  }

        try:
            res = self.api.get("V_PROJETOS_ORGAOS", params)
            return res.content if res is not None else []
        except NoContentException:
            return []

    def atualizar_orgao(self, orgao):
        """
        :rtype : APIPUTResponse
        :raises: APIException
        """
        try:
            retorno = self.api.put(self.path, orgao)
            if retorno.affectedRows == 1:
                return True
            return False
        except APIException:
            return False

    def deletar_orgao(self, id_orgao_projeto):

        params = {"ID_ORGAO_PROJETO": id_orgao_projeto}
        try:
            retorno = self.api.delete(self.path, params)
            if retorno and retorno.affectedRows == 1:
                return True
            return False
        except APIException:
            return False


class SIEParticipantesProjsPesquisa(SIEParticipantesProjs):
    COD_SITUACAO_ATIVO = "A"

    def __init__(self):
        super(SIEParticipantesProjsPesquisa, self).__init__()
        self.path = "PARTICIPANTES_PROJ"

    def cadastra_participante(self, participante):
        """

        :param participante: Um participante é composto dos seguintes campos:
            'id_projeto','id_curso_aluno','id_contrato_rh','id_ent_externa','id_pessoa','id_unidade',
                              'funcao_participante','data_ini','data_final','carga_horaria','carga_horaria_sugerida',
                              'titulacao_item','situacao/a-i','desc_mail','link_lattes'
        :return: APIPostResponse em caso de sucesso, None c.c.
        :raises APIException:
        """
        participante.update({
            'FUNCAO_TAB': SIEProjetosPesquisa.COD_TABELA_FUNCOES_PROJ,
            'TITULACAO_TAB': SIEProjetosPesquisa.COD_TABELA_TITULACAO,
            'SITUACAO': self.COD_SITUACAO_ATIVO
        })
        return self.api.post(self.path, participante)

    def get_participantes(self, id_projeto):
        """
        Retorna dicionário com todos os participantes do projeto
        :return: dict com informações dos participantes
        """
        params = {
            "LMIN": 0,
            "LMAX": 999,
            "ID_PROJETO": id_projeto,
            "SITUACAO": self.COD_SITUACAO_ATIVO
        }
        try:
            res = self.api.get("V_PROJETOS_PARTICIPANTES", params, cache_time=0)
            return res.content if res is not None else []
        except NoContentException:
            return []

    def get_participante_as_row(self, id_participante):
        """
        Este método retorna um dicionário contendo os dados referentes ao participante convertidos para o formato compatível
        com o modelo no web2py.
        :param id_participante: integer,
        :return: gluon.pydal.objects.Row contendo as informações, None caso não exista participante com a id informada/erro.
        """
        if id_participante:
            participante = self.get_participante(id_participante)
            if participante:
                participante_to_row = campos_sie_lower([participante])[0]
                participante_to_row['id'] = participante_to_row['id_participante']
                participante_to_row['titulacao'] = participante_to_row['descricao_titulacao'].encode('utf-8')
                # participante_to_row['carga_horaria'] = '20'; #dummy
                # participante_to_row['link_lattes'] = '???'; #dummy
                participante_to_row['descr_mail'] = participante_to_row['descr_mail'].strip()
                participante_to_row['funcao_projeto'] = participante_to_row['funcao_item']
                participante_to_row['dt_final'] = datetime.strptime(participante_to_row['dt_final'].strip(),
                                                                    '%Y-%m-%d').date()
                participante_to_row['dt_inicial'] = datetime.strptime(participante_to_row['dt_inicial'].strip(),
                                                                      '%Y-%m-%d').date()
                participante_row = Row(**participante_to_row)
            else:
                participante_row = None
        else:
            participante_row = None
        return participante_row

    def get_participante(self, id_participante):
        """
        Retorna dicionário com o participantes de id_participante
        :return: dict com informações dos participantes, None caso contrário.
        """
        params = {
            "LMIN": 0,
            "LMAX": 1,
            "ID_PARTICIPANTE": id_participante,
        }
        try:
            res = self.api.get("V_PROJETOS_PARTICIPANTES", params)
            return res.content[0] if res is not None else None
        except NoContentException:
            return None


    def get_participante(self, id_projeto, id_pessoa):
        """
        Retorna dicionário com o participante de id_projeto e id_pessoa.
        :return: dict com informações dos participantes, None caso contrário.
        """
        params = {"LMIN": 0,
                  "LMAX": 1,
                  "ID_PROJETO": id_projeto,
                  "ID_PESSOA": id_pessoa,
                  "SITUACAO": self.COD_SITUACAO_ATIVO
                  }
        try:
            res = self.api.get("PARTICIPANTES_PROJ", params,  cache_time=0)
            return res.content[0] if res is not None else None
        except ValueError:
            return None


    def from_form(self, form):
        """
        Converte as informações do form nas colunas referentes à tabela no SIE
        :param form: o formulário
        :return: tupla participante (dict)
        """

        participante = {
            "DT_INICIAL": form.vars.dt_final,
            "DT_FINAL": form.vars.dt_inicial,
            "CARGA_HORARIA": form.vars.carga_horaria,
            # "TITULACAO_ITEM": form.vars.titulacao,
            "DESCR_MAIL": form.vars.descr_mail,
            "CH_SUGERIDA": form.vars.carga_horaria,
            # "LINK_LATTES": form.vars.link_lattes,
            "FUNCAO_ITEM": form.vars.funcao_projeto,
        }

        return participante

    def atualizar_participante(self, participante):
        """
        :rtype : bool
        :raises APIException
        """
        retorno = self.api.put(self.path, participante)
        if retorno.affectedRows == 1:
            return True
        return False

    def deletar_participante(self, id_participante):

        params = {"ID_PARTICIPANTE": id_participante}
        try:
            retorno = self.api.delete(self.path, params)
            if retorno and int(retorno.affectedRows) == 1:
                return True
            return False
        except Exception:
            # todo Esse tratamento não deveria melhorar ?
            return False
