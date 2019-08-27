import collections
import datetime
import logging
import mimetypes
import os
from base64 import b64decode, b64encode

from dateutil.parser import parse
from marshmallow import fields, ValidationError
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy import Boolean, Column, DateTime, Integer, \
    String, create_engine, ForeignKey, Index, Table, Float
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
    IDEvento = Column(Integer, index=True)
    dataevento = Column(DateTime(), index=True)
    operadorevento = Column(String(14), index=True)
    dataregistro = Column(DateTime(), index=True)
    operadorregistro = Column(String(14), index=True)
    time_created = Column(DateTime(timezone=True),
                          index=True)
    recinto = Column(String(10), index=True)
    request_IP = Column(String(21), index=True)
    # TODO: Ver como tratar retificação (viola índice único)
    retificador = Column(Boolean)

    def __init__(self, IDEvento, dataevento, operadorevento, dataregistro,
                 operadorregistro, retificador,
                 time_created=None, recinto=None, request_IP=None):
        self.IDEvento = IDEvento
        # print(dataevento)
        # print(parse(dataevento))
        self.dataevento = parse(dataevento)
        self.operadorevento = operadorevento
        self.dataregistro = parse(dataregistro)
        self.operadorregistro = operadorregistro
        self.retificador = retificador
        self.time_created = datetime.datetime.utcnow()

        if recinto is not None:
            self.recinto = recinto
        if request_IP is not None:
            self.request_IP = request_IP


class PosicaoConteiner(EventoBase):
    __tablename__ = 'posicoesconteiner'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numero = Column(String(11))
    placa = Column(String(7))
    posicao = Column(String(20))
    altura = Column(Integer())
    emconferencia = Column(Boolean())
    solicitante = Column(String(10))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.numero = kwargs.get('numero')
        self.placa = kwargs.get('placa')
        self.posicao = kwargs.get('posicao')
        self.altura = kwargs.get('altura')
        self.emconferencia = kwargs.get('emconferencia')
        self.solicitante = kwargs.get('solicitante')


class AcessoPessoa(EventoBase):
    __tablename__ = 'acessospessoas'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    direcao = Column(String(10))
    formaidentificacao = Column(String(10))
    cpf = Column(String(11))
    identidade = Column(String(15))
    portaoacesso = Column(String(10))
    numerovoo = Column(String(20))
    reserva = Column(String(20))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.direcao = kwargs.get('direcao')
        self.formaidentificacao = kwargs.get('formaidentificacao')
        self.cpf = kwargs.get('cpf')
        self.identidade = kwargs.get('identidade')
        self.portaoacesso = kwargs.get('portaoacesso')
        self.numerovoo = kwargs.get('numerovoo')
        self.reserva = kwargs.get('reserva')


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


class PesagemTerrestreSchema(ModelSchema):
    conteineres = fields.Nested('ConteinerPesagemTerrestreSchema', many=True,
                                exclude=('ID', 'pesagem'))
    reboques = fields.Nested('ReboquePesagemTerrestreSchema', many=True,
                             exclude=('ID', 'pesagem'))

    class Meta:
        model = PesagemTerrestre


class ConteinerPesagemTerrestreSchema(ModelSchema):
    class Meta:
        model = ConteinerPesagemTerrestre


class ReboquePesagemTerrestreSchema(ModelSchema):
    class Meta:
        model = ReboquePesagemTerrestre


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


class PesagemMaritimo(EventoBase):
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
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(20))
    numero = Column(String(11))
    placa = Column(String(8))
    placasemireboque = Column(String(8))
    capturaautomatica = Column(Boolean)

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
        self.capturaautomatica = kwargs.get('capturaautomatica')


class AnexoBase(BaseDumpable):
    __abstract__ = True
    nomearquivo = Column(String(100), default='')
    contentType = Column(String(40), default='')

    def __init__(self, nomearquivo='', contentType=''):
        self.nomearquivo = nomearquivo
        self.contentType = contentType

    def monta_caminho_arquivo(self, basepath, eventobase):
        filepath = basepath
        for caminho in [eventobase.recinto,
                        eventobase.dataevento.year,
                        eventobase.dataevento.month,
                        eventobase.dataevento.day]:
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


