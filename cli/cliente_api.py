"""Script de linha de comando para validar JSON de Eventos.

Script de linha de comando para validar ou enviar JSON de Eventos

Args:

    --dir: diretório a processar (caso queira gerar)
    --arquivo:
    --send: endereço do Servidor APIRecintos

"""
import json
import logging
import os

import click
import requests

from apiserver.models import orm
from apiserver.use_cases.usecases import UseCases

BASE_DIR = os.getcwd()
API_URL = 'http://localhost:8000/'


def valida_evento(usecases, aclass, evento, logger, ind):
    try:
        result = usecases.insert_evento(aclass, evento)
        print('Evento numero %d Retorno: %s IDEvento: %s hash: %s' %
              (ind, result, result.IDEvento, result.hash))
    except Exception as err:
        print('Evento tipo: %s Linha do Evento: %s Erro: %s Sequência: %d' %
              (aclass.__name__, str(evento)[:100], str(err), ind))
        logger.error('Sequência %d Erro %s' % (ind, str(err)), exc_info=True)


@click.command()
@click.option('--arquivo', required=True,
              help='Arquivo a validar ou enviar')
@click.option('--envio',
              help='URL do Servidor para envio')
@click.option('--dir',
              help='diretório a processar')
def carrega(dir, arquivo, envio):
    """Script de linha de comando para validar ou enviar JSON de Eventos.

    --arquivo Se somente arquivo for informado, valida o arquivo, gravando erros
        detalhados caso ocorram no arquivo com final .erros.log,
        no mesmo diretório e nome do arquivo passado

    --envio Se parâmetro envio forem informados, tentará enviar arquivo para API.

    --dir Por último, o parâmetro dir serve para indicar um diretório com imagens
        que será utilizado para gerar um arquivo JSON do Evento (não implementado)
    """
    with open(os.path.join(BASE_DIR, arquivo), 'r') as json_in:
        testes = json.load(json_in)
    filehandler = logging.FileHandler(os.path.join(BASE_DIR, arquivo + '.erros.log'))
    print(filehandler.baseFilename)
    logger = logging.getLogger()
    logger.addHandler(filehandler)
    if envio:  # Conecta ao Servidor e imprime resultado na tela
        rv = requests.post(envio + '/set_eventos',
                           files={'file': (testes.read(), arquivo)})
    else:  # Valida arquivo json com BD na memória
        print('Criando Banco na memória para testes')
        session, engine = orm.init_db('sqlite:///:memory:')
        orm.Base.metadata.create_all(bind=engine)
        usecases = UseCases(session, 'TESTE', 'localhost', '.')
        ind = 1
        for classe, eventos in testes.items():
            print('Evento numero %d Tipo %s' % (ind, classe))
            aclass = getattr(orm, classe)
            if isinstance(eventos, list):
                for evento in eventos:
                    valida_evento(usecases, aclass, evento, logger, ind)
                    ind += 1
            else:
                valida_evento(usecases, aclass, eventos, logger, ind)
                ind += 1


def print_help_msg(command):
    with click.Context(command) as ctx:
        click.echo(command.get_help(ctx))


if __name__ == '__main__':
    carrega()
