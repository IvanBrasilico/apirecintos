import logging

from dateutil.parser import parse
from flask import current_app, request, jsonify, g
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from apiserver.logconf import logger
from apiserver.models import orm
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
    basepath = current_app.config['UPLOAD_FOLDER']
    return UseCases(db_session, basepath)


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


def pesagemveiculocarga(evento):
    usecase = create_usecases()
    try:
        evento = usecase.insert_pesagemveiculocarga(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(evento.hash, 201)


def get_pesagemveiculocarga(codRecinto, IDEvento):
    usecase = create_usecases()
    try:
        evento = usecase.load_pesagemveiculocarga(codRecinto, IDEvento)
        return evento, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def inspecaonaoinvasiva(evento):
    usecase = create_usecases()
    try:
        inspecaonaoinvasiva = usecase.insert_inspecaonaoinvasiva(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(inspecaonaoinvasiva.hash, 201)


def get_inspecaonaoinvasiva(codRecinto, IDEvento):
    usecase = create_usecases()
    try:
        inspecaonaoinvasiva = usecase.load_inspecaonaoinvasiva(codRecinto, IDEvento)
        return inspecaonaoinvasiva, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)


def acessoveiculo(evento):
    usecase = create_usecases()
    try:
        evento = usecase.insert_acessoveiculo(evento)
    except Exception as err:
        logging.error(err, exc_info=True)
        usecase.db_session.rollback()
        return _response_for_exception(err)
    return _response(evento.hash, 201)


def get_acessoveiculo(codRecinto, IDEvento):
    usecase = create_usecases()
    try:
        evento = usecase.load_acessoveiculo(codRecinto, IDEvento)
        return evento, 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return _response_for_exception(err)



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


def get_eventosnovos():
    pass