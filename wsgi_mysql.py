import os
import sys

from apiserver.models import orm

sys.path.insert(0, './apiserver')

from apiserver.main import create_app

MYSQLURI = os.environ.get('JAWSDB_URL',
                          'mysql+mysqlconnector://apirecintos@localhost/apirecintos')
session, engine = orm.init_db(MYSQLURI)
app = create_app(session, engine)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
