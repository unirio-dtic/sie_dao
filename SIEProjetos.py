# coding=utf-8
import base64
from datetime import date, datetime
from deprecator import deprecate
from unirio.api.apiresult import APIException, POSTException
from sie import SIE
from gluon import current
from sie.SIEBolsistas import SIEBolsas, SIEBolsistas
from sie.SIEDocumento import SIEDocumentos, SIETramitacoes, SIEFluxos
from sie.SIEFuncionarios import SIEFuncionarios
from sie.SIETabEstruturada import SIETabEstruturada


__all__ = [
    "SIEProjetos",
    "SIEArquivosProj",
    "SIEClassificacoesPrj",
    "SIEParticipantesProjs",
    "SIECursosDisciplinas",
    "SIEClassifProjetos",
    "SIEOrgaosProjetos"
]


class SIEProjetos(SIE):
    def __init__(self):
        super(SIEProjetos, self).__init__()
        self.path = "PROJETOS"

    def getProjeto(self, ID_PROJETO):
        """
        Dado o identificador único de um projeto na tabela PROJETOS, a função retorna um dicionáio
        correspondente. A requisição é cacheada.

        :param ID_PROJETO: Identificador único de um projeto
        :type ID_PROJETO: int
        :return: Uma entrada na tabela PROJETOS
        :rtype : dict
        """
        params = {
            'LMIN': 0,
            'LMAX': 1,
            'ID_PROJETO': ID_PROJETO
        }

        try:
            return self.api.performGETRequest(self.path, params, cached=0).content[0]
        except (ValueError, AttributeError):
            return None

    def getProjetoDados(self, ID_PROJETO):
        """
        Dado o identificador único de um projeto na tabela PROJETOS, a função retorna um dicionáio
        correspondente a uma entrada na view V_PROJETOS_DADOS, que é uma juncão das tabelas PROJETOS,
        PARTICIPANTES_PRJ, DOCUMENTOS, CLASSIFICACAO_PRJ

        :param ID_PROJETO: Identificador único de um projeto
        :type ID_PROJETO: int
        :return: Uma entrada na view V_PROJETOS_DADOS
        :rtype: dict
        """
        params = {
            'LMIN': 0,
            'LMAX': 1,
            'ID_PROJETO': ID_PROJETO
        }

        try:
            return self.api.performGETRequest("V_PROJETOS_DADOS", params, cached=self.cacheTime).content[0]
        except (ValueError, AttributeError):
            return None

    def getCoordenador(self, ID_PROJETO):
        """
        Dado um ID_PROJETO, a função retorna o seu coordenador, na forma de um dicionário representativo de uma entrada
        na tabela PESSOAS.

        :param ID_PROJETO: Identificador único de um projeto na tabela PROJETOS
        :return: Uma entrada na tabela PESSOAS
        :rtype : dict
        """
        params = {
            'LMIN': 0,
            'LMAX': 1,
            'ID_PROJETO': ID_PROJETO,
            'FUNCAO_ITEM': 1
        }

        try:
            c = self.api.performGETRequest("PARTICIPANTES_PROJ", params, cached=self.cacheTime).content[0]
            return self.api.performGETRequest("PESSOAS", {"ID_PESSOA": c['ID_PESSOA']},
                                                cached=self.cacheTime).content[0]
        except (ValueError, AttributeError):
            return None

    def getDisciplina(self, ID_PROJETO):
        """
        Dado um identificador único na tabela de PROJETOS, a função retornará uma string correspondente ao nome da
        disciplina, de acordo com a classificaçao do projeto

        :rtype : str
        :param ID_PROJETO: Identificador único de uma entrada na tabela PROJETOS
        :return: Nome de uma disciplina
        """
        params = {
            'LMIN': 0,
            'LMAX': 1,
            'ID_PROJETO': ID_PROJETO
        }

        try:
            return self.api.performGETRequest("V_PROJETOS_DADOS", params, cached=self.cacheTime).content[0]['NOME_DISCIPLINA']
        except (ValueError, AttributeError):
            return None

    def projetosDeEnsino(self, edicao, params={}):
        """

        :type edicao: gluon.storage.Storage
        :param edicao: Uma entrada da tabela `edicao`
        :type params: dict
        :param params: Um dicionário de parâmetros a serem usados na busca
        :rtype : list
        :return: Uma lista de projetos de ensino
        """
        params.update({
            "ID_CLASSIFICACAO": 40161,
            "DT_INICIAL": edicao.dt_inicial_projeto,
            "LMIN": 0,
            "LMAX": 99999
        })

        return self.api.get(self.path, params).content

    def projetosDadosEnsino(self, edicao, params={}):
        """

        :type edicao: gluon.storage.Storage
        :param edicao: Uma entrada da tabela `edicao`
        :type params: dict
        :param params: Um dicionário de parâmetros a serem usados na busca
        :rtype : list
        :return: Uma lista de projetos de ensino
        """
        params.update({
            "ID_CLASSIFICACAO": 40161,
            "DT_INICIAL": edicao.dt_inicial_projeto,
            "LMIN": 0,
            "LMAX": 99999
        })

        return self.api.performGETRequest('V_PROJETOS_DADOS', params).content

    @staticmethod
    def isAvaliado(projeto):
        """
        0 => Situação do projeto da Instituição
        1 => Concluído/Publicado
        2 => Em andamento
        4 => Suspenso
        5 => Cancelado
        6 => Renovado
        7 => Cancelado - Res. Interna
        8 => Em tramite para registro
        9 => Indeferido

        :type projeto: dict
        :param projeto: Dicionário correspondente a uma entrada na tabela PROJETOS
        :rtype bool
        """
        #TODO discituir se usar uma lista estática é uma solução aceitável ou se deveria ser realizada uma consulta na TAB_ESTRUTURADA
        if projeto["SITUACAO_ITEM"] in range(1, 10):
            return True

    @deprecate
    def salvarProjeto(self, projeto, funcionario):
        """
        EVENTO_TAB              => Tipos de Eventos
        EVENTO_ITEM = 1         => Não se aplica
        TIPO_PUBLICO_TAB        => Público alvo
        TIPO_PUBLICO_ITEM = 8   => 3o grau
        AVALIACAO_TAB           => Avaliação dos projetos da Instituição
        AVALIACAO_ITEM = 2      => Pendente de avaliacao

        :type projeto: dict
        :param projeto: Um projeto a ser inserido no banco
        :type funcionario: dict
        :param funcionario: Dicionário de IDS de um funcionário
        :return: Um dicionário contendo a entrada uma nova entrada da tabela PROJETOS
        """
        novoDocumento = SIEDocumentos().criarDocumento(funcionario)
        projeto.update({
            "ID_DOCUMENTO": novoDocumento["ID_DOCUMENTO"],
            "ID_UNIDADE": SIECursosDisciplinas().getIdUnidade(projeto['ID_CURSO']),
            "NUM_PROCESSO": novoDocumento["NUM_PROCESSO"],
            "EVENTO_TAB": 6028,
            "EVENTO_ITEM": 1,
            "TIPO_PUBLICO_TAB": 6002,
            "TIPO_PUBLICO_ITEM": 8,
            "ACESSO_PARTICIP": "S",
            "PAGA_BOLSA": "S",
            "DT_INICIAL": current.session.edicao.dt_inicial_projeto,
            "DT_REGISTRO": date.today(),
            "AVALIACAO_TAB": 6010,
            "AVALIACAO_ITEM": 2
        })

        novoProjeto = self.api.performPOSTRequest(self.path, projeto)
        projeto.update({"ID_PROJETO": novoProjeto.insertId})

        return projeto

    def avaliarProjeto(self, ID_PROJETO, avaliacao):
        """
        Método utilizado para avaliar um projeto

        avaliacao = 9           => indeferido (Indeferido)
        avaliacao = 2           => deferido (Em andamento)
        AVALIACAO_ITEM = 3      => Avaliado
        AVALIACAO_ITEM = 4      => Avaliado fora do prazo

        :type ID_PROJETO: int
        :type avaliacao: int
        :param ID_PROJETO: Identificador único de um PROJETO
        :param avaliacao: Um inteiro correspondente a uma avaliação
        """
        try:
            self.api.performPUTRequest(
                self.path,
                {
                    "ID_PROJETO": ID_PROJETO,
                    "AVALIACAO_ITEM": 3,
                    "SITUACAO_ITEM": avaliacao,
                    "DT_ULTIMA_AVAL": date.today()
                }
            )
            self.tramitarDocumentoProjeto(ID_PROJETO, avaliacao)
        except APIException:
            raise APIException("Não foi possível atualizar o estado da avaliação de um projeto.")

    def removerProjeto(self, ID_PROJETO):
        """
        Dada uma entrada na tabela PROJETOS, a função busca e remove essa entrada após buscar e remover o DOCUMENTO
        relacionado, os partifipantes deste projeto, seu orgão e classificação

        :param ID_PROJETO: Identificador único de uma entrada na tabela PROJETOS
        """
        projeto = self.getProjeto(ID_PROJETO)
        SIEParticipantesProjs().removerParticipantesFromProjeto(projeto['ID_PROJETO'])
        SIEOrgaosProjetos().removerOrgaosProjetosDeProjeto(projeto['ID_PROJETO'])
        SIEClassifProjetos().removerClassifProjetosDeProjeto(projeto['ID_PROJETO'])

        try:
            documento = SIEDocumentos().getDocumento(projeto['ID_DOCUMENTO'])
            SIEDocumentos().removerDocumento(documento)
        except ValueError:
            print "Documento %d não encontrado" % projeto['ID_DOCUMENTO']

        self.api.performDELETERequest(self.path, {"ID_PROJETO": ID_PROJETO})

    def situacoes(self):
        """
        A função retorna uma lista de dicionários com as possíveis situações (SITUACAO_ITEM) de um projeto

        :rtype : list
        :return: Lista de dicionários contendo as chaves `ITEM_TABELA` e `DESCRICAO`
        """
        return SIETabEstruturada().itemsDeCodigo(6011)

    def tramitarDocumentoProjeto(self, ID_PROJETO, avaliacao):
        """
        avaliacao = 9           => indeferido (Indeferido)
        avaliacao = 2           => deferido (Em andamento)

        :type ID_PROJETO: int
        :param ID_PROJETO: Identificador único de um PROJETO
        :type avaliacao: int
        :param avaliacao: Um inteiro correspondente a uma avaliação
        """
        projeto = self.getProjeto(ID_PROJETO)
        documento = SIEDocumentos().getDocumento(projeto['ID_DOCUMENTO'])

        if avaliacao == 9:
            # fluxo = SIEFluxos().getProximosFluxosFromDocumento(documento)
            fluxo = NotImplementedError
        elif avaliacao == 2:
            fluxo = NotImplementedError
        else:
            raise ValueError("%d não é um tipo de avaliação reconhecido" % avaliacao)

        tramitacao = SIETramitacoes(documento)
        novaTramitacao = tramitacao.criarTramitacao()
        tramitacao.tramitarDocumento(
            novaTramitacao,
            current.session.funcionario,
            fluxo
        )



