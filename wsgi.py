import sys

from apiserver.models import orm

sys.path.insert(0, './apiserver')

from apiserver.main import create_app

session, engine = orm.init_db() # 'sqlite:///:memory:')
# print(orm.Base.metadata.tables)
orm.Base.metadata.drop_all(bind=engine)
orm.Base.metadata.create_all(bind=engine)
app = create_app(session, engine)

if __name__ == '__main__':
    app.run(port=8000, threaded=False, debug=True)