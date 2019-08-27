import logging
import os
import pickle
import time
from base64 import b85decode

import six
from flask import request, jsonify, g, current_app
from jose import JWTError, jwt
from werkzeug.exceptions import Unauthorized

import assinador
from apiserver.api import _response
from apiserver.models.orm import ChavePublicaRecinto


def make_secret():
    try:
        with open('SECRET', 'rb') as secret:
            secret = pickle.load(secret)
    except (FileNotFoundError, pickle.PickleError):
        secret = os.urandom(24)
        with open('SECRET', 'wb') as out:
            pickle.dump(secret, out, pickle.HIGHEST_PROTOCOL)
    return secret


JWT_ISSUER = 'api-recintos'
JWT_SECRET = str(make_secret())
JWT_LIFETIME_SECONDS = 600
JWT_ALGORITHM = 'HS256'


def generate_token(recinto):
    # TODO: Validar usuario e senha
    timestamp = _current_timestamp()
    payload = {
        'iss': JWT_ISSUER,
        'iat': int(timestamp),
        'exp': int(timestamp + JWT_LIFETIME_SECONDS),
        'recinto': str(recinto['recinto']),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        logging.error(e, exc_info=True)
        six.raise_from(Unauthorized, e)
    except Exception as err:
        logging.error(err, exc_info=True)
        raise Exception('Erro ao analisar token: %s Mensagem de erro: %s' %
                        (token, (str(err))))


def get_secret(user, token_info) -> str:
    return """
    You are user_id {user} and the secret is 'wbevuec'.
    Decoded token claims: {token_info}.
    """.format(user=user, token_info=token_info)


def _current_timestamp() -> int:
    return int(time.time())


def recorta_token_header(headers):
    token = headers.get('Authorization')
    if token:
        token = token.split()
        if len(token) == 2:
            token = token[1]
    return token


def valida_assinatura(decoded_token, assinado, db_session):
    recinto = decoded_token.get('recinto')
    if g:
        g.recinto = recinto
    assinado = b85decode(assinado.encode('utf-8'))
    print('recinto: %s' % recinto)
    print('assinado: %s' % assinado)
    public_key_pem = ChavePublicaRecinto.get_public_key(db_session, recinto)
    public_key = assinador.load_public_key(public_key_pem)
    assinador.verify(assinado, recinto.encode('utf8'), public_key)


def valida_token_e_assinatura(request, db_session=None) -> [bool, str]:
    """Analisa request e retorna True ou False

    1. Retira token do header
    2. Decodifica token
    3. Pega campo recinto e recupera chave publica do recinto do banco
    4. Valida assinatura (campo assinado tem que estar no request e corresponder
    ao codigo do recinto assinado com sua chave privada)

    :param request: Objeto request
    :param db_session: Conexão ao BD
    :return: Sucesso(True, False), mensagem

    """
    token = recorta_token_header(request.headers)
    if token is None:
        return False, 'Token não fornecido'
    try:
        if db_session is None:
            db_session = current_app.config['db_session']
        # print(token)
        decoded_token = decode_token(token)
        verify_sign = os.environ.get('VERIFY_SIGN', 'NO').lower() == 'yes'
        if current_app and verify_sign:
            assinado = request.json.get('assinado')
            valida_assinatura(decoded_token, assinado, db_session)
        else:
            logging.warning(
                'Sem verificação de assinatura digital! '
                'Configure a variável de ambiente '
                '($export VERIFY_SIGN=YES) para ativar.'
            )

    except Exception as err:
        logging.error(err, exc_info=True)
        return False, str(err)
    return True, None


def configure_signature(app):
    # Caso autenticação esteja desligada, sai sem configurar nada
    app.app.config['authenticate'] = \
        os.environ.get('AUTHENTICATE', 'NO').lower() == 'yes'
    if app.app.config.get('authenticate', False) is False:
        logging.warning(
            'Sem autenticação!'
            ' Configure a variável de ambiente ($export AUTHENTICATE=YES) para ativar.'
        )
        return

    @app.app.before_request
    def before_request():
        if request.path in ['/', '/openapi.json', '/auth', '/privatekey']:
            return
        if 'site' in request.path or '/ui' in request.path:
            return
        sucesso, err_msg = valida_token_e_assinatura(request)
        if sucesso is False:
            return jsonify(
                _response('Token inválido ou Assinatura inválida: %s' % err_msg, 401)
            ), 401