class PosicaoLote(EventoBase):
    __tablename__ = 'posicoeslote'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numerolote = Column(Integer)
    posicao = Column(String(10))
    qtdevolumes = Column(Integer)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.numerolote = kwargs.get('numerolote')
        self.posicao = kwargs.get('posicao')
        self.qtdevolumes = kwargs.get('qtdevolumes')


class Unitizacao(EventoBase):
    __tablename__ = 'unitizacoes'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    numero = Column(String(11))
    placa = Column(String(7))
    placasemireboque = Column(String(11))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        # self.ID = kwargs.get('IDEvento')
        self.documentotransporte = kwargs.get('documentotransporte')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.numero = kwargs.get('numero')
        self.placa = kwargs.get('placa')
        self.placasemireboque = kwargs.get('placasemireboque')


class ImagemUnitizacao(BaseDumpable):
    __tablename__ = 'imagensunitizacao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    caminhoarquivo = Column(String(100))
    content = Column(String(1))
    contentType = Column(String(40))
    datacriacao = Column(DateTime())
    datamodificacao = Column(DateTime())
    unitizacao_id = Column(Integer, ForeignKey('unitizacoes.ID'))
    unitizacao = relationship(
        'Unitizacao', backref=backref('imagens')
    )


class LoteUnitizacao(BaseDumpable):
    __tablename__ = 'lotesunitizacao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numerolote = Column(String(10))
    qtdevolumes = Column(Integer)
    unitizacao_id = Column(Integer, ForeignKey('unitizacoes.ID'))
    unitizacao = relationship(
        'Unitizacao', backref=backref('lotes')
    )


class AvariaLote(EventoBase):
    __tablename__ = 'avariaslote'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numerolote = Column(Integer)
    descricaoavaria = Column(String(50))
    qtdevolumes = Column(Integer)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.numerolote = kwargs.get('numerolote')
        self.descricaoavaria = kwargs.get('descricaoavaria')
        self.qtdevolumes = kwargs.get('qtdevolumes')


class OperacaoNavio(EventoBase):
    __tablename__ = 'operacoesnavios'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    direcao = Column(String(10), index=True)
    imonavio = Column(String(7), index=True)
    viagem = Column(String(7))
    numero = Column(String(11))
    pesomanifestado = Column(Integer)
    pesovgm = Column(Integer)
    porto = Column(String(5))
    posicao = Column(String(10))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.direcao = kwargs.get('direcao')
        self.imonavio = kwargs.get('imonavio')
        self.viagem = kwargs.get('viagem')
        self.numero = kwargs.get('numero')
        self.pesomanifestado = kwargs.get('pesomanifestado')
        self.pesovgm = kwargs.get('pesovgm')
        self.imonavio = kwargs.get('imonavio')
        self.porto = kwargs.get('porto')
        self.posicao = kwargs.get('posicao')


class DTSC(EventoBase):
    __tablename__ = 'DTSC'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    imonavio = Column(String(7), index=True)
    viagem = Column(String(7))
    dataoperacao = Column(DateTime(), index=True)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.imonavio = kwargs.get('imonavio')
        self.viagem = kwargs.get('viagem')
        self.dataoperacao = parse(kwargs.get('dataoperacao'))


class CargaDTSC(BaseDumpable):
    __tablename__ = 'cargasDTSC'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    numero = Column(String(11))
    codigorecinto = Column(String(7))
    cpfcnpjproprietario = Column(String(15))
    cpfcnpjtransportador = Column(String(15))
    documentotransporte = Column(String(10))
    placasemireboque = Column(String(7))
    tipodocumentotransporte = Column(String(10))
    DTSC_id = Column(Integer, ForeignKey('DTSC.ID'))
    DTSC = relationship(
        'DTSC', backref=backref('cargas')
    )


