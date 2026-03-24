import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

async def main():
    dsn = "postgresql://postgres:mysecretpassword@localhost:5432/agentdb"
    async with AsyncConnectionPool(conninfo=dsn, row_factory=dict_row) as pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch_all("SELECT thread_id, title, user_id FROM threads ORDER BY created_at DESC LIMIT 5")
            print("--- Recent threads ---")
            for r in rows:
                print(f"{r['thread_id']} | {r['user_id']} | {r['title']}")

if __name__ == "__main__":
    asyncio.run(main())
