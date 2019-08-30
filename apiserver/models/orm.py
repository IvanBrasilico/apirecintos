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


class PesagemTerrestre(EventoBase):
    __tablename__ = 'pesagensterrestres'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    placa = Column(String(7))
    tara = Column(Integer())
    pesobrutodeclarado = Column(Integer())
    pesobalanca = Column(Integer())
    capturaautomatica = Column(Boolean())
    # reboques = relationship('ReboquePesagemTerrestre')
    conteineres = relationship('ConteinerPesagemTerrestre')

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.documentotransporte = kwargs.get('documentotransporte')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.placa = kwargs.get('placa')
        self.tara = kwargs.get('tara')
        self.pesobrutodeclarado = kwargs.get('pesobrutodeclarado')
        self.pesobalanca = kwargs.get('pesobalanca')
        self.capturaautomatica = kwargs.get('capturaautomatica')


class ReboquePesagemTerrestre(BaseDumpable):
    __tablename__ = 'reboquespesagemterrestre'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    tara = Column(Integer)
    pesagem_id = Column(Integer, ForeignKey('pesagensterrestres.ID'))
    pesagem = relationship(
        'PesagemTerrestre', backref=backref('reboques')
    )

    # def __init__(self, **kwargs):
    #    self.placa = kwargs.get('placa')
    #    self.tara = kwargs.get('tara')


class ConteinerPesagemTerrestre(BaseDumpable):
    __tablename__ = 'conteinerespesagemterrestre'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numero = Column(String(11))
    tara = Column(Integer)
    pesagem_id = Column(Integer, ForeignKey('pesagensterrestres.ID'))
    pesagem = relationship(
        'PesagemTerrestre'
    )

    # def __init__(self, **kwargs):
    #    self.numero = kwargs.get('numero')
    #    self.tara = kwargs.get('tara')


class PesagemVeiculoVazio(EventoBase):
    __tablename__ = 'pesagensveiculosvazios'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    pesobalanca = Column(Integer())

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.placa = kwargs.get('placa')
        self.pesobalanca = kwargs.get('pesobalanca')


class ReboquesPesagem(BaseDumpable):
    __tablename__ = 'reboquespesagem'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    pesagem_id = Column(Integer, ForeignKey('pesagensveiculosvazios.ID'))
    pesagem = relationship(
        'PesagemVeiculoVazio', backref=backref('reboques')
    )


class PesagemVeiculoCarga(EventoBase):
    __tablename__ = 'pesagensmaritimo'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    numero = Column(String(11))
    placa = Column(String(7))
    placasemireboque = Column(String(11))
    pesobrutodeclarado = Column(Integer())
    taraconjunto = Column(Integer())
    pesobalanca = Column(Integer())
    capturaautomatica = Column(Boolean())

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.documentotransporte = kwargs.get('documentotransporte')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.numero = kwargs.get('numero')
        self.placa = kwargs.get('placa')
        self.placasemireboque = kwargs.get('placasemireboque')
        self.pesobrutodeclarado = kwargs.get('pesobrutodeclarado')
        self.taraconjunto = kwargs.get('taraconjunto')
        self.pesobalanca = kwargs.get('pesobalanca')
        self.capturaautomatica = kwargs.get('capturaautomatica')


class InspecaonaoInvasiva(EventoBase):
    __tablename__ = 'inspecoesnaoinvasivas'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    idCamera = Column(Integer)
    idScanner = Column(Integer)
    placa = Column(String(8))
    ocrPlaca = Column(Boolean)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.idCamera = kwargs.get('idCamera')
        self.idScanner = kwargs.get('idScanner')
        self.placa = kwargs.get('placa')
        self.ocrPlaca = kwargs.get('ocrPlaca')


class AnexoBase(BaseDumpable):
    __abstract__ = True
    nomearquivo = Column(String(100), default='')
    contentType = Column(String(40), default='')

    def __init__(self, nomearquivo='', contentType=''):
        self.nomearquivo = nomearquivo
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
            if self.nomearquivo:
                filename = self.nomearquivo
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
        self.nomearquivo = filename
        return 'Arquivo salvo no anexo'

    def load_file(self, basepath, evento):
        if not self.nomearquivo:
            return ''
        try:
            filepath = self.monta_caminho_arquivo(basepath, evento)
            content = open(os.path.join(filepath, self.nomearquivo), 'rb')
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
    datacriacao = Column(DateTime())
    datamodificacao = Column(DateTime())
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('anexos')
    )

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
        'InspecaonaoInvasiva', backref=backref('listaSemirreboques')
    )