class SIEArquivosProj(SIE):


    ITEM_TIPO_ARQUIVO_TERMO_OUTORGA = 19
    ITEM_TIPO_ARQUIVO_PROJETO = 1
    ITEM_TIPO_ARQUIVO_ATA_DEPARTAMENTO = 5
    ITEM_TIPO_ARQUIVO_PARECER_CEUA = 18

    def __init__(self):
        super(SIEArquivosProj, self).__init__()
        self.path = "ARQUIVOS_PROJ"

    def __conteudoDoArquivo(self, arquivo):
        """
        O campo CONTEUDO_ARQUIVO é BLOB, tendo em vista que a API espera uma string base64, o método é responsável por
        encodar o conteúdo e fornecer uma string válida

        :type arquivo: FieldStorage
        :rtype : str
        :param arquivo: Um arquivo a ser convertido
        :return: Uma string correspondente ao conteúdo de um arquivo binário, na forma de base64
        """
        return base64.b64encode(arquivo.file.read())

    def get_arquivo_projeto(self, id_projeto):
        """
        Retorna um dicionário contendo a ata de departamento que satisfaça o id_projeto ou None, caso tal arquivo não exista
        :param id_projet:
        :return:
        """
        return self.get_arquivo(id_projeto, self.ITEM_TIPO_ARQUIVO_PROJETO)

    def get_ata_departamento(self, id_projeto):
        """
        Retorna um dicionário contendo o arquivo de projeto que satisfaça o id_projeto ou None, caso tal arquivo não exista
        :param id_projet:
        :return:
        """
        return self.get_arquivo(id_projeto, self.ITEM_TIPO_ARQUIVO_ATA_DEPARTAMENTO)

    def get_parecer_comite_etica(self, id_projeto):
        """
        Retorna um dicionário contendo o arquivo de parecer de comite de ética que satisfaça o id_projeto ou None, caso tal arquivo não exista
        :param id_projeto:
        :return:
        """
        return self.get_arquivo(id_projeto, self.ITEM_TIPO_ARQUIVO_PARECER_CEUA)

    def get_termo_outorga(self, id_projeto):
        """
        Retorna um dicionário contendo o termo de outorga que satisfaça o id_projeto ou None, caso tal arquivo não exista
        :param id_projet:
        :return:
        """
        return self.get_arquivo(id_projeto, self.ITEM_TIPO_ARQUIVO_TERMO_OUTORGA)

    def get_arquivo(self, id_projeto, tipo_arquivo):
        """
        Retorna um dicionário contendo o arquivo que satisfaça o id_projeto e tipo_arquivo e ou None, caso tal arquivo não exista
        :param id_projeto: id_projeto relacionado ao arquivo
        :param tipo_arquivo: tipo do arquivo
        :return: dicionário contendo {NOME_ARQUIVO:, file:, CONTEUDO_ARQUIVO.
        """
        params = {
            'ID_PROJETO': id_projeto,
            'TIPO_ARQUIVO_ITEM': tipo_arquivo,
            'LMIN': 0,
            'LMAX': 1,
            'ORDERBY':'ID_ARQUIVO_PROJ DESC'
        }

        fields = ["NOME_ARQUIVO", "CONTEUDO_ARQUIVO"]
        try:
            arquivo = self.api.get(self.path, params, fields, 0).content
        except (ValueError, AttributeError):
            arquivo = None
        return arquivo

    def salvar_arquivo(self, nome_arquivo, arquivo, id_projeto, tipo_arquivo):
        """
        :type arquivo: FieldStorage
        :param arquivo: Um arquivo correspondente a um projeto que foi enviado para um formulário
        :type projeto: int/string
        :param projeto: Um id de projeto
        :rtype : dict
        """
        arquivo_proj = {
            "ID_PROJETO": id_projeto,
            "DT_INCLUSAO": date.today(),
            "TIPO_ARQUIVO_TAB": 6005,
            "TIPO_ARQUIVO_ITEM": tipo_arquivo,
            "NOME_ARQUIVO": nome_arquivo,
            "CONTEUDO_ARQUIVO": SIE.handle_blob(arquivo)
        }

        try:
            novo_arquivo_proj = self.api.post(self.path, arquivo_proj)
            arquivo_proj.update({"ID_ARQUIVO_PROJ": novo_arquivo_proj.insertId}) #????
        except POSTException:
            arquivo_proj = None
        return arquivo_proj

    @deprecate
    def salvarArquivo(self, arquivo, projeto, funcionario, TIPO_ARQUIVO_ITEM):
        """

        TIPO_ARQUIVO_ITEM = 1       => Projeto

        :type arquivo: FieldStorage
        :param arquivo: Um arquivo correspondente a um projeto que foi enviado para um formulário
        :type projeto: dict
        :param projeto: Um dicionário contendo uma entrada da tabela PROJETOS
        :type funcionario: dict
        :param funcionario: Dicionário de IDS de um funcionário
        :rtype : dict
        """
        arquivoProj = {
            "ID_PROJETO": projeto["ID_PROJETO"],
            "DT_INCLUSAO": date.today(),
            "TIPO_ARQUIVO_TAB": 6005,
            "TIPO_ARQUIVO_ITEM": TIPO_ARQUIVO_ITEM,
            "NOME_ARQUIVO": arquivo.filename,
            "CONTEUDO_ARQUIVO": self.__conteudoDoArquivo(arquivo)
        }
        # TODO remover comentários quando BLOB estiver sendo salvo no DB2
        #novoArquivoProj = self.api.performPOSTRequest(self.path, arquivoProj)
        #arquivoProj.update({"ID_ARQUIVO_PROJ": novoArquivoProj.insertId})
        self.salvarDB2BLOB(arquivoProj)
        self.salvarCopiaLocal(arquivo, arquivoProj, funcionario)

        return arquivoProj

    def salvarDB2BLOB(self, arquivoProj):

        ID_ARQUIVO_PROJ = 'NEXT VALUE FOR DBSM.SEQ_ARQUIVOS_PROJ'
        CONCORRENCIA = '999'
        ENDERECO_FISICO = str(current.request.client)

        current.dbSie.executesql(""" SELECT ID_ARQUIVO_PROJ FROM NEW TABLE(
																		INSERT INTO DBSM.ARQUIVOS_PROJ(
																		                        ID_ARQUIVO_PROJ,
																								ID_PROJETO,
																								DT_INCLUSAO,
																								TIPO_ARQUIVO_TAB,
																								TIPO_ARQUIVO_ITEM,
																								NOME_ARQUIVO,
																								CONTEUDO_ARQUIVO,
																								DT_ALTERACAO,
																								HR_ALTERACAO,
																								COD_OPERADOR,
																								CONCORRENCIA)
																								VALUES
																								(
																								""" +ID_ARQUIVO_PROJ + """,
																								""" +arquivoProj["ID_PROJETO"] + """,
																								CURRENT_DATE,
																								""" + arquivoProj["TIPO_ARQUIVO_TAB"] + """,
																								"""+arquivoProj["TIPO_ARQUIVO_ITEM"]+""",
																								'""" + arquivoProj["NOME_ARQUIVO"] + """',
																								""" + arquivoProj["CONTEUDO_ARQUIVO"] + """,
																								CURRENT_DATE,
																								CURRENT_TIME,
																								'1',
																								""" + CONCORRENCIA + """
																								)
																		)""", as_dict=True)
        return dict()

    def salvarCopiaLocal(self, arquivo, arquivoProj, funcionario):
        """

        :type arquivo: FieldStorage
        :param arquivo: Um arquivo correspondente a um projeto que foi enviado para um formulário
        :type arquivo_proj: dict
        :param arquivo_proj: Um dicionário contendo uma entrada da tabela ARQUIVO_PROJS
        :type funcionario: dict
        :param funcionario: Dicionário de IDS de um funcionário
        """
        # TODO id_arquivo_proj não está com o comportamente desejado, mas é necessário até que BLOBS sejam inseridos corretamente. Remover o mesmo após resolver problema
        try:
            with open(arquivo.fp.name, 'rb') as stream:
                i = current.db.projetos.insert(
                    anexo_tipo=arquivo.type,
                    anexo_nome=arquivo.filename,
                    id_arquivo_proj=None,
                    id_funcionario=funcionario["ID_FUNCIONARIO"],
                    id_projeto=arquivoProj["ID_PROJETO"],
                    edicao=current.session.edicao.id,
                    arquivo=current.db.projetos.arquivo.store(stream, arquivo.filename),      # upload
                    tipo_arquivo_item=arquivoProj["TIPO_ARQUIVO_ITEM"],
                    dt_envio=datetime.now()
                )
                print "Gravou localmente [%s] com ID [%d]" % (arquivo.filename, i)
        except IOError as e:
            if e.errno == 63:
                current.session.flash += "Impossivel salvar o arquivo %s. Nome muito grande" % arquivo.filename
        except psycopg2.IntegrityError:
            current.db.rollback()
            current.session.flash += "Não é possível enviar mais de um arquivo por etapa"
        except Exception as e:
            current.db.rollback()
            raise e
        finally:
            current.db.commit()


