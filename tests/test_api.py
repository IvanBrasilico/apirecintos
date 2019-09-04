import datetime
import sys
from base64 import b85encode
from copy import deepcopy
from io import BytesIO

from apiserver.main import create_app
from basetest import BaseTestCase

sys.path.insert(0, 'apiserver')


class APITestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        app = create_app(self.db_session, self.engine)
        self.client = app.app.test_client()
        self.get_token()

    def tearDown(self) -> None:
        super().tearDown()

    def test_health(self):
        response = self.client.get('/non_ecxiste', headers=self.headers)
        assert response.status_code == 404

    def test1_evento_invalido_400(self):
        for nomeclasse in self.tipos_evento:
            print(nomeclasse)
            rv = self.client.post(nomeclasse.lower(),
                                  json={'idEvento': 1},
                                  headers=self.headers)
            assert rv.status_code == 400
            assert rv.is_json is True
            rv = self.client.get(nomeclasse.lower() + '/1', headers=self.headers)
            assert rv.status_code == 404
            assert rv.is_json is True

    def test2_evento_nao_encontrado_404(self):
        for nomeclasse in self.tipos_evento:
            rv = self.client.get(nomeclasse.lower() + '/1', headers=self.headers)
            assert rv.status_code == 404
            assert rv.is_json is True

    def compara_eventos(self, teste, response_json):
        for data in ['dataevento', 'dataregistro', 'dataoperacao', 'dataliberacao',
                     'dataagendamento', 'datamodificacao', 'datacriacao', 'inicio', 'fim',
                     'datanascimento', 'fimvalidade', 'iniciovalidade']:
            if teste.get(data) is not None:
                teste.pop(data)
            if response_json.get(data) is not None:
                response_json.pop(data)
        sub_response = self.extractDictAFromB(teste, response_json)
        self.maxDiff = None
        eliminar = []
        for k, v in teste.items():
            if isinstance(v, list):
                self.compara_eventos(v[0], sub_response[k][0])
                eliminar.append(k)
        for k in eliminar:
            sub_response.pop(k)
            teste.pop(k)
        self.assertDictContainsSubset(teste, sub_response)

    def test3_api(self):
        for classe, teste in self.testes.items():
            print(classe)
            rv = self.client.post(classe.lower(),
                                  json=teste,
                                  headers=self.headers)
            assert rv.status_code == 201
            assert rv.is_json is True
            response_token = rv.json
            rv = self.client.get(classe.lower() + '/' + str(teste['IDEvento']),
                                 headers=self.headers)
            assert rv.status_code == 200
            assert rv.is_json is True
            self.compara_eventos(deepcopy(teste), rv.json)

    def test4_evento_duplicado_409(self):
        for classe, teste in self.testes.items():
            print(classe)
            rv = self.client.post(classe.lower(),
                                  json=teste,
                                  headers=self.headers)
            rv = self.client.post(classe.lower(),
                                  json=teste,
                                  headers=self.headers)
            assert rv.status_code == 409
            assert rv.is_json is True

    def _api_insert(self, classe, cadastro):
        print(classe)
        rv = self.client.post(classe.lower(),
                              json=cadastro,
                              headers=self.headers)
        assert rv.status_code == 201
        assert rv.is_json is True

    def _api_load(self, classe, cadastro):
        print(classe)
        rv = self.client.get(classe.lower() + '/' + str(cadastro['IDEvento']),
                             headers=self.headers)
        assert rv.status_code == 200
        assert rv.is_json is True
        self.compara_eventos(deepcopy(cadastro), rv.json)
