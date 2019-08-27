import random
from datetime import datetime
import json
import os
from unittest import TestCase

from dateutil.parser import parse

from apiserver.models import orm


def random_str(num, fila):
    result = ''
    for i in range(num):
        result += random.choice(fila)
    return result


db_session = None
engine = None
testes = None
cadastros = None


def create_session():
    global db_session
    global engine
    global testes
    global cadastros
    if db_session is None:
        print('Creating memory database')
        db_session, engine = orm.init_db('sqlite:///:memory:')
        with open(os.path.join(os.path.dirname(__file__),
                               'tests.json'), 'r') as json_in:
            testes = json.load(json_in)
        with open(os.path.join(os.path.dirname(__file__),
                               'cadastros.json'), 'r') as json_in:
            cadastros = json.load(json_in)
    return db_session, engine, testes, cadastros


def extractDictAFromB(A, B):
    return dict([(k, B[k]) for k in A.keys() if k in B.keys()])


class BaseTestCase(TestCase):

    def setUp(self):
        self.db_session, self.engine, self.testes, self.cadastros = create_session()
        orm.Base.metadata.create_all(bind=self.engine)
        self.recinto = '00001'
        self.assinado = ''
        self.headers = {}

    def tearDown(self) -> None:
        orm.Base.metadata.drop_all(bind=self.engine)


    def get_keys(self):
        """Acessa endpoint para gerar chave, guarda codigo recinto assinado."""
        rv = self.client.post('/privatekey', json={'recinto': self.recinto})
        assert rv.json
        pem = rv.json.get('pem')
        self.assinado = rv.json.get('assinado')

    def get_token(self):
        recinto_senha = {'recinto': self.recinto,
                         'senha': 'senha'}
        rv = self.client.post('/auth', json=recinto_senha)
        # assert rv.status_code == 200
        token = rv.data.decode('utf-8').strip()
        self.headers = {'Authorization': 'Bearer %s' % token}

    def compare_dict(self, adict, bdict):
        for k, v in adict.items():
            vb = bdict.get(k)
            if vb is not None:
                if isinstance(vb, list):
                    for itema, itemb in zip(v, vb):
                        self.compare_dict(itema, itemb)
                elif isinstance(vb, dict):
                    self.compare_dict(v, vb)
                else:
                    if isinstance(vb, datetime):
                        if not isinstance(v, datetime):
                            vadate = parse(v)
                            # self.assertEqual(vadate, vb)
                    else:
                        self.assertEqual(v, vb)

    def compara_eventos(self, teste, response_json):
        for data in ['dataevento', 'dataregistro', 'dataoperacao', 'dataliberacao', 'dataagendamento']:
            if teste.get(data) is not None:
                teste.pop(data)
            if response_json.get(data) is not None:
                response_json.pop(data)
        # sub_response = extractDictAFromB(teste, response_json)
        self.compare_dict(teste, response_json)
        # self.maxDiff = None
        # self.assertDictContainsSubset(teste, sub_response)

    def cria_lote(self):
        letras = 'ABCDEFGHIJKLMNOPQRSTUVXZ'
        numeros = ''.join([str(i) for i in range(10)])
        textos = 'ABCDEFGHIJKLMNOPQRSTUVXZ          abcdefghijklmnopqrstuvwxyz'
        placas = [random_str(3, letras) + random_str(5, numeros) for i in range(100)]
        reboques = [random_str(3, letras) + random_str(5, numeros) for i in range(200)]
        conteineres = [random_str(4, letras) + random_str(7, numeros) for i in range(200)]
        operadores = [random_str(11, letras) for i in range(10)]
        motoristas = [random_str(11, letras) for i in range(50)]
        textos = [random_str(random.randint(10, 20), textos) for i in range(50)]

        self.pesagens = []
        for r in range(10):
            data = datetime.now().isoformat()
            operador = random.choice(operadores)
            conteiner = random.choice(conteineres)
            tara = random.randint(9000, 12000)
            pesobrutodeclarado = random.randint(3000, 15000)
            pesobalanca = tara + random.randint(-2000, 2000)
            placa = random.choice(placas)
            reboque = random.choice(reboques)
            texto = random.choice(textos)
            pesagem = \
                {'IDEvento': r + 500,
                 'capturaautomatica': True,
                 'numero': random.choice(conteineres),
                 'dataevento': data,
                 'dataregistro': data,
                 'retificador': False,
                 'documentotransporte': texto,
                 'operadorevento': operador,
                 'operadorregistro': operador,
                 'pesobalanca': pesobalanca,
                 'pesobrutodeclarado': pesobrutodeclarado,
                 'placa': placa,
                 'placasemireboque': reboque,
                 'taraconjunto': tara,
                 'tipodocumentotransporte': 'CE'}
            self.pesagens.append(pesagem)
            json_pesagens = {'PesagemMaritimo': self.pesagens}
            with open('test.json', 'w', encoding='utf-8', newline='') as json_out:
                json.dump(json_pesagens, json_out)