class AgendamentoAcessoVeiculo(EventoBase):
    __tablename__ = 'agendamentosacessoveiculo'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    tipooperacao = Column(String(10))
    tipodocumentotransporte = Column(String(20))
    documentotransporte = Column(String(20))
    pesoespecial = Column(Boolean)
    dimensaoespecial = Column(Boolean)
    placa = Column(String(7))
    chassi = Column(String(30))
    cpfmotorista = Column(String(11))
    nomemotorista = Column(String(50))
    cpfcnpjtransportador = Column(String(14))
    nometransportador = Column(String(50))
    modal = Column(String(20))
    dataagendada = Column(DateTime)
    areasacesso = Column(String(100))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.tipooperacao = kwargs.get('tipooperacao')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.pesoespecial = kwargs.get('pesoespecial')
        self.dimensaoespecial = kwargs.get('dimensaoespecial')
        self.documentotransporte = kwargs.get('documentotransporte')
        self.placa = kwargs.get('placa')
        self.chassi = kwargs.get('chassi')
        self.cpfmotorista = kwargs.get('cpfmotorista')
        self.nomemotorista = kwargs.get('nomemotorista')
        self.cpfcnpjtransportador = kwargs.get('cpfcnpjtransportador')
        self.nometransportador = kwargs.get('nometransportador')
        self.modal = kwargs.get('modal')
        if kwargs.get('dataagendada') is not None:
            self.dataagendada = parse(kwargs.get('dataagendada'))
        self.areasacesso = kwargs.get('areasacesso')


class GateAgendado(BaseDumpable):
    __abstract__ = True
    lacres = Column(String(50))
    lacressif = Column(String(50))
    localsif = Column(String(50))
    vazio = Column(Boolean())


class ConteineresGateAgendado(GateAgendado):
    __tablename__ = 'conteineresgateagendado'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numero = Column(String(11))
    portodescarga = Column(String(30))
    paisdestino = Column(String(30))
    navioembarque = Column(String(30))
    cpfcnpjcliente = Column(String(14))
    nomecliente = Column(String(30))
    agendamentoacessoveiculo_id = Column(
        Integer,
        ForeignKey('agendamentosacessoveiculo.ID'))
    agendamentoacessoveiculo = relationship(
        'AgendamentoAcessoVeiculo', backref=backref('conteineres')
    )


class ReboquesGateAgendado(GateAgendado):
    __tablename__ = 'agendamentoreboquesgate'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    cnpjestadia = Column(String(14))
    nomeestadia = Column(String(50))
    agendamentoacessoveiculo_id = Column(
        Integer,
        ForeignKey('agendamentosacessoveiculo.ID'))
    agendamentoacessoveiculo = relationship(
        'AgendamentoAcessoVeiculo', backref=backref('reboques')
    )


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


class PosicaoVeiculo(EventoBase):
    __tablename__ = 'posicoesveiculo'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    box = Column(String(20))
    camera = Column(String(20))
    divergencia = Column(Boolean)
    emconferencia = Column(Boolean)
    observacaodivergencia = Column(String(100))
    solicitante = Column(String(20))
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(20))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.placa = kwargs.get('placa')
        self.box = kwargs.get('box')
        self.camera = kwargs.get('camera')
        self.divergencia = kwargs.get('divergencia')
        self.emconferencia = kwargs.get('emconferencia')
        self.observacaodivergencia = kwargs.get('observacaodivergencia')
        self.solicitante = kwargs.get('solicitante')
        self.documentotransporte = kwargs.get('documentotransporte')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')


class ConteinerPosicao(BaseDumpable):
    __tablename__ = 'conteineresposicao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numero = Column(String(11))
    vazio = Column(Boolean)
    posicaoveiculo_id = Column(Integer, ForeignKey('posicoesveiculo.ID'))
    posicaoveiculo = relationship(
        'PosicaoVeiculo', backref=backref('conteineres')
    )


class ReboquePosicao(BaseDumpable):
    __tablename__ = 'reboquesposicao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(7))
    vazio = Column(Boolean)
    posicaoveiculo_id = Column(Integer, ForeignKey('posicoesveiculo.ID'))
    posicaoveiculo = relationship(
        'PosicaoVeiculo', backref=backref('reboques')
    )


class Desunitizacao(EventoBase):
    __tablename__ = 'desunitizacoes'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    numero = Column(String(11))
    placa = Column(String(7))
    placasemireboque = Column(String(11))

    # imagens = relationship('ImagemDesunitizacao')
    # lotes = relationship('Lote')

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


class ImagemDesunitizacao(BaseDumpable):
    __tablename__ = 'imagensdesunitizacao'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    caminhoarquivo = Column(String(100))
    content = Column(String(1))
    contentType = Column(String(40))
    datacriacao = Column(DateTime())
    datamodificacao = Column(DateTime())
    desunitizacao_id = Column(Integer, ForeignKey('desunitizacoes.ID'))
    desunitizacao = relationship(
        'Desunitizacao', backref=backref('imagens')
    )