class SIEClassificacoesPrj(SIE):

    COD_CLASSIFICACAO_PRJ_CAMARA_PESQUISA = 33
    COD_CLASSIFICACAO_PRJ_CLASSIFICACAO_CNPQ = 3
    COD_CLASSIFICACAO_PRJ_COMITE_ETICA = 32
    COD_CLASSIFICACAO_PRJ_GRUPO_CNPQ = 4
    ITEM_PARECER_COMITE_ETICA_NAO_SE_APLICA = 40172

    def __init__(self):
        super(SIEClassificacoesPrj, self).__init__()
        self.path = "CLASSIFICACOES_PRJ"

    def getClassificacoesPrj(self, classificacaoItem, codigo):
        """
        Talvez devesse se chamar get_classificacao_projeto


        CLASSIFICACAO_ITEM  => 1 - Tipos de Projetos, 41 - Disciplina vinculada
        CODIGO PARA CLASSIFICACAO_ITEM = 1 => 1 - Ensino, 2 - Pesquisa, 3 - Extensão, 4 - Desenvolvimento institucional

        :type classificacaoItem: int
        :type codigo: int
        :param classificacaoItem:
        :param codigo: COD_DISCIPLINA de uma disciplina do SIE
        :rtype : list
        :return: Uma lista de dicionários com os tipos de projetos
        """
        params = {
            'CLASSIFICACAO_ITEM': classificacaoItem,
            'CODIGO': codigo
        }
        fields = [
            'ID_CLASSIFICACAO',
            'DESCRICAO'
        ]
        return self.api.performGETRequest(self.path, params, fields, cached=self.cacheTime).content

    def get_classificacoes_proj(self, classificacao_item):
        """
        CLASSIFICACAO_ITEM  => 1 - Tipos de Projetos, 41 - Disciplina vinculada
        CODIGO PARA CLASSIFICACAO_ITEM = 1 => 1 - Ensino, 2 - Pesquisa, 3 - Extensão, 4 - Desenvolvimento institucional

        :type classificacaoItem: int
        :type codigo: int
        :param classificacaoItem:
        :param codigo: COD_DISCIPLINA de uma disciplina do SIE
        :rtype : list
        :return: Uma lista de dicionários com os tipos de projetos
        """
        params = {
            'CLASSIFICACAO_ITEM': classificacao_item
        }
        params.update({
            'LMIN': 0,
            'LMAX': 9999
        })
        fields = ["ID_CLASSIFICACAO", "DESCRICAO","CODIGO","ID_CLASSIF_SUP"]
        return self.api.performGETRequest(self.path, params, fields, cached=self.cacheTime).content

    def get_camaras_pesquisa(self):
        try:
            camaras_dict = self.get_classificacoes_proj(self.COD_CLASSIFICACAO_PRJ_CAMARA_PESQUISA)
            camaras = [ (d[u'ID_CLASSIFICACAO'],d[u'DESCRICAO'].encode('utf-8')) for d in camaras_dict]
        except AttributeError:
            camaras = None

        return camaras

    def get_classificacoes_cnpq(self):
        try:
            classif_dict = self.get_classificacoes_proj(self.COD_CLASSIFICACAO_PRJ_CLASSIFICACAO_CNPQ)
            classif = [ (d[u'ID_CLASSIFICACAO'],d[u'DESCRICAO'].encode('utf-8'),d[u'ID_CLASSIF_SUP']) for d in classif_dict]
        except AttributeError:
            classif = None

        return classif

    def get_grupos_cnpq(self):
        try:
            grupo_dict = self.get_classificacoes_proj(self.COD_CLASSIFICACAO_PRJ_GRUPO_CNPQ)
            grupos = [ (d[u'ID_CLASSIFICACAO'],d[u'DESCRICAO'].encode('utf-8'),d[u'ID_CLASSIF_SUP']) for d in grupo_dict]
        except AttributeError:
            grupos = None

        return grupos

    def get_comites_etica(self):
        try:
            comites_dict = self.get_classificacoes_proj(self.COD_CLASSIFICACAO_PRJ_COMITE_ETICA)
            comites = [ (d[u'ID_CLASSIFICACAO'],d[u'DESCRICAO'].encode('utf-8')) for d in comites_dict]
        except AttributeError:
            comites = None

        return comites

