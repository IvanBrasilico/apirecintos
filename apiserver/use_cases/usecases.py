import json
import logging
from zipfile import ZipFile

from sqlalchemy.orm import load_only

from apiserver.models import orm


class UseCases:

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
