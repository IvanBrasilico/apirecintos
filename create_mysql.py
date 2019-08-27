import os

from apiserver.models import orm

if __name__ == '__main__':
    MYSQLURI = os.environ.get('JAWSDB_URL',
                              'mysql+mysqlconnector://apirecintos@localhost/apirecintos')
    session, engine = orm.init_db(MYSQLURI)
    orm.Base.metadata.drop_all(bind=engine)
    orm.Base.metadata.create_all(bind=engine)