class Lote(BaseDumpable):
    __tablename__ = 'lotes'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    numerolote = Column(String(10))
    acrescimo = Column(Boolean)
    documentodesconsolidacao = Column(String(20))
    tipodocumentodesconsolidacao = Column(String(20))
    documentopapel = Column(String(20))
    tipodocumentopapel = Column(String(20))
    falta = Column(Boolean)
    marca = Column(String(100))
    observacoes = Column(String(100))
    pesolote = Column(Integer)
    qtdefalta = Column(Integer)
    qtdevolumes = Column(Integer)
    tipovolume = Column(String(20))
    desunitizacao_id = Column(Integer, ForeignKey('desunitizacoes.ID'))
    desunitizacao = relationship(
        'Desunitizacao', backref=backref('lotes')
    )


class DesunitizacaoSchema(ModelSchema):
    lotes = fields.Nested('LoteSchema', many=True,
                          exclude=('ID', 'desunitizacao'))
    imagens = fields.Nested('ImagemDesunitizacaoSchema', many=True,
                            exclude=('ID', 'desunitizacao'))

    class Meta:
        model = Desunitizacao


class LoteSchema(ModelSchema):
    class Meta:
        model = Lote


class ImagemDesunitizacaoSchema(ModelSchema):
    class Meta:
        model = ImagemDesunitizacao


# SCHEMAS

# Custom validator
def must_not_be_blank(data):
    if not data:
        raise ValidationError('Data not provided.')


# Entidades de cadastro
# Entidades de cadastro têm um comportamento diferente

class Cadastro(BaseDumpable):
    __abstract__ = True
    ativo = Column(Boolean(), index=True, default=True)
    fim = Column(DateTime(), index=True)

    def inativar(self):
        if self.ativo is True:
            # TODO: Criar / gerar evento para inativacao
            # (Salvar em uma tabela as datas de ativacao e inativacao)
            self.fim = datetime.datetime.utcnow()
            self.ativo = False
        else:
            raise Exception('Cadastro já foi inativado em %s' %
                            datetime.datetime.strftime(self.fim,
                                                       '%d/%m/%Y %H:%M'))


class CadastroRepresentacao(EventoBase, Cadastro):
    __tablename__ = 'representacoes'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    cpfrepresentante = Column(String(11), index=True)
    cpfcnpjrepresentado = Column(String(14), index=True)
    inicio = Column(DateTime(), index=True)

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.cpfrepresentante = kwargs.get('cpfrepresentante')
        self.cpfcnpjrepresentado = kwargs.get('cpfcnpjrepresentado')
        self.inicio = parse(kwargs.get('inicio'))
        self.fim = parse(kwargs.get('fim'))


class CredenciamentoPessoa(EventoBase, Cadastro):
    __tablename__ = 'credenciamentopessoas'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    cpf = Column(String(11), index=True)
    identidade = Column(String(15), index=True)
    cnh = Column(String(15), index=True)
    nome = Column(String(50), index=True)
    datanascimento = Column(DateTime)
    telefone = Column(String(20))
    cpfcnpjrepresentado = Column(String(14), index=True)
    nomerepresentado = Column(String(50), index=True)
    funcao = Column(String(40))
    iniciovalidade = Column(DateTime(), index=True)
    fimvalidade = Column(DateTime(), index=True)
    horaentrada = Column(Integer)
    horasaida = Column(Integer)
    permissao = Column(String(100))
    materiais = Column(String(100))
    motivacao = Column(String(100))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.cpf = kwargs.get('cpf')
        self.identidade = kwargs.get('identidade')
        self.cnh = kwargs.get('cnh')
        self.nome = kwargs.get('nome')
        self.nascimento = kwargs.get('nascimento')
        self.telefone = kwargs.get('telefone')
        self.cpfcnpjrepresentado = kwargs.get('cpfcnpjrepresentado')
        self.nomerepresentado = kwargs.get('nomerepresentado')
        self.funcao = kwargs.get('funcao')
        self.iniciovalidade = parse(kwargs.get('iniciovalidade'))
        self.fimvalidade = parse(kwargs.get('fimvalidade'))
        self.horaentrada = kwargs.get('horaentrada')
        self.horasaida = kwargs.get('horasaida')
        self.permissao = kwargs.get('permissao')
        self.materiais = kwargs.get('materiais')
        self.motivacao = kwargs.get('motivacao')