class SIEParticipantesProjs(SIE):
    def __init__(self):
        super(SIEParticipantesProjs, self).__init__()
        self.path = "PARTICIPANTES_PROJ"

    def criarParticipanteCoordenador(self, ID_PROJETO, funcionario):
        """
        FUNCAO_TAB = 6003       => Papel do participante de um projeto
        FUNCAO_ITEM = 1         => Coordenador
        SITUACAO = A            => Ao adicionar um participante, ele estará ativo(A)

        :param ID_PROJETO: Identificador único de uma entrada na tabela PROJETOS
        :param funcionario: Dicionário de IDS de um funcionário
        :rtype : unirio.api.apiresult.APIPostResponse
        """
        escolaridade = SIEFuncionarios().getEscolaridade(funcionario["ID_FUNCIONARIO"])
        participante = {
            "TITULACAO_ITEM": escolaridade["ESCOLARIDADE_ITEM"],
            "ID_PESSOA": funcionario["ID_PESSOA"],
            "ID_CONTRATO_RH": funcionario["ID_CONTRATO_RH"]
            # "DESCR_MAIL": funcionario["DESCR_MAIL"],   # TODO deveria constar na session.funcionario
        }

        return self._criarParticipante(ID_PROJETO, 1, participante)

    def criarParticipanteBolsista(self, projeto, aluno, edicao):
        """
        TITULACAO_ITEM = 9      => Superior Incompleto
        FUNCAO_ITEM = 3         => Bolsista

        :param ID_PROJETO: Identificador único de uma entrada na tabela PROJETOS
        :param aluno: Dicionário de atributos de um aluno
        :rtype : unirio.api.apiresult.APIPostResponse
        """
        ID_BOLSISTA = SIEBolsistas().criarBolsista(SIEBolsas().getBolsa(6), edicao, aluno, projeto).insertId

        participante = {
            "ID_PESSOA": aluno["ID_PESSOA"],
            "ID_CURSO_ALUNO": aluno["ID_CURSO_ALUNO"],
            "TITULACAO_ITEM": 9,
            "DESCR_MAIL": aluno["DESCR_MAIL"],
            "ID_BOLSISTA": ID_BOLSISTA
        }

        return self._criarParticipante(projeto['ID_PROJETO'], 3, participante)

    def _criarParticipante(self, ID_PROJETO, FUNCAO_ITEM, participante={}):
        """
        FUNCAO_TAB = 6003       => Papel do participante de um projeto

        FUNCAO_ITEM previstas na TAB_ESTRUTURADA:

        1 => Coordenador
        2 => Orientador
        3 => Bolsista
        4 => Participante Voluntário
        5 => Pesquisador Colaborador
        6 => Co-orientador
        10 => Apresentador
        11 => Autor
        12 => Co-autor
        13 => Executor
        14 => Estagiário
        15 => Acompanhante
        16 => Monitoria não subsidiada
        20 => Não definida
        17 => Orientador de aluno
        50 => Candidato a bolsista

        :type ID_PROJETO: int
        :param ID_PROJETO: Identificador único de uma projeto na tabela PROJETOS
        :type FUNCAO_ITEM: int
        :param FUNCAO_ITEM: Identificador úncio de uma descrição de função. Identificadores possíveis podem ser
                            encontrados na TAB_ESTRUTURADA, COD_TABELA 6003
        :type pessoa: dict
        :param pessoa: Dicionário contendo dados
        :rtype : unirio.api.apiresult.APIPostResponse
        """
        participante.update({
            "CARGA_HORARIA": 20,
            "CH_SUGERIDA": 20,
            "DT_INICIAL": date.today(),
            "ID_PROJETO": ID_PROJETO,
            "FUNCAO_ITEM": FUNCAO_ITEM,
            "FUNCAO_TAB": 6003,
            "ID_PESSOA": participante["ID_PESSOA"],
            "SITUACAO": "A",
            "TITULACAO_TAB": 168,
        })

        return self.api.performPOSTRequest(self.path, participante)

    def descricaoDeFuncaoDeParticipante(self, participante):
        """
        Dado um parcipante, o método retorna a descrição textual de sua função no projeto

        :type participante: dict
        :rtype : str
        :param participante: Um dicionário correspondente a uma entrada da tabela PARTICIPANTES_PROJ que contenha pelo
        menos a chave FUNCAO_ITEM
        """
        try:
            return SIETabEstruturada().descricaoDeItem(participante["FUNCAO_ITEM"], 6003)
        except AttributeError:
            return "Não foi possível recuperar"

    def getParticipantes(self, params):
        """

        :rtype : list
        """
        params.update({
            'LMIN': 0,
            'LMAX': 9999
        })

        try:
            return self.api.performGETRequest(self.path, params).content
        except (ValueError, AttributeError):
            return None

    def getBolsistas(self, ID_PROJETO):
        params = {
            'ID_PROJETO': ID_PROJETO,
            'FUNCAO_ITEM': 3
        }
        return self.getParticipantes(params)

    def getParticipacoes(self, pessoa, params={}):
        """

        :param pessoa: Um dicionário da view V_FUNCIONARIO_IDS
        :param params: Um dicionários de parâmetros a serem utilizados na busca
        :return: Uma lista de participações em projetos
        :rtype: list
        """
        params.update({
            "ID_PESSOA": pessoa["ID_PESSOA"],
            "LMIN": 0,
            "LMAX": 9999
        })

        try:
            return self.api.performGETRequest(self.path, params).content
        except ValueError:
            return []

    def getParticipante(self, ID_PARTICIPANTE):
        params = {
            'ID_PARTICIPANTE': ID_PARTICIPANTE,
            'LMIN': 0,
            'LMAX': 1
        }
        return self.api.performGETRequest(self.path, params, cached=self.cacheTime).content[0]

    def removerParticipante(self, ID_PARTICIPANTE):
        self.api.performDELETERequest(self.path, {"ID_PARTICIPANTE": ID_PARTICIPANTE})

    def removerParticipantesFromProjeto(self, ID_PROJETO):
        params = {
            "ID_PROJETO": ID_PROJETO,
            "LMIN": 0,
            "LMAX": 99999
        }
        try:
            participantes = self.api.performGETRequest(self.path, params, ['ID_PARTICIPANTE'])
            for p in participantes.content:
                self.removerParticipante(p['ID_PARTICIPANTE'])
        except ValueError:
            print "Nenhum participante para remover do projeto %d" % ID_PROJETO

    def inativarParticipante(self, participante):
        """
        Dado um participante, o método inativa o mesmo e a bolsa referente.

        :type participante: dict
        :param participante: Uma entrada da tabela PARTICIPANTES_PROJ, contendo as keys ID_PARTICIPANTE e ID_BOLSISTA
        """
        params = {
            'ID_PARTICIPANTE': participante['ID_PARTICIPANTE'],
            'SITUACAO': 'I',
            'DT_FINAL': date.today()
        }
        self.api.performPUTRequest(self.path, params)
        SIEBolsistas().inativarBolsista(participante['ID_BOLSISTA'])

