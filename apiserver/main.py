import connexion

from apiserver.models import orm
from apiserver.views import create_views
from apiserver.authentication import configure_signature


def create_app(session, engine):  # pragma: no cover
    app = connexion.FlaskApp(__name__)
    app.add_api('openapi.yaml')
    app.app.config['db_session'] = session
    app.app.config['engine'] = engine
    print('Configurou app')
    create_views(app)
    configure_signature(app)
    print('Configurou views')
    return app


def main():  # pragma: no cover
    # session, engine = orm.init_db('sqlite:///:memory:')
    # orm.Base.metadata.create_all(bind=engine)
    session, engine = orm.init_db()
    app = create_app(session, engine)
    print(app.app.config['db_session'])
    app.run(debug=True, port=8000, threaded=False)


if __name__ == '__main__':  # pragma: no cover
    main()
