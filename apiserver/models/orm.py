import collections
import logging
import mimetypes
import os
from base64 import b64decode, b64encode

from dateutil.parser import parse
from sqlalchemy import Boolean, Column, DateTime, Integer, \
    String, create_engine, ForeignKey, Index, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref

Base = declarative_base()
db_session = None
engine = None


class BaseDumpable(Base):
    __abstract__ = True

    def dump(self, exclude=None):
        dump = dict([(k, v) for k, v in vars(self).items() if not k.startswith('_')])
        if exclude:
            for key in exclude:
                if dump.get(key):
                    dump.pop(key)
        return dump

    def __hash__(self):
        dump = self.dump()
        clean_dump = {}
        for k, v in dump.items():
            if isinstance(v, collections.Hashable):
                clean_dump[k] = v
        _sorted = sorted([(k, v) for k, v in clean_dump.items()])
        # print('Sorted dump:', _sorted)
        ovalues = tuple([s[1] for s in _sorted])
        # print('Sorted ovalues:', ovalues)
        ohash = hash(ovalues)
        # print(ohash)
        return ohash


class Manifesto(BaseDumpable):
    __abstract__ = True
    num = Column(String(100))
    tipo = Column(String)


class EventoBase(BaseDumpable):
    __abstract__ = True

    cnpjTransmissor = Column(String, index=True)
    codRecinto = Column(String, index=True)
    contingencia = Column(Boolean, index=True)
    cpfOperOcor = Column(String, index=True)
    cpfOperReg = Column(String, index=True)
    dtHrOcorrencia = Column(DateTime(), index=True)
    dtHrTransmissao = Column(DateTime(), index=True)
    dtHrRegistro = Column(DateTime(), index=True)
    idEvento = Column(String, index=True)
    idEventoRetif = Column(String, index=True)
    retificador = Column(Boolean)
    ip = Column(String, index=True)
    hash = Column(String, index=True)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(BaseDumpable).keys()
        ])
        super().__init__(**superkwargs)
        self.cnpjTransmissor = kwargs.get('cnpjTransmissor')
        self.codRecinto = kwargs.get('codRecinto')
        self.contingencia = kwargs.get('contingencia')
        self.cpfOperOcor = kwargs.get('cpfOperOcor')
        self.cpfOperReg = kwargs.get('cpfOperReg')
        if kwargs.get('dtHrOcorrencia') is not None:
            self.dtHrOcorrencia = parse(kwargs.get('dtHrOcorrencia'))
        if kwargs.get('dtHrTransmissao') is not None:
            self.dtHrTransmissao = parse(kwargs.get('dtHrTransmissao'))
        if kwargs.get('dtHrRegistro') is not None:
            self.dtHrRegistro = parse(kwargs.get('dtHrRegistro'))
        self.idEvento = kwargs.get('idEvento')
        self.idEventoRetif = kwargs.get('idEventoRetif')
        self.retificador = kwargs.get('retificador')
        self.ip = kwargs.get('ip')
        self.hash = kwargs.get('hash')


class PesagemVeiculoCarga(EventoBase):
    __tablename__ = 'pesagensveiculocarga'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placaCavalo = Column(String(7))
    taraConjunto = Column(Integer())
    pesoBrutoManifesto = Column(Integer())
    pesoBrutoBalanca = Column(Integer())
    capturaAutoPeso = Column(Boolean())
    Dutos = Column(String)
    idBalanca = Column(String)
    idCamera = Column(String)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.placaCavalo = kwargs.get('placaCavalo')
        self.taraConjunto = kwargs.get('taraConjunto')
        self.pesoBrutoManifesto = kwargs.get('pesoBrutoManifesto')
        self.pesoBrutoBalanca = kwargs.get('pesoBrutoBalanca')
        self.capturaAutoPeso = kwargs.get('capturaAutoPeso')
        self.Dutos = kwargs.get('Dutos')
        self.idCamera = kwargs.get('idCamera')
        self.idBalanca = kwargs.get('idBalanca')