class SIECursosDisciplinas(SIE):
    def __init__(self):
        super(SIECursosDisciplinas, self).__init__()
        self.path = "V_CURSOS_DISCIPLINAS"

    def getCursos(self, params={}):
        params.update({
            "LMIN": 0,
            "LMAX": 99999,
            "ORDERBY": "NOME_CURSO",
            "DISTINCT": "T"
        })
        fields = [
            "NOME_CURSO",
            "ID_CURSO"
        ]
        return self.api.performGETRequest(self.path, params, fields, cached=self.cacheTime).content

    def getCursosGraduacao(self):
        """
        NIVEL_CURSO_ITEM = 3    => Graduação

        :rtype : list
        :return: Returna uma lista de cursos de graduação
        """
        params = {"NIVEL_CURSO_ITEM": 3}
        return self.getCursos(params)

    def getDisciplinas(self, ID_CURSO, filtroObrigatorias=False):
        params = {
            "LMIN": 0,
            "LMAX": 9999,
            "ID_CURSO": ID_CURSO,
            "ORDERBY": "NOME_DISCIPLINA"
        }
        if filtroObrigatorias:
            params["OBRIGATORIA"] = "S"
        fields = [
            "NOME_DISCIPLINA",
            "COD_DISCIPLINA"
        ]
        return self.api.performGETRequest(self.path, params, fields, cached=self.cacheTime).content

    def getIdUnidade(self, ID_CURSO):
        """
        :type ID_CURSO: int
        :rtype : int
        """
        params = {
            "ID_CURSO": ID_CURSO
        }
        fields = ["ID_UNIDADE"]
        return self.api.performGETRequest(self.path, params, fields).first()["ID_UNIDADE"]


