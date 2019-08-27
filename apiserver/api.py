import logging

from dateutil.parser import parse
from flask import current_app, request, jsonify, g
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from apiserver.logconf import logger
from apiserver.models import maschemas, orm
from apiserver.use_cases.usecases import UseCases

RECINTO = '00001'


def dump_eventos(eventos):
    eventos_dump = []
    for evento in eventos:
        evento.hash = hash(evento)
        eventos_dump.append(evento.dump())
    return jsonify(eventos_dump)


titles = {200: 'Evento encontrado',
          201: 'Evento incluido',
          400: 'Evento ou consulta invalidos (BAD Request)',
          401: 'Não autorizado',
          404: 'Evento ou recurso nao encontrado',
          409: 'Erro de integridade'}


def get_recinto():
    recinto = g.get('recinto')
    if recinto is None:
        recinto = RECINTO
    return recinto


def create_usecases():
    db_session = current_app.config['db_session']
    request_IP = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    basepath = current_app.config['UPLOAD_FOLDER']
    return UseCases(db_session, get_recinto(), request_IP, basepath)


def _response(msg, status_code, title=None):
    response = {'status': status_code}
    if isinstance(msg, Exception):
        response['type'] = msg.__class__.__name__
        response['detail'] = str(msg)
    else:
        response['detail'] = msg
    if title is None:
        title = titles[status_code]
    response['title'] = title
    return response, status_code


def _response_for_exception(exception, title=None):
    status_code = 400
    if isinstance(exception, IntegrityError):
        status_code = 409
    elif isinstance(exception, NoResultFound):
        status_code = 404
    if title is None:
        title = titles[status_code]
    response = {'detail': str(exception),
                'status': status_code,
                'title': title,
                'type': exception.__class__.__name__}
    return response, status_code


def _commit(evento):
    db_session = current_app.config['db_session']
    try:
        evento.request_IP = request.environ.get('HTTP_X_REAL_IP',
                                                request.remote_addr)
        evento.recinto = get_recinto()
        # evento.time_created = datetime.datetime.utcnow()
        db_session.flush()
        db_session.refresh(evento)
        ohash = hash(evento)
        db_session.commit()
        logger.info('Recinto: %s Classe: %s IDEvento: %d ID: %d hash: %d' %
                    (evento.recinto, evento.__class__.__name__,
                     evento.IDEvento, evento.ID, ohash))
    except IntegrityError as err:
        db_session.rollback()
        logging.error(err, exc_info=True)
        return _response('Evento repetido ou campo invalido: %s' % err,
                         409)
    except Exception as err:
        db_session.rollback()
        logging.error(err, exc_info=True)
        return _response('Erro inesperado: %s ' % err, 400)
    return _response(ohash, 201)


def get_evento(IDEvento, aclass):
    db_session = current_app.config['db_session']
    try:
        evento = db_session.query(aclass).filter(
            aclass.IDEvento == IDEvento,
            aclass.recinto == get_recinto()
        ).one_or_none()
        # print(evento.dump() if evento is not None else 'None')
        # print(hash(evento) if evento is not None else 'None')
        if evento is None:
            return _response('Evento não encontrado', 404)
        evento.hash = hash(evento)
        return evento.dump(), 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def add_evento(aclass, evento):
    usecase = create_usecases()
    try:
        novo_evento = usecase.insert_evento(aclass, evento)
        logger.info('Recinto: %s Classe: %s IDEvento: %d ID: %d Token: %d' %
                    (novo_evento.recinto, novo_evento.__class__.__name__,
                     novo_evento.IDEvento, novo_evento.ID, novo_evento.hash))
    except IntegrityError as err:
        usecase.db_session.rollback()
        logging.error(err, exc_info=True)
        return _response('Evento repetido ou campo invalido: %s' % err,
                         409)
    except Exception as err:
        usecase.db_session.rollback()
        logging.error(err, exc_info=True)
        return _response('Erro inesperado: %s ' % err, 400)
    return _response(novo_evento.hash, 201)


def posicaoconteiner(evento):
    return add_evento(orm.PosicaoConteiner, evento)


def get_posicaoconteiner(IDEvento):
    return get_evento(IDEvento, orm.PosicaoConteiner)