class ReboquePesagemVeiculoCarga(BaseDumpable):
    __tablename__ = 'reboquespesagemveiculocarga'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    tara = Column(Integer)
    pesagem_id = Column(Integer, ForeignKey('pesagensveiculocarga.ID'))
    pesagem = relationship(
        'PesagemVeiculoCarga', backref=backref('listaSemirreboque')
    )


class ConteinerPesagemVeiculoCarga(BaseDumpable):
    __tablename__ = 'conteinerespesagemveiculocarga'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(7))
    tara = Column(Integer)
    pesagem_id = Column(Integer, ForeignKey('pesagensveiculocarga.ID'))
    pesagem = relationship(
        'PesagemVeiculoCarga', backref=backref('listaConteineresUld')
    )


class ManifestoPesagemVeiculoCarga(Manifesto):
    __tablename__ = 'listamanifestospesagem'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    pesagem_id = Column(Integer, ForeignKey('pesagensveiculocarga.ID'))
    pesagem = relationship(
        'PesagemVeiculoCarga', backref=backref('listaManifestos')
    )

    def __init__(self, **kwargs):
        self.num = kwargs.get('num')
        self.tipo = kwargs.get('tipo')
        self.pesagem_id = kwargs.get('pesagem_id')


class InspecaonaoInvasiva(EventoBase):
    __tablename__ = 'inspecoesnaoinvasivas'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(8))
    ocrPlaca = Column(Boolean)
    idCamera = Column(Integer)
    idScanner = Column(Integer)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.placa = kwargs.get('placa')
        self.ocrPlaca = kwargs.get('ocrPlaca')
        self.idCamera = kwargs.get('idCamera')
        self.idScanner = kwargs.get('idScanner')


class AnexoBase(BaseDumpable):
    __abstract__ = True
    nomeArquivo = Column(String(100), default='')
    contentType = Column(String(40), default='')

    def __init__(self, nomeArquivo='', contentType=''):
        self.nomeArquivo = nomeArquivo
        self.contentType = contentType

    def monta_caminho_arquivo(self, basepath, eventobase):
        filepath = basepath
        for caminho in [eventobase.codRecinto,
                        eventobase.dtHrOcorrencia.year,
                        eventobase.dtHrOcorrencia.month,
                        eventobase.dtHrOcorrencia.day]:
            filepath = os.path.join(filepath, str(caminho))
            if not os.path.exists(filepath):
                print('making dir %s' % filepath)
                os.mkdir(filepath)
        return filepath

    def save_file(self, basepath, file, filename, evento) -> (str, bool):
        """

        :param basepath: diretorio onde guardar arquivos
        :param file: objeto arquivo
        :return:
            mensagem de sucesso ou mensagem de erro
            True se sucesso, False se houve erro
        """
        if filename is None:
            if self.nomeArquivo:
                filename = self.nomeArquivo
        if not file:
            raise AttributeError('Arquivo vazio')
        if not filename:
            raise AttributeError('Nome arquivo não informado!')
        filepath = self.monta_caminho_arquivo(
            basepath, evento)
        try:
            with open(os.path.join(filepath, filename), 'wb') as file_out:
                try:
                    file = b64decode(file.encode())
                except AttributeError:
                    pass
                file_out.write(file)
        except FileNotFoundError as err:
            logging.error(str(err), exc_info=True)
            raise (err)
        self.contentType = mimetypes.guess_type(filename)[0]
        self.nomeArquivo = filename
        return 'Arquivo salvo no anexo'

    def load_file(self, basepath, evento):
        if not self.nomeArquivo:
            return ''
        try:
            filepath = self.monta_caminho_arquivo(basepath, evento)
            content = open(os.path.join(filepath, self.nomeArquivo), 'rb')
            base64_bytes = b64encode(content.read())
            base64_string = base64_bytes.decode('utf-8')
        except FileNotFoundError as err:
            logging.error(str(err), exc_info=True)
            base64_string = None
        self.content = base64_string