class SIEClassifProjetos(SIE):
    def __init__(self):
        super(SIEClassifProjetos, self).__init__()
        self.path = "CLASSIF_PROJETOS"

    @deprecate
    def criarClassifProjetos(self, ID_PROJETO, ID_CLASSIFICACAO):
        """

        :type ID_PROJETO: int
        :param ID_PROJETO: Identificador único de um projeto
        :type ID_CLASSIFICACAO: int
        :param ID_CLASSIFICACAO: Identificador único da classificação de um projeto
        :rtype: unirio.api.apiresult.APIPOSTResponse
        """
        classifProj = {
            "ID_PROJETO": ID_PROJETO,
            "ID_CLASSIFICACAO": ID_CLASSIFICACAO
        }

        try:
            return self.api.post(self.path, classifProj)
        except Exception:
            current.session.flash = "Não foi possível criar uma nova classificação para o projeto."

    @deprecate
    def removerClassifProjetos(self, ID_CLASSIF_PROJETO):
        self.api.delete(self.path, {"ID_CLASSIF_PROJETO": ID_CLASSIF_PROJETO})

    @deprecate
    def removerClassifProjetosDeProjeto(self, ID_PROJETO):
        params = {
            "ID_PROJETO": ID_PROJETO,
            "LMIN": 0,
            "LMAX": 9999
        }
        try:
            classifs = self.api.performGETRequest(self.path, params, ["ID_CLASSIF_PROJETO"])
            for classif in classifs.content:
                self.removerClassifProjetos(classif['ID_CLASSIF_PROJETO'])
        except ValueError:
            print "Nenhum CLASSIF_PROJETOS a deletar"

    @deprecate
    def getClassifProjetos(self, ID_PROJETO):
        params = {
            "ID_PROJETO": ID_PROJETO,
            "LMIN": 0,
            "LMAX": 9999
        }
        try:
            return self.api.performGETRequest(self.path, params)
        except ValueError:
            return None

    @deprecate
    def getClassifProjetosEnsino(self, ID_PROJETO):
        try:
            return self.getClassifProjetos(ID_PROJETO).content[0]
        except ValueError:
            return None

    @deprecate
    def atualizar(self, ID_CLASSIF_PROJETO, ID_CLASSIFICACAO):
        raise NotImplementedError
        # self.db.log_admin.insert(
        #             acao='update',
        #             valores=ID_CLASSIFICACAO,
        #             tablename='CLASSIF_PROJETOS',
        #             colname='ID_CLASSIFICACAO',
        #             uid=ID_CLASSIF_PROJETO,
        #             user_id=current.auth.user_id,
        #             dt_alteracao=datetime.now()
        #     )
        # return self.api.performPUTRequest(self.path, {
        #     'ID_CLASSIF_PROJETO': ID_CLASSIF_PROJETO,
        #     'ID_CLASSIFICACAO': ID_CLASSIFICACAO
        # })

    def atualizar_classificacoes(self, id_projeto, classificacoes, grupos, comite, camara):
        """

        :param id_projeto:
        :param classificacoes:
        :param grupos:
        :param comite:
        :param camara:
        :return:
        """

        #pior maneira de se fazer isso: deletar o que tem, criar de novo.
        self.removerClassifProjetosDeProjeto(id_projeto)  #TRY???

        todas_classificacoes = []
        todas_classificacoes.extend(classificacoes) if type(classificacoes) == list else todas_classificacoes.append(classificacoes)
        todas_classificacoes.extend(grupos) if type(grupos) == list else todas_classificacoes.append(grupos)
        todas_classificacoes.extend([comite])
        todas_classificacoes.extend([camara])

        for classificacao in todas_classificacoes:
            self.criarClassifProjetos(id_projeto, classificacao)

        return True

    def get_classif_projeto(self, params):

        params.update({
            "LMIN": 0,
            "LMAX": 9999,
        })
        try:
            res = self.api.get("V_PROJETOS_CLASSIFICACOES", params, cached=0)
            return res.content if res is not None else []
        except (AttributeError, ValueError):
            return []


    def get_classificacoes_cnpq(self,id_projeto):

        params = {
            "ID_PROJETO": id_projeto,
            "CLASSIFICACAO_ITEM": SIEClassificacoesPrj.COD_CLASSIFICACAO_PRJ_CLASSIFICACAO_CNPQ
        }
        classificacoes_cnpq = self.get_classif_projeto(params)
        if classificacoes_cnpq:
            ids_classificacoes_cnpq = [row[u'ID_CLASSIFICACAO'] for row in classificacoes_cnpq]
            return ids_classificacoes_cnpq
        return []

    def get_grupos_cnpq(self, id_projeto):

        params = {
            "ID_PROJETO": id_projeto,
            "CLASSIFICACAO_ITEM": SIEClassificacoesPrj.COD_CLASSIFICACAO_PRJ_GRUPO_CNPQ
        }
        grupos_cnpq = self.get_classif_projeto(params)
        if grupos_cnpq:
            ids_grupos_cnpq = [row[u'ID_CLASSIFICACAO'] for row in grupos_cnpq]
            return ids_grupos_cnpq
        return []

    def get_camara_pesquisa(self,id_projeto):
        params = {
            "ID_PROJETO": id_projeto,
            "CLASSIFICACAO_ITEM": SIEClassificacoesPrj.COD_CLASSIFICACAO_PRJ_CAMARA_PESQUISA
        }
        camara_pesquisa = self.get_classif_projeto(params)
        if camara_pesquisa:
            return camara_pesquisa[0][u"ID_CLASSIFICACAO"]
        return None

    def get_comite_etica(self,id_projeto):
        params = {
            "ID_PROJETO": id_projeto,
            "CLASSIFICACAO_ITEM": SIEClassificacoesPrj.COD_CLASSIFICACAO_PRJ_COMITE_ETICA
        }
        comite_etica = self.get_classif_projeto(params)
        if comite_etica:
            return comite_etica[0][u"ID_CLASSIFICACAO"]
        return None