def acessopessoa(evento):
    return add_evento(orm.AcessoPessoa, evento)


def get_acessopessoa(IDEvento):
    return get_evento(IDEvento, orm.AcessoPessoa)


def posicaolote(evento):
    return add_evento(orm.PosicaoLote, evento)


def get_posicaolote(IDEvento):
    return get_evento(IDEvento, orm.PosicaoLote)


def avarialote(evento):
    return add_evento(orm.AvariaLote, evento)


def get_avarialote(IDEvento):
    return get_evento(IDEvento, orm.AvariaLote)


def pesagemmaritimo(evento):
    return add_evento(orm.PesagemMaritimo, evento)


def get_pesagemmaritimo(IDEvento):
    return get_evento(IDEvento, orm.PesagemMaritimo)


def inspecaonaoinvasiva(evento):
    usecase = create_usecases()
    try:
        inspecaonaoinvasiva = usecase.insert_inspecaonaoinvasiva(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(inspecaonaoinvasiva.hash, 201)


def get_inspecaonaoinvasiva(IDEvento):
    usecase = create_usecases()
    try:
        inspecaonaoinvasiva = usecase.load_inspecaonaoinvasiva(IDEvento)
        print(inspecaonaoinvasiva)
        return inspecaonaoinvasiva, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def agendamentoacessoveiculo(evento):
    usecase = create_usecases()
    try:
        agendamentoacessoveiculo = usecase.insert_agendamentoacessoveiculo(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(agendamentoacessoveiculo.hash, 201)


def get_agendamentoacessoveiculo(IDEvento):
    usecase = create_usecases()
    try:
        agendamentoacessoveiculo = usecase.load_agendamentoacessoveiculo(IDEvento)
        print(agendamentoacessoveiculo)
        return agendamentoacessoveiculo, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def operacaonavio(evento):
    return add_evento(orm.OperacaoNavio, evento)


def get_operacaonavio(IDEvento):
    return get_evento(IDEvento, orm.OperacaoNavio)


def ocorrencia(evento):
    return add_evento(orm.Ocorrencia, evento)


def get_ocorrencia(IDEvento):
    return get_evento(IDEvento, orm.Ocorrencia)


def get_acessoveiculo(IDEvento):
    try:
        acessoveiculo = orm.AcessoVeiculo.query.filter(
            orm.AcessoVeiculo.IDEvento == IDEvento
        ).outerjoin(
            orm.ListaNfeGate
        ).outerjoin(
            orm.ConteineresGate
        ).outerjoin(
            orm.ReboquesGate).one_or_none()
        if acessoveiculo is None:
            return _response('Evento não encontrado.', 404)
        acessoveiculo_schema = maschemas.AcessoVeiculo()
        data = acessoveiculo_schema.dump(acessoveiculo)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(acessoveiculo)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def acessoveiculo(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating acessoveiculo %s..', evento.get('IDEvento'))
    try:
        acessoveiculo = orm.AcessoVeiculo(**evento)
        db_session.add(acessoveiculo)
        conteineres = evento.get('conteineres')
        if conteineres:
            for conteiner in conteineres:
                logging.info('Creating conteiner %s..', conteiner.get('numero'))
                conteinergate = orm.ConteineresGate(acessoveiculo=acessoveiculo,
                                                    **conteiner)
                # numero=conteiner.get('numero'),
                # avarias=conteiner.get('avarias'),
                # l acres=conteiner.get('lacres'),
                # vazio=conteiner.get('vazio'))
                db_session.add(conteinergate)
        reboques = evento.get('reboques')
        if reboques:
            for reboque in reboques:
                logging.info('Creating reboque %s..', reboque.get('placa'))
                reboquegate = orm.ReboquesGate(acessoveiculo=acessoveiculo, **reboque)

                #                               placa=reboque.get('placa'),
                #                               avarias=reboque.get('avarias'),
                #                              lacres=reboque.get('lacres'),
                #                             vazio=reboque.get('vazio'))
            db_session.add(reboquegate)
        listanfe = evento.get('listanfe')
        if listanfe:
            for chavenfe in listanfe:
                logging.info('Creating reboque %s..', chavenfe.get('chavenfe'))
                achavenfe = orm.ListaNfeGate(acessoveiculo=acessoveiculo, **chavenfe)
            db_session.add(achavenfe)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(acessoveiculo)


def dtsc(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating DTSC %s..', evento.get('IDEvento'))
    try:
        dtsc = orm.DTSC(**evento)
        db_session.add(dtsc)
        cargas = evento.get('cargas')
        if cargas:
            for carga in cargas:
                logging.info('Creating loteDTSC %s..',
                             carga.get('placa'))
                acarga = orm.CargaDTSC(
                    DTSC=dtsc,
                    **carga
                )
                db_session.add(acarga)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(dtsc)


def get_dtsc(IDEvento):
    try:
        dtsc = orm.DTSC.query.filter(
            orm.DTSC.IDEvento == IDEvento
        ).outerjoin(
            orm.CargaDTSC
        ).one_or_none()
        if dtsc is None:
            return _response('Evento não encontrado.', 404)
        dtsc_schema = maschemas.DTSC()
        data = dtsc_schema.dump(dtsc)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(dtsc)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def pesagemveiculovazio(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating pesagemveiculovazio %s..', evento.get('IDEvento'))
    try:
        pesagemveiculovazio = orm.PesagemVeiculoVazio(**evento)
        db_session.add(pesagemveiculovazio)
        reboques = evento.get('reboques')
        if reboques:
            for reboque in reboques:
                logging.info('Creating lotepesagemveiculovazio %s..',
                             reboque.get('placa'))
                olote = orm.ReboquesPesagem(
                    pesagem=pesagemveiculovazio,
                    placa=reboque.get('placa')
                )
                db_session.add(olote)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(pesagemveiculovazio)


def get_pesagemveiculovazio(IDEvento):
    try:
        pesagemveiculovazio = orm.PesagemVeiculoVazio.query.filter(
            orm.PesagemVeiculoVazio.IDEvento == IDEvento
        ).outerjoin(
            orm.ReboquesPesagem
        ).one_or_none()
        if pesagemveiculovazio is None:
            return _response('Evento não encontrado.', 404)
        pesagemveiculovazio_schema = maschemas.PesagemVeiculoVazio()
        data = pesagemveiculovazio_schema.dump(pesagemveiculovazio)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(pesagemveiculovazio)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return str(err), 400


def posicaoveiculo(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating posicaoveiculo %s..', evento.get('IDEvento'))
    try:
        posicaoveiculo = orm.PosicaoVeiculo(**evento)
        db_session.add(posicaoveiculo)
        conteineres = evento.get('conteineres')
        if conteineres:
            for conteiner in conteineres:
                logging.info('Creating conteinerpesagemterrestre %s..',
                             conteiner.get('numero'))
                oconteiner = orm.ConteinerPosicao(posicaoveiculo=posicaoveiculo,
                                                  numero=conteiner.get('numero'),
                                                  vazio=conteiner.get('vazio'))
                db_session.add(oconteiner)
        reboques = evento.get('reboques')
        if reboques:
            for reboque in reboques:
                logging.info('Creating reboque %s..', reboque.get('placa'))
                oreboque = orm.ReboquePosicao(posicaoveiculo=posicaoveiculo,
                                              placa=reboque.get('placa'),
                                              vazio=reboque.get('vazio'))
            db_session.add(oreboque)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(posicaoveiculo)


def get_posicaoveiculo(IDEvento):
    try:
        posicaoveiculo = orm.PosicaoVeiculo.query.filter(
            orm.PosicaoVeiculo.IDEvento == IDEvento
        ).outerjoin(
            orm.ConteinerPosicao
        ).outerjoin(
            orm.ReboquePosicao
        ).one_or_none()
        if posicaoveiculo is None:
            return _response('Evento não encontrado.', 404)
        posicaoveiculo_schema = maschemas.PosicaoVeiculo()
        data = posicaoveiculo_schema.dump(posicaoveiculo)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(posicaoveiculo)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def unitizacao(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating unitizacao %s..', evento.get('IDEvento'))
    try:
        unitizacao = orm.Unitizacao(**evento)
        db_session.add(unitizacao)
        lotes = evento.get('lotes')
        if lotes:
            for lote in lotes:
                logging.info('Creating loteunitizacao %s..',
                             lote.get('numerolote'))
                olote = orm.LoteUnitizacao(unitizacao=unitizacao, **lote)
                db_session.add(olote)
        imagensunitizacao = evento.get('imagens')
        if imagensunitizacao:
            for imagemunitizacao in imagensunitizacao:
                logging.info('Creating imagemunitizacao %s..',
                             imagemunitizacao.get('caminhoarquivo'))
                aimagemunitizacao = orm.ImagemUnitizacao(
                    unitizacao=unitizacao,
                    caminhoarquivo=imagemunitizacao.get('caminhoarquivo'),
                    content=imagemunitizacao.get('content'),
                    contentType=imagemunitizacao.get('contentType'),
                    datacriacao=parse(imagemunitizacao.get('datacriacao')),
                    datamodificacao=parse(imagemunitizacao.get('datamodificacao'))
                )
            db_session.add(aimagemunitizacao)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(unitizacao)


def get_unitizacao(IDEvento):
    try:
        unitizacao = orm.Unitizacao.query.filter(
            orm.Unitizacao.IDEvento == IDEvento
        ).outerjoin(
            orm.LoteUnitizacao
        ).outerjoin(
            orm.ImagemUnitizacao
        ).one_or_none()
        if unitizacao is None:
            return {'message': 'Evento não encontrado.'}, 404
        unitizacao_schema = maschemas.Unitizacao()
        data = unitizacao_schema.dump(unitizacao)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(unitizacao)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def desunitizacao(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating desunitizacao %s..', evento.get('IDEvento'))
    try:
        desunitizacao = orm.Desunitizacao(**evento)
        db_session.add(desunitizacao)
        lotes = evento.get('lotes')
        if lotes:
            for lote in lotes:
                logging.info('Creating lotedesunitizacao %s..',
                             lote.get('numerolote'))
                olote = orm.Lote(desunitizacao=desunitizacao, **lote)
                db_session.add(olote)
        imagensdesunitizacao = evento.get('imagens')
        if imagensdesunitizacao:
            for imagemdesunitizacao in imagensdesunitizacao:
                logging.info('Creating imagemdesunitizacao %s..',
                             imagemdesunitizacao.get('caminhoarquivo'))
                aimagemdesunitizacao = orm.ImagemDesunitizacao(
                    desunitizacao=desunitizacao,
                    caminhoarquivo=imagemdesunitizacao.get('caminhoarquivo'),
                    content=imagemdesunitizacao.get('content'),
                    contentType=imagemdesunitizacao.get('contentType'),
                    datacriacao=parse(imagemdesunitizacao.get('datacriacao')),
                    datamodificacao=parse(imagemdesunitizacao.get('datamodificacao'))
                )
                db_session.add(aimagemdesunitizacao)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(desunitizacao)


def get_desunitizacao(IDEvento):
    try:
        desunitizacao = orm.Desunitizacao.query.filter(
            orm.Desunitizacao.IDEvento == IDEvento
        ).outerjoin(
            orm.Lote
        ).outerjoin(
            orm.ImagemDesunitizacao
        ).one_or_none()
        if desunitizacao is None:
            return _response('Evento não encontrado.', 404)
        desunitizacao_schema = orm.DesunitizacaoSchema()
        data = desunitizacao_schema.dump(desunitizacao)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(desunitizacao)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def pesagemterrestre(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating pesagemterrestre %s..', evento.get('IDEvento'))
    try:
        pesagemterrestre = orm.PesagemTerrestre(**evento)
        db_session.add(pesagemterrestre)
        conteineres = evento.get('conteineres')
        if conteineres:
            for conteiner in conteineres:
                logging.info('Creating conteinerpesagemterrestre %s..',
                             conteiner.get('numero'))
                oconteiner = orm.ConteinerPesagemTerrestre(
                    pesagem=pesagemterrestre,
                    numero=conteiner.get('numero'),
                    tara=conteiner.get('tara'))
                db_session.add(oconteiner)
        reboques = evento.get('reboques')
        if reboques:
            for reboque in reboques:
                logging.info('Creating reboque %s..', reboque.get('placa'))
                oreboque = orm.ReboquePesagemTerrestre(
                    pesagem=pesagemterrestre,
                    placa=reboque.get('placa'),
                    tara=reboque.get('tara'))
            db_session.add(oreboque)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(pesagemterrestre)


def get_pesagemterrestre(IDEvento):
    try:
        pesagemterrestre = orm.PesagemTerrestre.query.filter(
            orm.PesagemTerrestre.IDEvento == IDEvento
        ).outerjoin(
            orm.ReboquePesagemTerrestre
        ).outerjoin(
            orm.ConteinerPesagemTerrestre
        ).one_or_none()
        if pesagemterrestre is None:
            return _response('Evento não encontrado.', 404)
        pesagemterrestre_schema = orm.PesagemTerrestreSchema()
        data = pesagemterrestre_schema.dump(pesagemterrestre)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(pesagemterrestre)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def get_artefatorecinto(IDEvento):
    try:
        artefatorecinto = orm.ArtefatoRecinto.query.filter(
            orm.ArtefatoRecinto.IDEvento == IDEvento
        ).outerjoin(
            orm.CoordenadaArtefato).one_or_none()
        if artefatorecinto is None:
            return {'message': 'Evento não encontrado.'}, 404
        artefatorecinto_schema = maschemas.ArtefatoRecinto()
        data = artefatorecinto_schema.dump(artefatorecinto)
        if getattr(data, 'data'):
            data = data.data
        data = {**{'hash': hash(artefatorecinto)}, **data}
        return data, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 400)


def artefatorecinto(evento):
    db_session = current_app.config['db_session']
    logging.info('Creating artefatorecinto %s..', evento.get('IDEvento'))
    try:
        artefatorecinto = orm.ArtefatoRecinto(**evento)
        db_session.add(artefatorecinto)
        coordenadas = evento.get('coordenadasartefato')
        if coordenadas:
            for coordenada in coordenadas:
                logging.info('Creating coordenada %s..', coordenada.get('ordem'))
                coordenadaarteafato = orm.CoordenadaArtefato(
                    artefato=artefatorecinto,
                    ordem=coordenada.get('ordem'),
                    lat=coordenada.get('lat'),
                    long=coordenada.get('long')
                )
                db_session.add(coordenadaarteafato)
    except Exception as err:
        logging.error(err, exc_info=True)
        db_session.rollback()
        return _response(err, 400)
    return _commit(artefatorecinto)


def list_posicaoconteiner(filtro):
    db_session = current_app.config['db_session']
    try:
        try:
            recinto = filtro.get('recinto')
            datainicial = filtro.get('datainicial')
            datafinal = filtro.get('datafinal')
            altura = filtro.get('altura')
            filters = [orm.PosicaoConteiner.dataevento.between(datainicial, datafinal),
                       orm.PosicaoConteiner.recinto.like(recinto)]
            if altura is not None:
                filters.append(orm.PosicaoConteiner.altura.__eq__(int(altura)))
        except Exception as err:
            logging.error(err, exc_info=True)
            return _response('Erro nos filtros passados: %s' % str(err), 400)
        eventos = db_session.query(
            orm.PosicaoConteiner
        ).filter(and_(*filters)).all()
        if eventos is None or len(eventos) == 0:
            return 'Sem eventos posicaoconteiner entre datas %s a %s.' % \
                   (datainicial, datafinal), 404
        return dump_eventos(eventos)
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 405)


def get_eventosnovos(filtro):
    usecase = create_usecases()
    print(filtro)
    IDEvento = filtro.get('IDEvento')
    dataevento = filtro.get('dataevento')
    try:
        dataevento = parse(dataevento)
    except Exception as err:
        logging.error(err, exc_info=True)
        if IDEvento is None:
            return _response('IDEvento e dataevento invalidos, '
                             'ao menos um dos dois e necessario', 400)
        dataevento = None
    try:
        tipoevento = filtro.get('tipoevento')
        aclass = getattr(orm, tipoevento)
    except AttributeError as err:
        logging.error(err, exc_info=True)
        return _response('Erro no campo tipoevento do filtro %s ' % str(err), 400)
    fields = filtro.get('fields')
    eventos = usecase.load_eventosnovos(aclass, IDEvento, dataevento, fields)
    try:
        if eventos is None or len(eventos) == 0:
            if dataevento is None:
                return _response('Sem eventos com ID maior que %d.' % IDEvento, 404)
            return _response('Sem eventos com dataevento maior que %s.' % dataevento,
                             404)
        return dump_eventos(eventos)
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 405)
        return _response(err, 405)


def filter_eventos(filtro):
    db_session = current_app.config['db_session']
    print(filtro)
    recinto = filtro.get('recinto')
    datainicial = filtro.get('datainicial')
    datafinal = filtro.get('datafinal')
    try:
        datainicial = parse(datainicial)
        datafinal = parse(datafinal)
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response('Datas inválidas, verifique.', 400)
    try:
        tipoevento = filtro.get('tipoevento')
        aclass = getattr(orm, tipoevento)
    except AttributeError as err:
        logging.error(err, exc_info=True)
        return _response('Erro no campo tipoevento do filtro %s ' % str(err), 400)
    try:
        filters = [aclass.dataevento.between(datainicial, datafinal)]
        if recinto:
            filters.append(aclass.recinto == recinto)
        eventos = db_session.query(aclass).filter(
            and_(*filters)
        ).all()
        if eventos is None:
            return _response('Sem eventos tipo %s para recinto %s '
                             'no intervalo de datas %s a %s.' %
                             (tipoevento, recinto, datainicial, datafinal), 404)
        return dump_eventos(eventos)
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response(err, 405)


def bloqueia_cadastro(IDEvento, aclass):
    db_session = current_app.config['db_session']
    try:
        cadastro = db_session.query(aclass).filter(
            aclass.IDEvento == IDEvento
        ).one_or_none()
        if cadastro is None:
            return _response('Evento nao encontrado', 404)
        cadastro.inativar()
        db_session.commit()
        db_session.refresh(cadastro)
        cadastro.hash = hash(cadastro)
        return cadastro.dump(), 201
    except Exception as err:
        db_session.rollback()
        logging.error(err, exc_info=True)
        return _response(err, 400)


def cadastrorepresentacao(evento):
    return add_evento(orm.CadastroRepresentacao, evento)


def get_cadastrorepresentacao(IDEvento):
    return get_evento(IDEvento, orm.CadastroRepresentacao)


def encerra_cadastrorepresentacao(IDEvento):
    return bloqueia_cadastro(IDEvento, orm.CadastroRepresentacao)


def credenciamentoveiculo(evento):
    usecase = create_usecases()
    try:
        credenciamentoveiculo = usecase.insert_credenciamentoveiculo(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(credenciamentoveiculo.hash, 201)


def get_credenciamentoveiculo(IDEvento):
    usecase = create_usecases()
    try:
        credenciamentoveiculo = usecase.load_credenciamentoveiculo(IDEvento)
        return credenciamentoveiculo, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def inativar_credenciamentoveiculo(IDEvento):
    return bloqueia_cadastro(IDEvento, orm.CredenciamentoVeiculo)


def credenciamentopessoa(evento):
    usecase = create_usecases()
    try:
        credenciamentopessoa = usecase.insert_credenciamentopessoa(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(credenciamentopessoa.hash, 201)


def get_credenciamentopessoa(IDEvento):
    usecase = create_usecases()
    try:
        credenciamentopessoa = usecase.load_credenciamentopessoa(IDEvento)
        return credenciamentopessoa, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def inativar_credenciamentopessoa(IDEvento):
    return bloqueia_cadastro(IDEvento, orm.CredenciamentoPessoa)


def informacaobloqueio(evento):
    return add_evento(orm.InformacaoBloqueio, evento)


def get_informacaobloqueio(IDEvento):
    return get_evento(IDEvento, orm.InformacaoBloqueio)


def desbloqueia_informacaobloqueio(IDEvento):
    return bloqueia_cadastro(IDEvento, orm.InformacaoBloqueio)


def agendamentoconferencia(evento):
    return add_evento(orm.AgendamentoConferencia, evento)


def get_agendamentoconferencia(IDEvento):
    return get_evento(IDEvento, orm.AgendamentoConferencia)


def cancela_agendamentoconferencia(IDEvento):
    return bloqueia_cadastro(IDEvento, orm.AgendamentoConferencia)
