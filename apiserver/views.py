import logging
import os
from base64 import b85encode

from dateutil.parser import parse
from flask import current_app, request, render_template, \
    jsonify, Response, send_from_directory

from apiserver.api import dump_eventos, _response, _commit, create_usecases
from apiserver.logconf import logger
from apiserver.models import orm
from apiserver.use_cases.usecases import UseCases


def home():
    return render_template('home.html')


def getfile():
    db_session = current_app.config['db_session']
    try:
        IDEvento = request.form.get('IDEvento')
        tipoevento = request.form.get('tipoevento')
        nomearquivo = request.form.get('nomearquivo')
        if not tipoevento:
            raise Exception('Parâmetro tipoevento é obrigatório.')
        try:
            aclass = getattr(orm, tipoevento)
        except AttributeError:
            raise AttributeError('tipoevento "%s" não existente' % tipoevento)
        except TypeError:
            raise AttributeError('tipoevento "%s": erro ao processar parâmetro' %
                                 tipoevento)
        evento = db_session.query(aclass).filter(
            aclass.IDEvento == IDEvento
        ).one_or_none()
        if evento is None:
            return jsonify(_response('Evento não encontrado.', 404)), 404
        oanexo = UseCases.get_anexo(evento, nomearquivo)
        basepath = current_app.config.get('UPLOAD_FOLDER')
        oanexo.load_file(basepath)
        print(oanexo.content)
        return Response(response=oanexo.content,
                        mimetype=oanexo.contentType
                        ), 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return jsonify(_response(err, 400)), 400


def uploadfile():
    """Função simplificada para upload de arquivo para um Evento."""
    db_session = current_app.config['db_session']
    usecase = create_usecases()
    try:
        file = request.files.get('file')
        IDEvento = request.form.get('IDEvento')
        tipoevento = request.form.get('tipoevento')
        nomearquivo = request.form.get('nomearquivo')
        tipoanexo = request.form.get('tipoanexo')
        validfile, mensagem = usecase.valid_file(file)
        if not validfile:
            return jsonify(_response(mensagem, 400)), 400
        aclass = getattr(orm, tipoevento)
        evento = db_session.query(aclass).filter(
            aclass.IDEvento == IDEvento
        ).one_or_none()
        if evento is None:
            return jsonify(_response('Evento não encontrado.', 404)), 404
        db_session.add(evento)
        oanexo = UseCases.get_anexo(evento, nomearquivo)
        if oanexo is None:
            classeanexo = getattr(orm, tipoanexo)
            oanexo = classeanexo.create(
                evento
            )
        basepath = current_app.config.get('UPLOAD_FOLDER')
        oanexo.save_file(basepath,
                         file.read(),
                         file.filename
                         )
        db_session.add(oanexo)
        return jsonify(_commit(evento)), 201
    except Exception as err:
        logger.error(str(err), exc_info=True)
        return jsonify(_response(err, 400)), 400


def seteventosnovos():
    usecase = create_usecases()
    try:
        file = request.files.get('file')
        eventos = usecase.load_arquivo_eventos(file)
        for tipoevento, eventos in eventos.items():
            aclass = getattr(orm, tipoevento)
            for evento in eventos:
                try:
                    usecase.insert_evento(aclass, evento, commit=False)
                # Ignora exceções porque vai comparar no Banco de Dados
                except Exception as err:
                    logging.error(str(err))
            try:
                usecase.db_session.commit()
            except Exception as err:
                logging.error(str(err))
            result = []
            for evento in eventos:
                try:
                    IDEvento = evento.get('IDEvento')
                    evento_recuperado = usecase.load_evento(aclass, IDEvento)
                    ohash = hash(evento_recuperado)
                    result.append({'IDEvento': IDEvento, 'hash': ohash})
                    logger.info('Recinto: %s IDEvento: %d ID: %d hash: %d' %
                                (evento_recuperado.recinto, IDEvento,
                                 evento_recuperado.ID, ohash))
                except Exception as err:
                    result.append({'IDEvento': IDEvento, 'hash': str(err)})
                    logger.error('Evento ID:  %d erro: %s' %
                                 (IDEvento,
                                  str(err)))
    except Exception as err:
        logging.error(err, exc_info=True)
        return str(err), 405
    return jsonify(result), 201


def geteventosnovos():
    usecase = create_usecases()
    try:
        try:
            IDEvento = int(request.form.get('IDEvento'))
        except TypeError:
            IDEvento = None
        try:
            dataevento = parse(request.form.get('dataevento'))
        except Exception:
            if IDEvento is None:
                return jsonify(_response('IDEvento e dataevento invalidos, '
                                         'ao menos um dos dois e necessario', 400)), 400
            dataevento = None
        tipoevento = request.form.get('tipoevento')
        aclass = getattr(orm, tipoevento)
        fields = request.form.get('fields')
        eventos = usecase.load_eventosnovos(aclass, IDEvento, dataevento, fields)
        if eventos is None:
            if dataevento is None:
                return jsonify(_response('Sem eventos com ID maior que %d.' %
                                         IDEvento, 404)), 404
            return jsonify(_response('Sem eventos com dataevento maior que %s.' %
                                     dataevento, 404)), 404
        return dump_eventos(eventos), 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return jsonify(_response(err, 400)), 400


def site(path):
    return send_from_directory('site', path)


def get_private_key():
    recinto = request.json.get('recinto')
    try:
        private_key_pem, assinado = UseCases.gera_chaves_recinto(
            current_app.config['db_session'],
            recinto
        )
        return jsonify({'pem': private_key_pem.decode('utf-8'),
                        'assinado': b85encode(assinado).decode('utf-8')}), 200
    except Exception as err:
        logging.error(err, exc_info=True)
        return jsonify(_response(err, 400)), 400


def recriatedb():  # pragma: no cover
    # db_session = current_app.config['db_session']
    engine = current_app.config['engine']
    try:
        orm.Base.metadata.drop_all(bind=engine)
        orm.Base.metadata.create_all(bind=engine)
    except Exception as err:
        return jsonify(_response(err, 405)), 405
    return jsonify(_response('Banco recriado!!!', 201)), 201


def create_views(app):
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'files')
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
    app.app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.add_url_rule('/', 'home', home)
    app.add_url_rule('/upload_file', 'uploadfile', uploadfile, methods=['POST'])
    app.add_url_rule('/get_file', 'getfile', getfile)
    app.add_url_rule('/eventosnovos/get', 'geteventosnovos', geteventosnovos)
    app.add_url_rule('/eventosnovos/upload', 'seteventosnovos',
                     seteventosnovos, methods=['POST'])
    app.add_url_rule('/privatekey', 'get_private_key',
                     get_private_key, methods=['POST'])
    app.add_url_rule('/site/<path:path>', 'site', site)
    app.add_url_rule('/recriatedb', 'recriatedb', recriatedb)