class SIEOrgaosProjetos(SIE):
    def __init__(self):
        super(SIEOrgaosProjetos, self).__init__()
        self.path = "ORGAOS_PROJETOS"

    def criarOrgaosProjetos(self, projeto, ID_UNIDADE):
        """
        FUNCAO_ORG_TAB => 6006 - Função dos órgãos nos projetos
        FUNCAO_ITEM_TAB => 6 - Curso beneficiado

        :param projeto: Um dicionário contendo a entrada uma entrada da tabela PROJETOS
        :param ID_UNIDADE:
        :return:
        """
        orgaoProj = {
            "ID_PROJETO": projeto["ID_PROJETO"],
            "ID_UNIDADE": ID_UNIDADE,
            "FUNCAO_ORG_TAB": 6006,
            "FUNCAO_ORG_ITEM": 6,
            "DT_INICIAL": projeto["DT_INICIAL"],
            "SITUACAO": "A"
        }
        try:
            return self.api.performPOSTRequest(self.path, orgaoProj)
        except Exception:
            current.session.flash = "Não foi possível associar um órgão ao projeto."

    def removerOrgaosProjetos(self, ID_ORGAO_PROJETO):
        self.api.performDELETERequest(self.path, {"ID_ORGAO_PROJETO": ID_ORGAO_PROJETO})

    def removerOrgaosProjetosDeProjeto(self, ID_PROJETO):
        """
        Dada uma entrada na tabela PROJETOS, a função busca e remove todas as entradas de ORGAOES_PROJETOS referentes a
        esse projeto.

        :param ID_PROJETO: Identificador único de uma entrada na tabela PROJETOS
        :type ID_PROJETO: int
        """
        try:
            orgaos = self.api.performGETRequest(self.path,
                                                {"ID_PROJETO": ID_PROJETO},
                                                ['ID_ORGAO_PROJETO'])
            for orgao in orgaos.content:
                self.removerOrgaosProjetos(orgao['ID_ORGAO_PROJETO'])
        except ValueError:
            print "Nenhuma entrada encontrada em ORGAOS_PROJETOS"