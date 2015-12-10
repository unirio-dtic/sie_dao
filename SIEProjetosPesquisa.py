# -*- coding: utf-8 -*-
from unirio.api.exceptions import APIException, NoContentException
from sie.SIETabEstruturada import SIETabEstruturada
from sie.SIEProjetos import SIEProjetos, SIEParticipantesProjs, SIEArquivosProj, SIEOrgaosProjetos, SIEAvaliacaoProjDAO
from sie.SIEDocumento import SIEDocumentoDAO
from sie.SIEParametros import SIEParametrosDAO
from sie.sie_utils import campos_sie_lower,remover_acentos_query
from sie import SIE, SIEException
from pydal.objects import Row
from datetime import date, datetime
import collections


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

    ITEM_TAB_ESTRUTURADA_DESCRICAO_CAMPO = 0
    ITEM_TITULACAO_INDEFINIDA = 99
    ITEM_FUNDACOES_NAO_SE_APLICA = 1  # => Não se aplica
    ITEM_TIPO_EVENTO_NAO_SE_APLICA = 1  # => Não se aplica
    ITEM_TIPO_PUBLICO_3_GRAU = 8  # => 3o grau
    ITEM_AVALIACAO_PROJETOS_INSTITUICAO_NAO_AVALIADO = 1  # => Não-avaliado
    ITEM_AVALIACAO_PROJETOS_INSTITUICAO_PENDENTE_AVALIACAO = 2
    ITEM_CLASSIFICACAO_PROJETO_PESQUISA = 39718

    ITEM_SITUACAO_SUSPENSO = 4
    ITEM_SITUACAO_RENOVADO = 6
    ITEM_SITUACAO_TRAMITE_REGISTRO = 8
    ITEM_SITUACAO_ANDAMENTO = 2
    # TODO Ter estes parâmetros HARD-CODED é uma limitação.
    ITEM_FUNCOES_PROJ_CANDIDATO_BOLSISTA = 50
    ITEM_FUNCOES_PROJ_DESCR = 0
    ITEM_FUNCOES_PROJ_COORDENADOR = 1
    ITEM_FUNCOES_PROJ_BOLSISTA = 3
    ITEM_FUNCOES_PROJ_NAO_DEFINIDA = 20

    ITEM_FUNCOES_ORGAOS_RESPONSAVEL = 5
    ITEM_FUNCOES_ORGAOS_AGENCIA_FOMENTO = 4
    ITEM_ESTADO_REGULAR = 1

    TIPO_DOCUMENTO = 217

    SITUACAO_ATIVO = 'A'
    ACESSO_PARTICIPANTES_APENAS_COORDENADOR = 'N'
    NAO_PAGA_BOLSA = 'N'

    def __init__(self):
        super(SIEProjetosPesquisa, self).__init__()

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
            'ORDERBY': 'ID_ORGAO_PROJETO',
            "SORT": 'ASC'
        }

        try:
            agencias = self.api.get("V_PROJETOS_ORGAOS", params, cache_time=0)
            return agencias.first()
        except (NoContentException, ValueError):
            return None

    def enviar_relatorio_docente(self, relatorio, params_projeto):

        ha_avaliacao = SIEAvaliacaoProjsPesquisaDAO().get_avaliacao(params_projeto['ANO_REF_AVAL'],relatorio.id_projeto,params_projeto["PERIODO_REF_TAB"],params_projeto["PERIODO_REF_ITEM"])
        if ha_avaliacao:
            raise SIEException("Já há avaliação cadastrada para este projeto neste período de avaliação.")

        arquivo_salvo = SIEArquivosProj().salvar_arquivo(nome_arquivo=relatorio.filename,
                                                         arquivo=relatorio.arquivo,
                                                         id_projeto=relatorio.id_projeto,
                                                         tipo_arquivo=SIEArquivosProj.ITEM_TIPO_ARQUIVO_RELATORIO_DOCENTE)

        documento_avaliacao = SIEAvaliacaoProjsPesquisaDAO().documento_inicial_padrao()

        documento_avaliacao.update({
            "RESUMO_ASSUNTO": "Projeto nº "+ self.get_projeto(relatorio.id_projeto)['NUM_PROCESSO'].strip() #TODO Verificar se essa é a lógica exata.
        })

        documentoDAO = SIEDocumentoDAO()
        documento = documentoDAO.criar_documento(documento_avaliacao)  # PASSO 1

        # cria avaliacao para o arquivo
        avaliacao = SIEAvaliacaoProjsPesquisaDAO().criar_avaliacao(relatorio.id_projeto,documento,params_projeto,data_prorrogacao=relatorio.nova_data_conclusao,obs=relatorio.obs)

        # atualizar ref tabela de arquivos.
        SIEArquivosProj().atualizar_arquivo(arquivo_salvo["ID_ARQUIVO_PROJ"],
                                            {"ID_AVALIACAO_PROJ": avaliacao["ID_AVALIACAO_PROJ"]})

        fluxo = documentoDAO.obter_fluxo_inicial(documento)

        # tramita para a câmara
        documentoDAO.tramitar_documento(documento, fluxo)

        #atualizar projeto com avaliacao_item pendente.
        self.atualizar_projeto({
            "ID_PROJETO":relatorio.id_projeto,
            "AVALIACAO_ITEM": SIEProjetosPesquisa.ITEM_AVALIACAO_PROJETOS_INSTITUICAO_PENDENTE_AVALIACAO
        })

    def registrar_projeto(self, id_projeto):
        """
        Cria o documento e tramita para DPQ. Muda status do projeto tb.
        :param id_projeto:
        :return:
        :rtype: bool
        """

        documento_projeto = self.documento_inicial_padrao()
        documentoDAO = SIEDocumentoDAO()
        documento = documentoDAO.criar_documento(documento_projeto)  # PASSO 1

        # marcando a maneira de lidar com o fluxo caso o destino esteja em uma query (IND_QUERY='S')
        # resolvedor_destino = lambda fluxo: self.resolve_destino_tramitacao(fluxo, id_projeto) # Era usado anteriormente. Deixando aqui pois pode server para depois.

        # faz a primeira tramitação
        fluxo = documentoDAO.obter_fluxo_inicial(documento)
        documentoDAO.tramitar_documento(documento, fluxo)

        projeto = {
            "ID_PROJETO": id_projeto,
            "ID_DOCUMENTO": documento['ID_DOCUMENTO'],
            "NUM_PROCESSO": documento['NUM_PROCESSO']
        }

        return self.atualizar_projeto(projeto)

    def resolve_destino_tramitacao(self, fluxo, id_projeto):
        """
        Resolve o destino do fluxo. No caso de projetos, faz uma query específica no banco.
        Ideal seria que este método fosse uma espécie de delegate, com parâmetros variáveis. pq todo o método primeira tramitacao iria para dentro de um DAO de documento.
        """
        params = {
            "FUNCAO_ORG_ITEM": SIEProjetosPesquisa.ITEM_FUNCOES_ORGAOS_RESPONSAVEL,  # TODO ??? Não seria a câmara??
            "ID_PROJETO": id_projeto
        }
        id_destino = self.api.get("ORGAOS_PROJETOS", params).first()
        return fluxo['TIPO_DESTINO'], id_destino

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
                arquivosDAO = SIEArquivosProj()
                termo = arquivosDAO.get_termo_outorga(id_projeto)
                ata = arquivosDAO.get_ata_departamento(id_projeto)
                arquivo_proj = arquivosDAO.get_arquivo_projeto(id_projeto)
                agencia_fomento = self.get_agencia_fomento(id_projeto)

                projeto = {
                    'id_documento': projeto_bd['ID_DOCUMENTO'],
                    'num_processo': projeto_bd['NUM_PROCESSO'],
                    'titulo': projeto_bd[u'TITULO'].encode('utf-8'),
                    'resumo': projeto_bd[u'RESUMO'].encode('utf-8'),
                    'keyword_1': projeto_bd[u'PALAVRA_CHAVE01'].encode('utf-8'),
                    'keyword_2': projeto_bd[u'PALAVRA_CHAVE02'].encode('utf-8'),
                    'keyword_3': projeto_bd[u'PALAVRA_CHAVE03'].encode('utf-8') if projeto_bd[
                                                                                       u'PALAVRA_CHAVE03'] is not None else "",
                    'keyword_4': projeto_bd[u'PALAVRA_CHAVE04'].encode('utf-8') if projeto_bd[
                                                                                       u'PALAVRA_CHAVE04'] is not None else "",
                    "financeiro_apoio_financeiro": int(bool(agencia_fomento)), #agencia de fomento é uma linha de orgaos do projeto. a representacao na pagina espera um int (0 ou 1).
                # TODO Lógica cheia de gambiarra de lidar com fundações.
                    "carga_horaria": projeto_bd[u'CARGA_HORARIA'],
                    "financeiro_termo_outorga": termo,  # TODO
                    "financeiro_valor_previsto": agencia_fomento["VL_CONTRIBUICAO"] if agencia_fomento else "",
                    "financeiro_agencia_fomento": agencia_fomento["NOME_UNIDADE"].encode(
                        'utf-8').strip() if agencia_fomento else "",
                    "financeiro_id_orgao_projeto": agencia_fomento["ID_ORGAO_PROJETO"] if agencia_fomento else "",
                    "financeiro_id_origem": agencia_fomento["ID_ORIGEM"] if agencia_fomento else "",
                    "financeiro_origem": agencia_fomento["ORIGEM"] if agencia_fomento else "",
                    "ata_departamento": ata,  # TODO
                    "arquivo_projeto": arquivo_proj,  # TODO
                    'vigencia_inicio': datetime.strptime(projeto_bd[u'DT_INICIAL'], '%Y-%m-%d').date() if projeto_bd[
                        u'DT_INICIAL'] else None,
                    'vigencia_final': datetime.strptime(projeto_bd[u'DT_CONCLUSAO'], '%Y-%m-%d').date() if projeto_bd[
                        u'DT_CONCLUSAO'] else None,
                    'id': projeto_bd[u"ID_PROJETO"]
                }
                return Row(**projeto)
            else:
                return None
        return None

    def from_form(self, form):
        """
        Converte as informações do form nas colunas referentes à tabela no SIE
        :param form: o formulário
        :return: tupla projeto (dict), e tem_apoio_financeiro (boolean)
        """

        tem_apoio_financeiro = bool(int(form.vars['financeiro_apoio_financeiro'])) # TODO meio gambi , mas funciona.

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
            "AVALIACAO_ITEM": self.ITEM_AVALIACAO_PROJETOS_INSTITUICAO_NAO_AVALIADO,
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
        retorno = self.api.put(self.path, projeto)
        if retorno and retorno.affectedRows == 1:
            return True
        return False

    def get_lista_opcoes_titulacao(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        return SIETabEstruturada().get_drop_down_options(self.COD_TABELA_TITULACAO)

    def get_lista_fundacoes(self):
        """
        :return: lista contendo listas ("CodOpcao","NomeOpcao")
        """
        return SIETabEstruturada().get_drop_down_options(codigo_tabela=self.COD_TABELA_FUNDACOES,
                                                         valores_proibidos=(self.ITEM_TAB_ESTRUTURADA_DESCRICAO_CAMPO,
                                                                            self.ITEM_FUNDACOES_NAO_SE_APLICA,))

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

        query = remover_acentos_query(query)

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

        query = remover_acentos_query(query)

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
            # Entidade externa só tem ID_PESSOA
            params.update({
                "MATRICULA": matricula
            })

        try:
            res = self.api.get("V_PROJETOS_PESSOAS", params, cache_time=0)
            return res.content[0] if res is not None else {}
        except ValueError:
            return {}

    def get_projetos_pode_pedir_bolsista(self,
                                         cpf_coordenador):  # TODO possivelmente atrelado a uma instancia de algum modelo de coordenador
        projetos_possiveis = self.get_projetos(cpf_coordenador=cpf_coordenador, situacoes=[self.ITEM_SITUACAO_ANDAMENTO,
                                                                                           self.ITEM_SITUACAO_TRAMITE_REGISTRO])

        # Filtra os que tão sem id_documento (ainda não tramitados)
        return filter(lambda projeto: projeto["ID_DOCUMENTO"] is not None,
                      projetos_possiveis)  # TODO tem como fazer sem ser por aqui? checar is not null pela API?

    def get_projetos_em_andamento(self, cpf_coordenador):
        return self.get_projetos(cpf_coordenador, self.ITEM_SITUACAO_ANDAMENTO)

    def get_projetos(self, cpf_coordenador=None, situacoes=None):

        params = {
            "LMIN": 0,
            "LMAX": 9999,
        }

        if cpf_coordenador:
            params.update({
                "CPF_COORDENADOR": cpf_coordenador
            })
        if situacoes:
            if isinstance(situacoes, collections.Iterable) and len(situacoes) > 1:
                params.update({"SITUACAO_ITEM_SET": situacoes})
            elif isinstance(situacoes, collections.Iterable):
                params.update({"SITUACAO_ITEM": situacoes[0]})  # TODO AttributeError?
            else:
                params.update({"SITUACAO_ITEM": situacoes})

        return self.api.get("V_PROJETOS_PESQUISA", params, cache_time=0, bypass_no_content_exception=True)

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
                    'nome': orgao_bd[u'NOME_UNIDADE'].encode('utf-8'),
                    'descricao_origem': "UNIRIO" if orgao_bd[u"ORIGEM"] == "ID_UNIDADE" else "Externo",
                    'funcao_orgao': orgao_bd[u"FUNCAO_ORG_ITEM"],
                    "valor": orgao_bd[u'VL_CONTRIBUICAO'],
                    'participacao_inicio': datetime.strptime(orgao_bd[u'DT_INICIAL'], '%Y-%m-%d').date() if orgao_bd[
                        u'DT_INICIAL'] else None,
                    'participacao_fim': datetime.strptime(orgao_bd[u'DT_FINAL'], '%Y-%m-%d').date() if orgao_bd[
                        u'DT_FINAL'] else None,
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


class SIEAvaliacaoProjsPesquisaDAO(SIEAvaliacaoProjDAO):
    COD_TABELA_TIPO_AVALIACAO = 6016
    ITEM_TIPO_AVALIACAO_PROJETO = 1


    def __init__(self):
        super(SIEAvaliacaoProjDAO, self).__init__()



    def _resolve_situacao_avaliacao(self, situacao_projeto, prorrogacao):
        """Resolve o valor da coluna 'SITUACAO_ITEM' da avaliação a ser criada.
        TODO Existem casos não previstos?
        :param situacao_projeto: conteudo da coluna 'SITUACAO_ITEM' da tabela PROJETOS
        :type situacao_projeto: int
        :param prorrogacao: booleano que indica se o usuário pediu ou não prorrogação da vigencia do projeto.
        :type prorrogacao: bool
        :returns: A situação que deve ser utilizada.
        :rtype: int
        """
        #TODO O que fazer com esse método. Não sabemos se isso será usado ou não!

        if situacao_projeto == SIEProjetosPesquisa.ITEM_SITUACAO_SUSPENSO:
            return SIEProjetosPesquisa.ITEM_SITUACAO_ANDAMENTO
        elif prorrogacao:
            return SIEProjetosPesquisa.ITEM_SITUACAO_RENOVADO
        else:
            return situacao_projeto

    def criar_avaliacao(self,id_projeto,documento,params_projeto_pesquisa,data_prorrogacao=False,obs=''):
        """
        :param id_projeto:
        :param documento:
        :param params_projeto_pesquisa:
        :param prorrogacao:
        :return:
        """
        projeto = SIEProjetosPesquisa().get_projeto(id_projeto)

        avaliacao_default = {
            "PERIODO_REF_TAB": params_projeto_pesquisa["PERIODO_REF_TAB"],
            "PERIODO_REF_ITEM": params_projeto_pesquisa["PERIODO_REF_ITEM"],
            "TIPO_AVAL_TAB": self.COD_TABELA_TIPO_AVALIACAO,
            "TIPO_AVAL_ITEM": self.ITEM_TIPO_AVALIACAO_PROJETO,
            "SITUACAO_TAB": SIEProjetosPesquisa.COD_TABELA_SITUACAO,
            "SITUACAO_ITEM": projeto['SITUACAO_ITEM'], # Atualizado conforme e-mail de 9 de dezembro de 2015 23:33 da Síntese.
            "ANO_REF": params_projeto_pesquisa["ANO_REF_AVAL"],  # TODO  em tese, o ano de referencia é o ano atual de avaliação, pois nenhum projeto pode pedir bolsas sem estar 'em andamento' e para estar 'em andamento' os relatórios não podem estar atrasados -> só falta o relatório atual
            "DT_CONCLUSAO": data_prorrogacao if data_prorrogacao else projeto['DT_CONCLUSAO'],
            "ID_CONTRATO_RH": self.usuario['ID_CONTRATO_RH'],
            "ID_UNIDADE": self.usuario['ID_LOT_OFICIAL']
        }

        avaliacao_default.update({
            "ID_PROJETO": id_projeto,
            "ID_DOCUMENTO": documento['ID_DOCUMENTO'],
            "NUM_PROCESSO": documento["NUM_PROCESSO"]
        })

        if obs:
            avaliacao_default.update({
                'OBS_PRORROGACAO':obs
            })

        try:
            resultado = self.api.post(self.path, avaliacao_default)
            avaliacao_default.update({"ID_AVALIACAO_PROJ": resultado.insertId})  # ????
        except APIException:
            avaliacao_default = None
        return avaliacao_default

class SIECandidatosBolsistasProjsPesquisa(SIE):
    """
    Classe DAO que faz a interação com a tabela de candidatos a bolsistas
    """

    path = "CANDIDATOS_BOLSISTA"

    def __init__(self):
        super(SIECandidatosBolsistasProjsPesquisa, self).__init__()

    def from_candidato_item(self, candidato, id_plano_de_estudos):
        """
        Monta candidato a ser inserido no banco de dados a partir da instancia guardada dos formulários anteriores na session
        :param candidato:
        :return:
        """

        candidato_bolsista = {
            "ID_PROJETO": candidato['projeto_pesquisa'],
            "ID_CURSO_ALUNO": candidato['id_curso_aluno'],
            "ID_PLANO_ESTUDO": id_plano_de_estudos,
        }

        if candidato['link_lattes']:
            candidato_bolsista.update({"LINK_LATTES": candidato['link_lattes']})
        if candidato['descr_mail']:
            candidato_bolsista.update({"DESCR_MAIL": candidato['descr_mail']})
        if candidato['renovacao']:
            candidato_bolsista.update({"RENOVACAO": "S"})

        # ESSE ERA O ANTIGO. DEIXAR AQUI POIS NUNCA SE SABE.
        # candidato_bolsista = {
        #     "ID_PROJETO": candidato['projeto_pesquisa'],
        #     "FUNCAO_ITEM": SIEProjetosPesquisa.ITEM_FUNCOES_PROJ_CANDIDATO_BOLSISTA,
        #     "CARGA_HORARIA": 20,
        #     "TITULACAO_ITEM": SIEProjetosPesquisa.ITEM_TITULACAO_SUPERIOR_INCOMPLETO, # TODO Deve ser mesmo hard-coded? E se for uma segunda graduação?
        #     "CH_SUGERIDA": 20,
        #     "ID_CURSO_ALUNO": candidato['id_curso_aluno'],
        #     "ID_PESSOA": candidato['id_pessoa'],
        #     "ID_UNIDADE": candidato['id_unidade'],
        #     "DT_INICIAL": date.today(),
        #     "DESCR_MAIL": candidato['descr_mail'],
        #     # "ID_BOLSISTA": "..." # TODO??
        #     "LINK_LATTES": candidato['link_lattes'],
        # }
        return candidato_bolsista

    def deletar_candidatos(self, candidatos):
        try:
            for candidato in candidatos:
                params = {"ID_CANDIDATOS_BOLSISTA": candidato["ID_CANDIDATOS_BOLSISTA"]}

                # Deletar linha do candidato
                self.api.delete(self.path, params)
                # plano de estudo relacionado.
                SIEArquivosProj().deletar_arquivo(candidato["ID_PLANO_ESTUDO"])

        except APIException as e:
            raise SIEException("Não foi possível deletar candidato a bolsista", e)
        return True

    def get_candidato_bolsista(self, **kwargs):
        """
        Retorna o candidato a bolsista, dependendo dos kwargs passados. Existem duas formas de se pegar um candidato a bolsista:
        Uma é via o id_candidatos_bolsista, ou é via id_projeto + id_curso_aluno
        :param kwargs: idealmente, ou é { id_candidatos_bolsista: } ou {id_projeto: "", id_curso_aluno: ""}
        :return: candidato a bolsista ou None
        :rtype dict
        """

        params = {}
        if kwargs.has_key('id_candidatos_bolsista'):
            params.update({
                "ID_CANDIDATOS_BOLSISTA": kwargs['id_candidatos_bolsista']
            })
        elif kwargs.has_key('id_projeto') and kwargs.has_key('id_curso_aluno') and kwargs.has_key('ano_ref'):
            params.update({
                "ID_PROJETO": kwargs['id_projeto'],
                "ID_CURSO_ALUNO": kwargs['id_curso_aluno'],
                "ANO_REF_AVAL": kwargs['ano_ref']  # TODO Seria mesmo ano ref aval? ou ano candidatura?
            })
        else:
            raise RuntimeError("Parâmetros inválidos.")

        return self.api.get_single_result(self.path, params, cache_time=0)

    def get_candidatos_bolsistas(self, cpf_coordenador):
        """

        Retorna os candidatos a bolsista atuais de um coordenador.

        :param cpf_coordenador:
        :return:
        """

        params = {
            "CPF_COORDENADOR": cpf_coordenador,
            "ANO_REF_AVAL": SIEParametrosDAO().parametros_prod_inst()["ANO_REF_AVAL"]
        }

        return self.api.get("V_CANDIDATOS_BOLSISTA_DADOS", params, bypass_no_content_exception=True)

    def cadastra_candidato(self, candidato, ano_ref):
        """
        Cadastra candidato a bolsista no banco pela API.

        :param candidato:
        :return:
        """

        candidato.update({
            "ANO_REF_AVAL": ano_ref
        })
        return self.api.post(self.path, candidato)

    def inserir_candidato_bolsista(self, candidato, id_plano_estudos):

        candidato_bolsista = SIECandidatosBolsistasProjsPesquisa().from_candidato_item(candidato, id_plano_estudos)
        ano_ref = SIEParametrosDAO().parametros_prod_inst()[
            "ANO_REF_AVAL"]  # TODO em tese, o ano de referencia é o ano atual??

        # TODO candidato_bolsista_no_banco = SIECandidatosBolsistasProjsPesquisa().get_candidato_bolsista(id_projeto=candidato['projeto_pesquisa'],id_curso_aluno=candidato['id_curso_aluno'],ano_ref=ano_ref) # TODO seria essa uma boa maneira de verificar? podia ter uma exception quando inserisse? id_projeto + id_curso_aluno?
        # TODO if not candidato_bolsista_no_banco:
        SIECandidatosBolsistasProjsPesquisa().cadastra_candidato(candidato_bolsista, ano_ref)
        # else:
        #    raise CandidatoBolsistaExistenteException


class SIEParticipantesProjsPesquisa(SIEParticipantesProjs):
    COD_SITUACAO_ATIVO = "A"

    path = "PARTICIPANTES_PROJ"

    def __init__(self):
        super(SIEParticipantesProjsPesquisa, self).__init__()

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
            'SITUACAO': self.COD_SITUACAO_ATIVO,
            'TITULACAO_ITEM': SIEProjetosPesquisa.ITEM_TITULACAO_INDEFINIDA
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
                # participante_to_row['carga_horaria'] = '20'; #dummy
                # participante_to_row['link_lattes'] = '???'; #dummy
                participante_to_row['descr_mail'] = participante_to_row['descr_mail'].strip()
                participante_to_row['funcao'] = participante_to_row['funcao_item']
                participante_to_row['dt_final'] = datetime.strptime(participante_to_row['dt_final'].strip(),
                                                                    '%Y-%m-%d').date() if participante_to_row[
                    'dt_final'] else None
                participante_to_row['dt_inicial'] = datetime.strptime(participante_to_row['dt_inicial'].strip(),
                                                                      '%Y-%m-%d').date() if participante_to_row[
                    'dt_inicial'] else None
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

    # def get_participante_candidato_bolsista(self, id_projeto, id_pessoa):
    #     """
    #     Retorna dicionário com o participante de id_projeto e id_pessoa.
    #     :return: dict com informações dos participantes, None caso contrário.
    #     """
    #     params = {"LMIN": 0,
    #               "LMAX": 1,
    #               "ID_PROJETO": id_projeto,
    #               "ID_PESSOA": id_pessoa,
    #               "SITUACAO": self.COD_SITUACAO_ATIVO,
    #               "FUNCAO_ITEM": SIEProjetosPesquisa.ITEM_FUNCOES_PROJ_CANDIDATO_BOLSISTA
    #               }
    #     try:
    #         res = self.api.get("PARTICIPANTES_PROJ", params,  cache_time=0)
    #         return res.content[0] if res is not None else None
    #     except ValueError:
    #         return None

    def from_form(self, form):
        """
        Converte as informações do form nas colunas referentes à tabela no SIE
        :param form: o formulário
        :return: tupla participante (dict)
        """
        # TODO Isto não deveria estar aqui, gera dependencia com web2py.
        participante = {
            "DT_INICIAL": form.vars.dt_final,
            "DT_FINAL": form.vars.dt_inicial,
            "CARGA_HORARIA": form.vars.carga_horaria,
            "DESCR_MAIL": form.vars.descr_mail,
            "CH_SUGERIDA": form.vars.carga_horaria,
            "LINK_LATTES": form.vars.link_lattes,
            "FUNCAO_ITEM": form.vars.funcao,
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
