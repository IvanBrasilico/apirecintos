from apiserver.models import orm
from apiserver.use_cases.usecases import UseCases
from tests.basetest import BaseTestCase


class UseCaseTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.usecase = UseCases(self.db_session, '')

    def _insert(self, classe_evento):
        evento = self.open_json_test_case(classe_evento)
        return self.usecase.insert_evento(classe_evento,
                                          evento)

    def _load(self, classe_evento, IDEvento):
        return self.usecase.load_evento(classe_evento,
                                        IDEvento)

    def _insert_and_load(self, classe_evento):
        evento = self.open_json_test_case(classe_evento)
        evento_banco = self._insert(classe_evento)
        evento_banco_load = self._load(classe_evento, evento['IDEvento'])

        self.compara_eventos(evento, evento_banco.dump())
        self.compara_eventos(evento, evento_banco_load.dump())

    """
    def test_PesagemVeiculoCarga(self):
        self._insert_and_load(orm.PesagemVeiculoCarga)
    """

    def test_InspecaonaoInvasiva(self):
        evento = self.open_json_test_case(orm.InspecaonaoInvasiva)
        evento_banco = self.usecase.insert_inspecaonaoinvasiva(evento)

        self.compara_eventos(evento, evento_banco.dump())
        evento_banco_load = self.usecase.load_inspecaonaoinvasiva(
            evento['codRecinto'],
            evento['idEvento'])
        print(sorted(evento.items(), key = lambda x: x[0]))
        print(sorted(evento_banco_load.items(), key = lambda x: x[0]))
        self.compara_eventos(evento, evento_banco_load)
        # print(sorted(evento_banco.dump().items(), key = lambda x: x[0]))
        assert False
