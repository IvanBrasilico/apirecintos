import json
import logging
from zipfile import ZipFile

from sqlalchemy.orm import load_only

from apiserver.models import orm


class UseCases:

    def __init__(self, db_session, basepath: str):
        """Init

        :param db_session: Conexao ao Banco
        :param recinto: codigo do recinto
        :param request_IP: IP de origem
        :param basepath: Diretório raiz para gravar arquivos
        """
        self.db_session = db_session
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
        self.db_session.add(novo_evento)
        if commit:
            self.db_session.commit()
        else:
            self.db_session.flush()
        self.db_session.refresh(novo_evento)
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

    def load_filhos(self, osfilhos, campos_excluidos=['ID']):
        filhos = []
        if osfilhos and len(osfilhos) > 0:
            for filho in osfilhos:
                filhos.append(
                    filho.dump(
                        exclude=campos_excluidos)
                )
        return filhos

    def insert_filhos(self, idevento, osfilhos, classefilho, fk_no_filho):
        """Processa lista no campo 'campofilhos' para inserir aclasse

        :param idevento: ID do evento pai (PK)
        :param campofilhos: nome do campo que contem filhos do evento
        :param aclasse: Nome da Classe a criar
        :param fk_no_filho: Nome do campo que referencia pai na Classe filha (FK)
        :return: None, apenas levanta exceção se acontecer
        """
        for filho in osfilhos:
            params = {**{fk_no_filho: idevento}, **filho}
            print('filho', filho)
            print('params', params)
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
        listaconteineres = evento.get('listaConteineresUld', [])
        for conteiner in listaconteineres:
            conteiner['inspecao_id'] = inspecaonaoinvasiva.ID
            logging.info('Creating ConteinerUld %s..',
                         conteiner.get('num'))
            conteineruld = orm.ConteinerUld(inspecao=inspecaonaoinvasiva,
                                            **conteiner)
            self.db_session.add(conteineruld)
        listareboques = evento.get('listaSemirreboque', [])
        for reboque in listareboques:
            reboque['inspecao_id'] = inspecaonaoinvasiva.ID
            logging.info('Creating Semirreboque %s..',
                         reboque.get('placa'))
            semirreboque = orm.Semirreboque(inspecao=inspecaonaoinvasiva,
                                            **reboque)
            self.db_session.add(semirreboque)
        listamanifestos = evento.get('listaManifestos', [])
        for manifesto in listamanifestos:
            manifesto['inspecao_id'] = inspecaonaoinvasiva.ID
            logging.info('Creating manifesto %s..',
                         manifesto.get('num'))
            ormmanifesto = orm.Manifesto(inspecao=inspecaonaoinvasiva,
                                         **manifesto)
            self.db_session.add(ormmanifesto)
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
            print(anexo.get('coordenadasAlerta'))
            if anexo.get('coordenadasAlerta'):
                self.db_session.flush()
                self.db_session.refresh(anexoinspecao)
                self.insert_filhos(anexoinspecao.ID,
                                   anexo.get('coordenadasAlerta'),
                                   orm.CoordenadasAlerta,
                                   'anexo_id')

        identificadores = evento.get('listaCarga', [])
        for identificador in identificadores:
            logging.info('Creating identificadorinspecaonaoinvasiva %s..',
                         identificador)
            oidentificador = orm.IdentificadorInspecao(
                inspecao=inspecaonaoinvasiva,
                identificador=identificador)
            self.db_session.add(oidentificador)
        self.db_session.commit()
        self.db_session.refresh(inspecaonaoinvasiva)
        return inspecaonaoinvasiva

    def load_inspecaonaoinvasiva(self, codRecinto: str,
                                 idEvento: str) -> orm.InspecaonaoInvasiva:
        """
        Retorna InspecaonaoInvasiva encontrada única no filtro recinto E IDEvento.

        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.InspecaonaoInvasiva
        """
        print(idEvento, codRecinto)
        inspecaonaoinvasiva = orm.InspecaonaoInvasiva.query.filter(
            orm.InspecaonaoInvasiva.idEvento == idEvento,
            orm.InspecaonaoInvasiva.codRecinto == codRecinto
        ).outerjoin(
            orm.AnexoInspecao
        ).outerjoin(
            orm.IdentificadorInspecao
        ).outerjoin(
            orm.ConteinerUld
        ).outerjoin(
            orm.Semirreboque
        ).outerjoin(
            orm.Manifesto
        ).one()
        inspecaonaoinvasiva_dump = inspecaonaoinvasiva.dump()
        if inspecaonaoinvasiva.anexos and len(inspecaonaoinvasiva.anexos) > 0:
            inspecaonaoinvasiva_dump['anexos'] = []
            for anexo in inspecaonaoinvasiva.anexos:
                anexo.load_file(self.basepath)
                anexo_dump = anexo.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                anexo_dump['coordenadasAlerta'] = []
                for coordenadas in anexo.coordenadasAlerta:
                    anexo_dump['coordenadasAlerta'].append(
                        coordenadas.dump(exclude=['ID', 'anexo', 'anexo_id'])
                    )
                inspecaonaoinvasiva_dump['anexos'].append(anexo_dump)
        if inspecaonaoinvasiva.listaConteineresUld and \
                len(inspecaonaoinvasiva.listaConteineresUld) > 0:
            inspecaonaoinvasiva_dump['listaConteineresUld'] = []
            for conteiner in inspecaonaoinvasiva.listaConteineresUld:
                inspecaonaoinvasiva_dump['listaConteineresUld'].append(
                    conteiner.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                )
        if inspecaonaoinvasiva.listaSemirreboque and \
                len(inspecaonaoinvasiva.listaSemirreboque) > 0:
            inspecaonaoinvasiva_dump['listaSemirreboque'] = []
            for semirreboque in inspecaonaoinvasiva.listaSemirreboque:
                inspecaonaoinvasiva_dump['listaSemirreboque'].append(
                    semirreboque.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                )
        if inspecaonaoinvasiva.listaManifestos and \
                len(inspecaonaoinvasiva.listaManifestos) > 0:
            inspecaonaoinvasiva_dump['listaManifestos'] = []
            for manifesto in inspecaonaoinvasiva.listaManifestos:
                inspecaonaoinvasiva_dump['listaManifestos'].append(
                    manifesto.dump(exclude=['ID', 'inspecao', 'inspecao_id'])
                )
        if inspecaonaoinvasiva.identificadores and \
                len(inspecaonaoinvasiva.identificadores) > 0:
            inspecaonaoinvasiva_dump['listaCarga'] = []
            for identificador in inspecaonaoinvasiva.identificadores:
                inspecaonaoinvasiva_dump['listaCarga'].append(
                    identificador.identificador
                )
        return inspecaonaoinvasiva_dump

    def insert_pesagemveiculocarga(self, evento: dict) -> orm.PesagemVeiculoCarga:
        logging.info('Creating PesagemVeiculoCarga %s..', evento.get('IDEvento'))
        pesagemveiculocarga = self.insert_evento(orm.PesagemVeiculoCarga, evento,
                                                 commit=False)
        listareboques = evento.get('listaSemirreboque', [])
        self.insert_filhos(pesagemveiculocarga.ID, listareboques,
                           orm.ReboquePesagemVeiculoCarga, 'pesagem_id')
        listaconteineres = evento.get('listaConteineresUld', [])
        self.insert_filhos(pesagemveiculocarga.ID, listaconteineres,
                           orm.ConteinerPesagemVeiculoCarga, 'pesagem_id')
        listaManifestos = evento.get('listaManifestos', [])
        self.insert_filhos(pesagemveiculocarga.ID, listaManifestos,
                           orm.ManifestoPesagemVeiculoCarga, 'pesagem_id')
        self.db_session.commit()
        self.db_session.refresh(pesagemveiculocarga)
        return pesagemveiculocarga

    def load_pesagemveiculocarga(self, codRecinto: str,
                                 idEvento: str) -> orm.PesagemVeiculoCarga:
        """
        Retorna PesagemVeiculoCarga encontrada única no filtro recinto E IDEvento.

        :param codRecinto: Codigo do recinto
        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.InspecaonaoInvasiva
        """
        evento = orm.PesagemVeiculoCarga.query.filter(
            orm.PesagemVeiculoCarga.idEvento == idEvento,
            orm.PesagemVeiculoCarga.codRecinto == codRecinto
        ).outerjoin(
            orm.ReboquePesagemVeiculoCarga
        ).outerjoin(
            orm.ConteinerPesagemVeiculoCarga
        ).outerjoin(
            orm.ManifestoPesagemVeiculoCarga
        ).one()
        pesagemveiculocarga_dump = evento.dump()
        lexclude = ['ID', 'pesagem', 'pesagem_id']
        pesagemveiculocarga_dump['listaSemirreboque'] = \
            self.load_filhos(evento.listaSemirreboque, lexclude)
        pesagemveiculocarga_dump['listaConteineresUld'] = \
            self.load_filhos(evento.listaConteineresUld, lexclude)
        pesagemveiculocarga_dump['listaManifestos'] = \
            self.load_filhos(evento.listaManifestos, lexclude)
        return pesagemveiculocarga_dump

    def insert_acessoveiculo(self, evento: dict) -> orm.AcessoVeiculo:
        logging.info('Creating PesagemVeiculoCarga %s..', evento.get('IDEvento'))
        acessoveiculo = self.insert_evento(orm.AcessoVeiculo, evento,
                                           commit=False)
        listareboques = evento.get('listaSemirreboque', [])
        self.insert_filhos(acessoveiculo.ID, listareboques,
                           orm.ReboqueGate, 'acessoveiculo_id')
        listaconteineres = evento.get('listaConteineresUld', [])
        self.insert_filhos(acessoveiculo.ID, listaconteineres,
                           orm.ConteineresGate, 'acessoveiculo_id')
        listamanifestos = evento.get('listaManifestos', [])
        self.insert_filhos(acessoveiculo.ID, listamanifestos,
                           orm.ManifestoGate, 'acessoveiculo_id')
        listadidue = evento.get('listaDiDue', [])
        self.insert_filhos(acessoveiculo.ID, listadidue,
                           orm.DiDueGate, 'acessoveiculo_id')
        for item in evento.get('listaChassi'):
            ochassi = orm.ChassiGate(
                acessoveiculo_id=acessoveiculo.ID, num=item
            )
            self.db_session.add(ochassi)
        for item in evento.get('listaNfe'):
            anfe = orm.NfeGate(
                acessoveiculo=acessoveiculo, chavenfe=item
            )
            self.db_session.add(anfe)
        self.db_session.commit()
        self.db_session.refresh(acessoveiculo)
        return acessoveiculo

    def load_acessoveiculo(self, codRecinto: str,
                           idEvento: str) -> orm.AcessoVeiculo:
        """
        Retorna PesagemVeiculoCarga encontrada única no filtro recinto E IDEvento.

        :param codRecinto: Codigo do recinto
        :param IDEvento: ID do Evento informado pelo recinto
        :return: instância objeto orm.InspecaonaoInvasiva
        """
        evento = orm.AcessoVeiculo.query.filter(
            orm.AcessoVeiculo.idEvento == idEvento,
            orm.AcessoVeiculo.codRecinto == codRecinto
        ).outerjoin(
            orm.ReboqueGate
        ).outerjoin(
            orm.ConteineresGate
        ).outerjoin(
            orm.ManifestoGate
        ).outerjoin(
            orm.DiDueGate
        ).outerjoin(
            orm.NfeGate
        ).outerjoin(
            orm.ChassiGate
        ).one()
        acessoveiculo_dump = evento.dump()
        lexclude = ['ID', 'acessoveiculo', 'acessoveiculo_id']
        acessoveiculo_dump['listaSemirreboque'] = \
            self.load_filhos(evento.listaSemirreboque, lexclude)
        acessoveiculo_dump['listaConteineresUld'] = \
            self.load_filhos(evento.listaConteineresUld, lexclude)
        acessoveiculo_dump['listaManifestos'] = \
            self.load_filhos(evento.listaManifestos, lexclude)
        acessoveiculo_dump['listaDiDue'] = \
            self.load_filhos(evento.listaDiDue, lexclude)
        if evento.listaChassi and len(evento.listaChassi) > 0:
            acessoveiculo_dump['listaChassi'] = []
            for item in evento.listaChassi:
                acessoveiculo_dump['listaChassi'].append(
                    item.num
                )
        if evento.listaNfe and len(evento.listaNfe) > 0:
            acessoveiculo_dump['listaNfe'] = []
            for item in evento.listaNfe:
                acessoveiculo_dump['listaNfe'].append(
                    item.chavenfe
                )
        return acessoveiculo_dump

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
