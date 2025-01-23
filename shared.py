# No global state, pls
from src.config import Config
from src.base import Base

config = Config(
        app_name=__name__,
        database_url="database1.db",
        host="0.0.0.0",
        port=5002,
        debug=True
)


base = Base(database=config.database)

def get_conn():
    if 'conn' not in g:
        g.conn = base.get_db_connection()
    return g.base


