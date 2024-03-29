import json
import os
import random
from datetime import datetime
from unittest import TestCase

from dateutil.parser import parse

from apiserver.models import orm

JSON_TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), 'json_exemplos')


def random_str(num, fila):
    result = ''
    for i in range(num):
        result += random.choice(fila)
    return result


db_session = None
engine = None
cadastros = None


def create_session():
    global db_session
    global engine
    global testes
    if db_session is None:
        print('Creating memory database')
        db_session, engine = orm.init_db('sqlite:///:memory:')
    return db_session, engine


class BaseTestCase(TestCase):

    def setUp(self):
        self.db_session, self.engine = create_session()
        orm.Base.metadata.create_all(bind=self.engine)
        self.recinto = '00001'
        self.assinado = ''
        self.headers = {}
        self.data_fields = ['dataevento', 'dataregistro', 'dataoperacao',
                            'dataliberacao', 'dataagendamento', 'dtHrTransmissao',
                            'dtHrOcorrencia', 'dtHrRegistro',
                            'datacriacao', 'datamodificacao']
        self.tipos_evento = set(
            [nomearquivo[:-5] for nomearquivo in
             os.listdir(JSON_TEST_CASES_PATH)]
        )
        self.load_test_cases()

    def tearDown(self) -> None:
        orm.Base.metadata.drop_all(bind=self.engine)

    def open_json_test_case(self, classe_evento):
        if isinstance(classe_evento, str):
            nomeclasse = classe_evento
        else:
            nomeclasse = classe_evento.__name__
        with open(os.path.join(JSON_TEST_CASES_PATH,
                               nomeclasse) + '.json') as json_in:
            return json.load(json_in)

    def load_test_cases(self):
        self.testes = {}
        for nomeclasse in self.tipos_evento:
            self.testes[nomeclasse] = self.open_json_test_case(nomeclasse)



    def extractDictAFromB(self, A, B):
        return dict([(k, B[k]) for k in A.keys() if k in B.keys()])

    def get_keys(self):
        """Acessa endpoint para gerar chave, guarda codigo recinto assinado."""
        rv = self.client.post('/apirecintos/privatekey', json={'recinto': self.recinto})
        assert rv.json
        pem = rv.json.get('pem')
        self.assinado = rv.json.get('assinado')

    def get_token(self):
        recinto_senha = {'recinto': self.recinto,
                         'senha': 'senha'}
        rv = self.client.post('/apirecintos/auth', json=recinto_senha)
        # assert rv.status_code == 200
        token = rv.data.decode('utf-8').strip()
        self.headers = {'Authorization': 'Bearer %s' % token}

    def purge_datas(self, adict):
        for data in self.data_fields:
            if adict.get(data) is not None:
                adict.pop(data)

    def compare_dict(self, adict, bdict):
        for k, v in adict.items():
            vb = bdict.get(k)
            if vb is not None:
                if isinstance(vb, list):
                    for itema, itemb in zip(v, vb):
                        if isinstance(itema, str):
                            self.assertEqual(itema, itemb)
                        else:
                            self.compare_dict(itema, itemb)
                elif isinstance(vb, dict):
                    self.compare_dict(v, vb)
                else:
                    if isinstance(vb, datetime):
                        if not isinstance(v, datetime):
                            vadate = parse(v)
                            # self.assertEqual(vadate, vb)
                    else:
                        if k not in self.data_fields:
                            self.assertEqual(v, vb)

    def compara_eventos(self, teste, response_json):
        self.purge_datas(teste)
        self.purge_datas(response_json)
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
            json_pesagens = {'PesagemVeiculoCarga': self.pesagens}
            with open('test.json', 'w', encoding='utf-8', newline='') as json_out:
                json.dump(json_pesagens, json_out)