class FotoVeiculo(AnexoBase):
    __tablename__ = 'fotosveiculos'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    credenciamentoveiculos_id = Column(Integer, ForeignKey('credenciamentoveiculos.ID'))
    credenciamentoveiculo = relationship(
        'CredenciamentoVeiculo', backref=backref('fotos')
    )

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(AnexoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.credenciamentoveiculo = kwargs.get('credenciamentoveiculo')

    def save_file(self, basepath, file, filename=None) -> (str, bool):
        return super().save_file(basepath, file, filename, self.credenciamentoveiculo)

    def load_file(self, basepath):
        return super().load_file(basepath, self.credenciamentoveiculo)

    @classmethod
    def create(cls, parent):
        return FotoVeiculo(credenciamentoveiculo=parent)


class ReboquesVeiculo(BaseDumpable):
    __tablename__ = 'reboquesveiculos'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    placa = Column(String(11))
    credenciamentoveiculos_id = Column(Integer, ForeignKey('credenciamentoveiculos.ID'))
    credenciamentoveiculo = relationship(
        'CredenciamentoVeiculo', backref=backref('reboques')
    )

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(AnexoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.placa = kwargs.get('placa')
        self.credenciamentoveiculo = kwargs.get('credenciamentoveiculo')

    @classmethod
    def create(cls, parent):
        return ReboquesVeiculo(credenciamentoveiculo=parent)


class CredenciamentoVeiculo(EventoBase, Cadastro):
    __tablename__ = 'credenciamentoveiculos'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    cpfcnpjresponsavel = Column(String(14), index=True)
    placa = Column(String(7), index=True)
    marca = Column(String(40))
    modelo = Column(String(40))
    ano = Column(String(4))
    geolocalizacao = Column(Boolean)
    iniciovalidade = Column(DateTime(), index=True)
    fimvalidade = Column(DateTime(), index=True)
    horaentrada = Column(Integer)
    horasaida = Column(Integer)
    permissao = Column(String(100))
    motivacao = Column(String(100))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.cpfcnpjresponsavel = kwargs.get('cpfcnpjresponsavel')
        self.placa = kwargs.get('placa')
        self.marca = kwargs.get('marca')
        self.modelo = kwargs.get('modelo')
        self.ano = kwargs.get('ano')
        self.geolocalizacao = kwargs.get('geolocalizacao')
        self.iniciovalidade = parse(kwargs.get('iniciovalidade'))
        self.fimvalidade = parse(kwargs.get('fimvalidade'))
        self.horaentrada = kwargs.get('horaentrada')
        self.horasaida = kwargs.get('horasaida')
        self.permissao = kwargs.get('permissao')
        self.motivacao = kwargs.get('motivacao')


class FotoPessoa(AnexoBase):
    __tablename__ = 'fotospessoas'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    credenciamentopessoas_id = Column(Integer, ForeignKey('credenciamentopessoas.ID'))
    credenciamentopessoa = relationship(
        'CredenciamentoPessoa', backref=backref('fotos')
    )

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(AnexoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.credenciamentopessoa = kwargs.get('credenciamentopessoa')

    def save_file(self, basepath, file, filename=None) -> (str, bool):
        return super().save_file(basepath, file, filename, self.credenciamentopessoa)

    def load_file(self, basepath):
        return super().load_file(basepath, self.credenciamentopessoa)

    @classmethod
    def create(cls, parent):
        return FotoPessoa(credenciamentopessoa=parent)


class ArtefatoRecinto(EventoBase, Cadastro):
    __tablename__ = 'artefatosrecinto'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    tipoartefato = Column(String(10))
    codigo = Column(String(10))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.codigo = kwargs.get('codigo')
        self.tipoartefato = kwargs.get('tipoartefato')


class CoordenadaArtefato(BaseDumpable):
    __tablename__ = 'coordenadasartefato'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    ordem = Column(Integer)
    long = Column(Float)
    lat = Column(Float)
    artefato_id = Column(Integer, ForeignKey('artefatosrecinto.ID'))
    artefato = relationship(
        'ArtefatoRecinto', backref=backref('coordenadasartefato')
    )


class AgendamentoConferencia(EventoBase, Cadastro):
    __tablename__ = 'agendamentosconferencia'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    numero = Column(String(11))
    placa = Column(String(7))
    placasemireboque = Column(String(11))
    dataagendamento = Column(DateTime)
    artefato = Column(Integer)
    local = Column(String(20))

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
        self.dataagendamento = parse(kwargs.get('dataagendamento'))
        self.artefato = kwargs.get('artefato')
        self.local = kwargs.get('local')


class InformacaoBloqueio(EventoBase, Cadastro):
    __tablename__ = 'bloqueios'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    documentotransporte = Column(String(20))
    tipodocumentotransporte = Column(String(10))
    numero = Column(String(11))
    placa = Column(String(7))
    motivo = Column(String(20))
    tipobloqueio = Column(String(20))
    solicitante = Column(String(20))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.documentotransporte = kwargs.get('documentotransporte')
        self.tipodocumentotransporte = kwargs.get('tipodocumentotransporte')
        self.numero = kwargs.get('numero')
        self.placa = kwargs.get('placa')
        self.motivo = kwargs.get('motivo')
        self.solicitante = kwargs.get('solicitante')


class Ocorrencia(EventoBase):
    __tablename__ = 'ocorrencias'
    __table_args__ = {'sqlite_autoincrement': True}
    ID = Column(Integer, primary_key=True)
    tipoartefato = Column(String(10), index=True)
    codigo = Column(String(10), index=True)
    disponivel = Column(Boolean, index=True)
    motivo = Column(String(100))

    def __init__(self, **kwargs):
        superkwargs = dict([
            (k, v) for k, v in kwargs.items() if k in vars(EventoBase).keys()
        ])
        super().__init__(**superkwargs)
        self.tipoartefato = kwargs.get('tipoartefato')
        self.codigo = kwargs.get('codigo')
        self.disponivel = kwargs.get('disponivel')
        self.motivo = kwargs.get('motivo')


class ChavePublicaRecinto(Base):
    __tablename__ = 'chavepublicarecintos'
    recinto = Column(String(10), primary_key=True)
    public_key = Column(String(200))

    def __init__(self, recinto, public_key):
        self.recinto = recinto
        self.public_key = public_key

    @classmethod
    def get_public_key(cls, db_session, recinto):
        umrecinto = db_session.query(ChavePublicaRecinto).filter(
            ChavePublicaRecinto.recinto == recinto
        ).one()
        return umrecinto.public_key

    @classmethod
    def set_public_key(cls, db_session, recinto, public_key):
        umrecinto = ChavePublicaRecinto.query.filter(
            ChavePublicaRecinto.recinto == recinto
        ).one_or_none()
        if umrecinto is None:
            umrecinto = ChavePublicaRecinto(recinto, public_key)
        else:
            umrecinto.public_key = public_key
        db_session.add(umrecinto)
        db_session.commit()
        return umrecinto


def init_db(uri='sqlite:///test.db'):
    global db_session
    global engine
    if db_session is None:
        print('Conectando banco %s' % uri)
        engine = create_engine(uri)
        db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False,
                                                 bind=engine))
        Base.query = db_session.query_property()
        for table in ['DTSC', 'acessospessoas', 'avariaslote',
                      'pesagensterrestres', 'pesagensveiculosvazios', 'posicoeslote',
                      'posicoesveiculo', 'unitizacoes', 'acessosveiculo',
                      'pesagensmaritimo', 'posicoesconteiner', 'inspecoesnaoinvasivas',
                      'artefatosrecinto', 'ocorrencias', 'operacoesnavios',
                      'desunitizacoes', 'representacoes', 'agendamentosconferencia',
                      'credenciamentoveiculos', 'credenciamentopessoas', 'bloqueios',
                      'agendamentosacessoveiculo']:
            # print(table)
            Table(table, Base.metadata,
                  Index(table + '_ideventorecinto_idx',
                        'recinto', 'IDEvento',
                        unique=True,
                        ),
                  extend_existing=True
                  )
    return db_session, engine


if __name__ == '__main__':
    db, engine = init_db()
    try:
        print('Apagando Banco!!!')
        Base.metadata.drop_all(bind=engine)
        print('Criando Banco novo!!!')
        Base.metadata.create_all(bind=engine)
    except Exception as err:
        logging.error(err, exc_info=True)
