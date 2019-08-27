from sqlalchemy.exc import IntegrityError

from apiserver.models import orm
from apiserver.use_cases.usecases import UseCases
from tests.basetest import BaseTestCase

RECINTO = '00001'
REQUEST_IP = '10.10.10.10'


class UseCaseTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.usecase = UseCases(self.db_session, RECINTO, REQUEST_IP, '')

    def _insert(self, classe_evento):
        evento = self.testes[classe_evento.__name__]
        return self.usecase.insert_evento(classe_evento,
                                          evento)

    def _load(self, classe_evento, IDEvento):
        return self.usecase.load_evento(classe_evento,
                                        IDEvento)

    def _insert_and_load(self, classe_evento):
        evento = self.testes[classe_evento.__name__]
        evento_banco = self._insert(classe_evento)
        evento_banco_load = self._load(classe_evento, evento['IDEvento'])
        self.compara_eventos(evento, evento_banco.dump())
        self.compara_eventos(evento, evento_banco_load.dump())

    def test_PesagemMaritimo(self):
        self._insert_and_load(orm.PesagemMaritimo)

    def test_InspecaonaoInvasiva(self):
        evento = self.testes['InspecaonaoInvasiva']
        evento_banco = self.usecase.insert_inspecaonaoinvasiva(evento)

        self.compara_eventos(evento, evento_banco.dump())
        evento_banco_load = self.usecase.load_inspecaonaoinvasiva(evento['IDEvento'])
        self.compara_eventos(evento, evento_banco_load)