class Manifesto(BaseDumpable):
    __tablename__ = 'listamanifestos'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    num = Column(String(100))
    tipo = Column(String)
    inspecao_id = Column(Integer, ForeignKey('inspecoesnaoinvasivas.ID'))
    inspecao = relationship(
        'InspecaonaoInvasiva', backref=backref('listaManifestos')
    )

    def __init__(self, **kwargs):
        self.num = kwargs.get('num')
        self.tipo = kwargs.get('tipo')



class AcessoVeiculo(EventoBase):
    __tablename__ = 'acessosveiculo'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    IDAgendamento = Column(Integer)
    IDGate = Column(String(20))
    tipodocumentotransporte = Column(String(20))
    documentotransporte = Column(String(20))
    placa = Column(String(7))
    ocr = Column(Boolean)
    chassi = Column(String(30))
    cpfmotorista = Column(String(11))
    nomemotorista = Column(String(50))
    cpfcnpjtransportador = Column(String(14))
    nometransportador = Column(String(50))
    modal = Column(String(20))
    pesoespecial = Column(Boolean)
    dimensaoespecial = Column(Boolean)
    tipooperacao = Column(String(10))
    dataliberacao = Column(DateTime)
    dataagendamento = Column(DateTime)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.IDAgendamento = kwargs.get('IDAgendamento')
        self.IDGate = kwargs.get('IDGate')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.documentotransporte = kwargs.get('documentotransporte')
        self.placa = kwargs.get('placa')
        self.ocr = kwargs.get('ocr')
        self.chassi = kwargs.get('chassi')
        self.cpfmotorista = kwargs.get('cpfmotorista')
        self.nomemotorista = kwargs.get('nomemotorista')
        self.cpfcnpjtransportador = kwargs.get('cpfcnpjtransportador')
        self.nometransportador = kwargs.get('nometransportador')
        self.modal = kwargs.get('modal')
        self.pesoespecial = kwargs.get('pesoespecial')
        self.dimensaoespecial = kwargs.get('dimensaoespecial')
        self.tipooperacao = kwargs.get('tipooperacao')
        if kwargs.get('dataliberacao') is not None:
            self.dataliberacao = parse(kwargs.get('dataliberacao'))
        if kwargs.get('dataagendamento') is not None:
            self.dataagendamento = parse(kwargs.get('dataagendamento'))


class Gate(BaseDumpable):
    __abstract__ = True
    avarias = Column(String(50))
    lacres = Column(String(50))
    vazio = Column(Boolean())


class ConteineresGate(Gate):
    __tablename__ = 'conteineresgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numero = Column(String(11))
    vazio = Column(Boolean)
    lacres = Column(String(30))
    lacresverificados = Column(String(30))
    localsif = Column(String(20))
    lacressif = Column(String(30))
    lacressifverificados = Column(String(30))
    portodescarga = Column(String(30))
    paisdestino = Column(String(30))
    navioembarque = Column(String(30))
    numerobooking = Column(String(30))
    avarias = Column(String(100))
    cpfcnpjcliente = Column(String(14))
    nomecliente = Column(String(30))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('conteineres')
    )


class ReboquesGate(Gate):
    __tablename__ = 'reboquesgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    vazio = Column(Boolean)
    lacres = Column(String(30))
    lacresverificados = Column(String(30))
    localsif = Column(String(20))
    lacressif = Column(String(30))
    lacressifverificados = Column(String(30))
    cnpjestadia = Column(String(14))
    nomeestadia = Column(String(50))
    avarias = Column(String(100))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('reboques')
    )


class ListaNfeGate(BaseDumpable):
    __tablename__ = 'listanfegate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    chavenfe = Column(String(30))
    acessoveiculo_id = Column(Integer, ForeignKey('acessosveiculo.ID'))
    acessoveiculo = relationship(
        'AcessoVeiculo', backref=backref('listanfe')
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
        for table in ['pesagensterrestres', 'pesagensveiculosvazios',
                      'acessosveiculo', 'pesagensmaritimo', 'inspecoesnaoinvasivas']:
            # print(table)
            Table(table, Base.metadata,
                  Index(table + '_ideventorecinto_idx',
                        'codRecinto', 'idEvento',
                        unique=True,
                        ),
                  extend_existing=True
                  )
    return db_session, engine