class AnexoInspecao(AnexoBase):
    __tablename__ = 'anexosinspecao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    dtHrModifArquivo = Column(DateTime())
    dtHrScaneamento = Column(DateTime())
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('anexos')
    )

    # TODO: Fazer coordenadas
    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(AnexoBase).keys()
        ])
        super().__init__(**superkwargs)
        if kwargs.get('datacriacao') is not None:
            self.datacriacao = parse(kwargs.get('datacriacao'))
        if kwargs.get('datamodificacao') is not None:
            self.datamodificacao = parse(kwargs.get('datamodificacao'))
        self.inspecao = kwargs.get('inspecao')

    def save_file(self, basepath, file, filename=None) -> (str, bool):
        return super().save_file(basepath, file, filename, self.inspecao)

    def load_file(self, basepath):
        return super().load_file(basepath, self.inspecao)

    @classmethod
    def create(cls, parent):
        return AnexoInspecao(inspecao=parent)


class CoordenadasAlerta(BaseDumpable):
    __tablename__ = 'coordenadasanexoinspecao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    x = Column(Integer)
    y = Column(Integer)
    x2 = Column(Integer)
    y2 = Column(Integer)
    anexo_id = Column(Integer, ForeignKey('anexosinspecao.ID'))
    anexo = relationship(
        'AnexoInspecao', backref=backref('coordenadasAlerta')
    )


class IdentificadorInspecao(BaseDumpable):
    __tablename__ = 'identificadoresinspecao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    identificador = Column(String(100))
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('identificadores')
    )


class ConteinerUld(BaseDumpable):
    __tablename__ = 'listaconteineresuldinspecao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(100))
    ocrNum = Column(Boolean)
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('listaConteineresUld')
    )


class Semirreboque(BaseDumpable):
    __tablename__ = 'listasemirreboquesinspecao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(100))
    ocrPlaca = Column(Boolean)
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('listaSemirreboque')
    )


class ManifestoInspecaonaoInvasiva(Manifesto):
    __tablename__ = 'listamanifestos'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('listaManifestos')
    )

    def __init__(self, **kwargs):
        self.num = kwargs.get('num')
        self.tipo = kwargs.get('tipo')
        self.inspecao_id = kwargs.get('inspecao_id')


class AcessoVeiculo(EventoBase):
    __tablename__ = 'acessosveiculo'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    direcao = Column(String(10))
    idAgendamento = Column(Integer)
    tipoGranel = Column(String)
    placa = Column(String(8))
    ocrPlaca = Column(Boolean)
    CpfMotorista = Column(String(11))
    nmMotorista = Column(String(50))
    cnpjTransportador = Column(String(14))
    nmTransportador = Column(String(50))
    modal = Column(String(20))
    oogPeso = Column(Boolean)
    oogDimensao = Column(Boolean)
    codRecintoDestino = Column(String)
    idGate = Column(String)
    idCamera = Column(String)


    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.direcao = kwargs.get('direcao')
        self.idAgendamento = kwargs.get('idAgendamento')
        self.tipoGranel = kwargs.get('tipoGranel')
        self.placa = kwargs.get('placa')
        self.ocrPlaca = kwargs.get('ocrPlaca')
        self.cpfMotorista = kwargs.get('cpfMotorista')
        self.nmMotorista = kwargs.get('nmMotorista')
        self.cnpjTransportador = kwargs.get('cnpjTransportador')
        self.nmTransportador = kwargs.get('nmTransportador')
        self.modal = kwargs.get('modal')
        self.oogPeso = kwargs.get('oogPeso')
        self.oogDimensao = kwargs.get('oogDimensao')
        self.codRecintoDestino = kwargs.get('codRecintoDestino')
        self.idGate = kwargs.get('idGate')
        self.idCamera = kwargs.get('idCamera')


