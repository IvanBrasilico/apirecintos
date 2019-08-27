import json
import logging
from zipfile import ZipFile

from sqlalchemy.orm import load_only

import assinador
from apiserver.models import orm


class UseCases:
    @classmethod
    def gera_chaves_recinto(cls, db_session, recinto: str) -> (bytes, bytes):
        """Chama gerador de chaves, armazena chave publica, retorna chave privada.

        :param db_session: Conexão ao BD
        :param recinto: codigo do recinto
        :return: chave privada gerada em bytes, recinto assinado em bytes
        """
        private_key, public_key = assinador.generate_keys()
        assinado = assinador.sign(recinto.encode('utf-8'), private_key)
        public_pem = assinador.public_bytes(public_key)
        orm.ChavePublicaRecinto.set_public_key(db_session, recinto, public_pem)
        private_pem = assinador.private_bytes(private_key)
        return private_pem, assinado

    @classmethod
    def get_public_key(cls, db_session, recinto):
        return orm.ChavePublicaRecinto.get_public_key(db_session, recinto)

    def __init__(self, db_session, recinto: str, request_IP: str, basepath: str):
        """Init

        :param db_session: Conexao ao Banco
        :param recinto: codigo do recinto
        :param request_IP: IP de origem
        :param basepath: Diretório raiz para gravar arquivos
        """
        self.db_session = db_session
        self.recinto = recinto
        self.request_IP = request_IP
        self.basepath = basepath
        self.eventos_com_filhos = {
            orm.InspecaonaoInvasiva: self.load_inspecaonaoinvasiva,
            orm.AgendamentoAcessoVeiculo: self.load_agendamentoacessoveiculo,
            orm.CredenciamentoPessoa: self.load_credenciamentopessoa,
            orm.CredenciamentoVeiculo: self.load_credenciamentoveiculo,
        }

    def allowed_file(self, filename, extensions):
        """Checa extensões permitidas."""
        return '.' in filename and \
               filename.rsplit('.', 1)[-1].lower() in extensions

    def valid_file(self, file, extensions=['jpg', 'xml', 'json']) -> [bool, str]:
        """Valida arquivo. Retorna resultado(True/False) e mensagem de erro."""
        erro = None
        if not file:
            erro = 'Arquivo nao informado'
        elif not file.filename:
            erro = 'Nome do arquivo vazio'
        elif not self.allowed_file(file.filename, extensions):
            erro = 'Nome de arquivo não permitido: ' + \
                   file.filename
        return erro is None, erro

    def insert_evento(self, aclass, evento: dict, commit=True) -> orm.EventoBase:
        logging.info('Creating evento %s %s' %
                     (aclass.__name__,
                      evento.get('IDEvento'))
                     )
        novo_evento = aclass(**evento)
        novo_evento.recinto = self.recinto
        novo_evento.request_IP = self.request_IP
        self.db_session.add(novo_evento)
        if commit:
            self.db_session.commit()
        else:
            self.db_session.flush()
        self.db_session.refresh(novo_evento)
        novo_evento.hash = hash(novo_evento)
        return novo_evento

    def load_evento(self, aclass, IDEvento: int, fields: list = None) -> orm.EventoBase:
        """
        Retorna Evento classe aclass encontrado único com recinto E IDEvento.

        Levanta exceção NoResultFound(não encontrado) ou MultipleResultsFound.

        :param aclass: Classe ORM que acessa o BD
        :param IDEvento: ID do Evento informado pelo recinto
        :param fields: Trazer apenas estes campos
        :return: objeto
        """
        query = self.db_session.query(aclass).filter(
            aclass.IDEvento == IDEvento,
            aclass.recinto == self.recinto
        )
        if fields and isinstance(fields, list) and len(fields) > 0:
            query = query.options(load_only(fields))
        evento = query.one()
        return evento

    def load_eventosnovos(self, aclass, IDEvento, dataevento,
                          fields: list = None) -> list:
        """
        Retorna Evento classe aclass encontrado único com recinto E IDEvento.

        Levanta exceção NoResultFound(não encontrado) ou MultipleResultsFound.

        :param IDEvento: ID a partir do qual buscar
        :param IDEvento: data a partir da qual buscar
        :param fields: Trazer apenas estes campos
        :return: lista de objetos
        """
        # TODO: Fazer para Todos os Eventos complexos, que possuem filhos
        if dataevento is None:
            query = self.db_session.query(aclass).filter(
                aclass.IDEvento > IDEvento,
                aclass.recinto == self.recinto
            )
        else:
            query = self.db_session.query(aclass).filter(
                aclass.dataevento > dataevento,
                aclass.recinto == self.recinto
            )
        if aclass in self.eventos_com_filhos:
            loader_func = self.eventos_com_filhos[aclass]
            idseventos = query.options(load_only(['ID'])).all()
            result = []
            for id in idseventos:
                result.append(loader_func(id))
        else:
            if fields is not None:
                query = query.options(load_only(fields))
            return query.all()

    def get_filhos(self, osfilhos, campos_excluidos=[]):
        filhos = []
        if osfilhos and len(osfilhos) > 0:
            for filho in osfilhos:
                filhos.append(
                    filho.dump(
                        exclude=campos_excluidos)
                )
        return filhos

    def insert_filhos(self, oevento, osfilhos, classefilho, fk_no_filho):
        """Processa lista no campo 'campofilhos' para inserir aclasse

        :param oevento: dict com valores recebidos do JSON
        :param campofilhos: nome do campo que contem filhos do evento
        :param aclasse: Nome da Classe a criar
        :param fk_no_filho: Nome do campo que referencia pai na Classe filha
        :return: None, apenas levanta exceção se acontecer
        """
        for filho in osfilhos:
            params = {**{fk_no_filho: oevento}, **filho}
            novofilho = classefilho(**params)
            self.db_session.add(novofilho)

    def get_anexos(self, osfilhos, campos_excluidos=[]):
        filhos = []
        if osfilhos and len(osfilhos) > 0:
            for filho in osfilhos:
                filho.load_file(self.basepath)
                filhos.append(
                    filho.dump(
                        exclude=campos_excluidos)
                )
        return filhos

    def insert_anexos(self, oevento, osfilhos, classefilho, fk_no_filho):
        """Processa lista no campo 'campofilhos' para inserir aclasse(AnexoBase)

        :param oevento: dict com valores recebidos do JSON
        :param campofilhos: nome do campo que contem filhos do evento
        :param aclasse: Nome da Classe a criar. Deve descender de AnexoBase
        :param fk_no_filho: Nome do campo que referencia pai na Classe filha
        :return: None, apenas levanta exceção se acontecer
        """
        for filho in osfilhos:
            params = {**{fk_no_filho: oevento}, **filho}
            novofilho = classefilho(**params)
            content = filho.get('content')
            if content:
                novofilho.save_file(self.basepath, content)
            self.db_session.add(novofilho)

    @classmethod
    def get_anexo(self, evento, nomearquivo):
        """Classes que têm anexo precisam deste comportamento comum


        :param evento: Base SQLAlchemy que tem campo anexos
        :param nomearquivo: nomearquivo de um dos anexos
        :return: um Anexo do EventoBase ou None se não encontrado
        """
        if nomearquivo:
            for anexo in evento.anexos:
                if anexo.nomearquivo == nomearquivo:
                    return anexo
        else:  # Se nomearquivo não foi passado, considera que só tem um anexo
            if getattr(evento, 'anexos', False) and len(evento.anexos) > 0:
                return evento.anexos[0]
        return None

    def insert_inspecaonaoinvasiva(self, evento: dict) -> orm.InspecaonaoInvasiva:
        logging.info('Creating inspecaonaoinvasiva %s..', evento.get('IDEvento'))
        inspecaonaoinvasiva = self.insert_evento(orm.InspecaonaoInvasiva, evento,
                                                 commit=False)
        anexos = evento.get('anexos', [])
        for anexo in anexos:
            anexo['inspecao_id'] = inspecaonaoinvasiva.ID
            logging.info('Creating anexoinspecaonaoinvasiva %s..',
                         anexo.get('datamodificacao'))
            anexoinspecao = orm.AnexoInspecao(inspecao=inspecaonaoinvasiva,
                                              **anexo)
            content = anexo.get('content')
            if anexo.get('content'):
                anexoinspecao.save_file(self.basepath, content)
            self.db_session.add(anexoinspecao)
        identificadores = evento.get('identificadores', [])
        for identificador in identificadores:
            logging.info('Creating identificadorinspecaonaoinvasiva %s..',
                         identificador.get('identificador'))
            oidentificador = orm.IdentificadorInspecao(
                inspecao=inspecaonaoinvasiva,
                **identificador)
            self.db_session.add(oidentificador)
        self.db_session.commit()
        return inspecaonaoinvasiva

    def load_inspecaonaoinvasiva(self, IDEvento: int) -> orm.InspecaonaoInvasiva:
        """
        Retorna InspecaonaoInvasiva encontrada única no filtro recinto E IDEvento.

        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.InspecaonaoInvasiva
        """
        inspecaonaoinvasiva = orm.InspecaonaoInvasiva.query.filter(
            orm.InspecaonaoInvasiva.IDEvento == IDEvento,
            orm.InspecaonaoInvasiva.recinto == self.recinto
        ).outerjoin(
            orm.AnexoInspecao
        ).outerjoin(
            orm.IdentificadorInspecao
        ).one()
        inspecaonaoinvasiva_dump = inspecaonaoinvasiva.dump()
        inspecaonaoinvasiva_dump['hash'] = hash(inspecaonaoinvasiva)
        if inspecaonaoinvasiva.anexos and len(inspecaonaoinvasiva.anexos) > 0:
            inspecaonaoinvasiva_dump['anexos'] = []
            for anexo in inspecaonaoinvasiva.anexos:
                anexo.load_file(self.basepath)
                inspecaonaoinvasiva_dump['anexos'].append(
                    anexo.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                )
        if inspecaonaoinvasiva.identificadores and \
                len(inspecaonaoinvasiva.identificadores) > 0:
            inspecaonaoinvasiva_dump['identificadores'] = []
            for identificador in inspecaonaoinvasiva.identificadores:
                inspecaonaoinvasiva_dump['identificadores'].append(
                    identificador.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                )
        return inspecaonaoinvasiva_dump

    def insert_agendamentoacessoveiculo(self, evento: dict
                                        ) -> orm.AgendamentoAcessoVeiculo:
        logging.info('Creating agendamentoacessoveiculo %s..',
                     evento.get('IDEvento'))
        agendamentoacessoveiculo = self.insert_evento(
            orm.AgendamentoAcessoVeiculo, evento,
            commit=False)
        conteineres = evento.get('conteineres', [])
        for conteiner in conteineres:
            logging.info('Creating conteinergateagendamento %s..',
                         conteiner.get('numero'))
            oconteiner = orm.ConteineresGateAgendado(
                agendamentoacessoveiculo=agendamentoacessoveiculo,
                **conteiner)
            self.db_session.add(oconteiner)
        reboques = evento.get('reboques', [])
        for reboque in reboques:
            logging.info('Creating reboquegateagendamento %s..',
                         reboque.get('identificador'))
            oreboque = orm.ReboquesGateAgendado(
                agendamentoacessoveiculo=agendamentoacessoveiculo,
                **reboque)
            self.db_session.add(oreboque)
        self.db_session.commit()
        return agendamentoacessoveiculo

    def load_agendamentoacessoveiculo(self, IDEvento: int
                                      ) -> orm.AgendamentoAcessoVeiculo:
        """
        Retorna AgendamentoAcessoVeiculo encontrada única no filtro recinto E IDEvento.

        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.AgendamentoAcessoVeiculo
        """
        agendamento = orm.AgendamentoAcessoVeiculo.query.filter(
            orm.AgendamentoAcessoVeiculo.IDEvento == IDEvento,
            orm.AgendamentoAcessoVeiculo.recinto == self.recinto
        ).outerjoin(
            orm.ConteineresGateAgendado
        ).outerjoin(
            orm.ReboquesGateAgendado
        ).one()
        agendamentoacessoveiculo_dump = agendamento.dump()
        agendamentoacessoveiculo_dump['hash'] = hash(agendamento)
        if agendamento.conteineres and len(agendamento.conteineres) > 0:
            agendamentoacessoveiculo_dump['conteineres'] = []
            for conteiner in agendamento.conteineres:
                agendamentoacessoveiculo_dump['conteineres'].append(
                    conteiner.dump(
                        exclude=['ID', 'agendamentoacessoveiculo',
                                 'agendamentoacessoveiculo_id'])
                )
        agendamentoacessoveiculo_dump['reboques'] = self.get_filhos(
            agendamento.reboques,
            campos_excluidos=['ID', 'agendamentoacessoveiculo',
                              'agendamentoacessoveiculo_id']
        )
        """
        if agendamento.reboques and \
                len(agendamento.reboques) > 0:
            agendamentoacessoveiculo_dump['reboques'] = []
            for reboque in agendamento.reboques:
                agendamentoacessoveiculo_dump['reboques'].append(
                    reboque.dump(
                        exclude=['ID', 'agendamentoacessoveiculo',
                                 'agendamentoacessoveiculo_id'])
                )
        """
        return agendamentoacessoveiculo_dump

    def insert_credenciamentopessoa(self, evento: dict) -> orm.CredenciamentoPessoa:
        """
        Insere CredenciamentoPessoa no Banco de Dados

        :param evento: Dicionário contendo valores do JSON passado
        :return: Objeto orm.CredenciamentoPessoa
        """
        logging.info('Creating credenciamentopessoa %s..',
                     evento['IDEvento'])
        credenciamentopessoa = self.insert_evento(
            orm.CredenciamentoPessoa, evento,
            commit=False)
        fotos = evento.get('fotos', [])
        self.insert_anexos(credenciamentopessoa, fotos,
                           orm.FotoPessoa, 'credenciamentopessoa')
        self.db_session.commit()
        return credenciamentopessoa

    def load_credenciamentopessoa(self, IDEvento):
        """
        Retorna CredenciamentoPessoa encontrado única no filtro recinto E IDEvento.

        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.CredenciamentoPessoa
        """
        credenciamento = orm.CredenciamentoPessoa.query.filter(
            orm.CredenciamentoPessoa.IDEvento == IDEvento,
            orm.CredenciamentoPessoa.recinto == self.recinto
        ).outerjoin(
            orm.FotoPessoa
        ).one()
        credenciamentopessoa_dump = credenciamento.dump()
        credenciamentopessoa_dump['hash'] = hash(credenciamento)
        credenciamentopessoa_dump['fotos'] = self.get_anexos(
            credenciamento.fotos,
            campos_excluidos=['ID', 'credenciamentopessoa',
                              'credenciamentopessoa_id']
        )
        return credenciamentopessoa_dump

    def insert_credenciamentoveiculo(self, evento: dict) -> orm.CredenciamentoVeiculo:
        """
        Insere CredenciamentoVeiculo no Banco de Dados

        :param evento: Dicionário contendo valores do JSON passado
        :return: Objeto orm.CredenciamentoVeiculo
        """
        logging.info('Creating credenciamentoveiculo %s..',
                     evento['IDEvento'])
        credenciamentoveiculo = self.insert_evento(
            orm.CredenciamentoVeiculo, evento,
            commit=False)
        fotos = evento.get('fotos', [])
        self.insert_anexos(credenciamentoveiculo, fotos,
                           orm.FotoVeiculo, 'credenciamentoveiculo')
        reboques = evento.get('reboques', [])
        self.insert_filhos(credenciamentoveiculo, reboques,
                           orm.ReboquesVeiculo, 'credenciamentoveiculo')
        self.db_session.commit()
        return credenciamentoveiculo

    def load_credenciamentoveiculo(self, IDEvento):
        """
        Retorna CredenciamentoVeiculo encontrado única no filtro recinto E IDEvento.

        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.CredenciamentoVeiculo
        """
        credenciamento = orm.CredenciamentoVeiculo.query.filter(
            orm.CredenciamentoVeiculo.IDEvento == IDEvento,
            orm.CredenciamentoVeiculo.recinto == self.recinto
        ).outerjoin(
            orm.FotoVeiculo
        ).outerjoin(
            orm.ReboquesVeiculo
        ).one()
        credenciamentoveiculo_dump = credenciamento.dump()
        credenciamentoveiculo_dump['hash'] = hash(credenciamento)
        credenciamentoveiculo_dump['fotos'] = self.get_anexos(
            credenciamento.fotos,
            campos_excluidos=['ID', 'credenciamentoveiculo',
                              'credenciamentoveiculo_id']
        )
        credenciamentoveiculo_dump['reboques'] = self.get_filhos(
            credenciamento.reboques,
            campos_excluidos=['ID', 'credenciamentoveiculo',
                              'credenciamentoveiculo_id']
        )
        return credenciamentoveiculo_dump

    def load_arquivo_eventos(self, file):
        """Valida e carrega arquivo JSON de eventos."""
        validfile, mensagem = self.valid_file(file,
                                              extensions=['json', 'bson', 'zip'])
        if not validfile:
            raise Exception(mensagem)
        if 'zip' in file.filename:
            file = ZipFile(file)
        content = file.read()
        content = content.decode('utf-8')
        eventos = json.loads(content)
        return eventos
