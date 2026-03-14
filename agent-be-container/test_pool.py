import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

async def main():
    pool_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
    }
    
    pool = AsyncConnectionPool(
        conninfo="postgres://angry-agent:testingtesting@angry-agent-pgbouncer-postgres.angry-agent:5432/angry_agent",
        kwargs=pool_kwargs,
        check=AsyncConnectionPool.check_connection
    )
    import pprint
    pprint.pprint(dir(pool))

asyncio.run(main())