class ConteineresGate(BaseDumpable):
    __tablename__ = 'conteineresgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(11))
    tipo = Column(String)
    ocrNum = Column(Boolean)
    vazio = Column(Boolean)
    numBooking = Column(String(30))
    portoDescarga = Column(String(30))
    destinoCarga = Column(String(30))
    imoNavio = Column(String(30))
    cnpjCliente = Column(String(14))
    nmCliente = Column(String(30))
    avarias = Column(String(100))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaConteineresUld')
    )

    def __init__(self, **kwargs):
        self.acessoveiculo_id = kwargs.get('acessoveiculo_id')
        self.num = kwargs.get('num')
        self.tipo = kwargs.get('tipo')
        self.ocrNum = kwargs.get('ocrNum')
        self.vazio = kwargs.get('vazio')
        self.numBooking = kwargs.get('numBooking')
        self.portoDescarga = kwargs.get('portoDescarga')
        self.destinoCarga = kwargs.get('destinoCarga')
        self.imoNavio = kwargs.get('imoNavio')
        self.cnpjCliente = kwargs.get('cnpjCliente')
        self.nmCliente = kwargs.get('nmCliente')
        self.avarias = kwargs.get('avarias')


class ReboqueGate(BaseDumpable):
    __tablename__ = 'reboquesgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String)
    ocrPlaca = Column(Boolean())
    vazio = Column(Boolean())
    cnpjCliente = Column(String(14))
    nmCliente = Column(String(50))
    avarias = Column(String(50))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaSemirreboque')
    )

    def __init__(self, **kwargs):
        self.acessoveiculo_id = kwargs.get('acessoveiculo_id')
        self.placa = kwargs.get('placa')
        self.ocrPlaca = kwargs.get('ocrPlaca')
        self.vazio = kwargs.get('vazio')
        self.cnpjCliente = kwargs.get('cnpjCliente')
        self.nmCliente = kwargs.get('nmCliente')
        self.avarias = kwargs.get('avarias')


class Lacre(BaseDumpable):
    __abstract__ = True
    num = Column(String)
    tipo = Column(String)
    localSif = Column(String)


class LacreReboque(Lacre):
    __tablename__ = 'lacresreboquegate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    reboquegate_id = Column(Integer, ForeignKey('reboquesgate.ID'))
    reboquegate = relationship(
        'ReboqueGate', backref=backref('listaLacres')
    )


class LacreConteiner(Lacre):
    __tablename__ = 'lacresconteineresgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    conteineresgate_id = Column(Integer, ForeignKey('conteineresgate.ID'))
    conteineresgate = relationship(
        'ConteineresGate', backref=backref('listaLacres')
    )


class ManifestoGate(Manifesto):
    __tablename__ = 'listamanifestosgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaManifestos')
    )

    def __init__(self, **kwargs):
        self.num = kwargs.get('num')
        self.tipo = kwargs.get('tipo')
        self.acessoveiculo_id = kwargs.get('acessoveiculo_id')


class DiDueGate(BaseDumpable):
    __tablename__ = 'listadiduegate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(100))
    tipo = Column(String)
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaDiDue')
    )


class ChassiGate(BaseDumpable):
    __tablename__ = 'listachassigate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(50))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaChassi')
    )

    def __init__(self, acessoveiculo_id, num):
        self.acessoveiculo_id = acessoveiculo_id
        self.num = num


class NfeGate(BaseDumpable):
    __tablename__ = 'listanfegate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    chavenfe = Column(String(30))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listaNfe')
    )


def init_db(uri='sqlite:///test.db'):
    global db_session
    global engine
    if db_session is None:
        print('Conectando banco %s' % uri)
        engine = create_engine(uri)
        db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                                 bind=engine))
        Base.query = db_session.query_property()
        for table in ['pesagensveiculocarga', 'acessosveiculo',
                      'inspecoesnaoinvasivas']:
            # print(table)
            Table(table, Base.metadata,
                  Index(table + '_ideventorecinto_idx',
                        'codRecinto', 'idEvento',
                        unique=True,
                        ),
                  extend_existing=True
                  )
    return db_session, engine


