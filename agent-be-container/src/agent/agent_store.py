import logging
from ..database import get_db_pool
from .embeddings import get_embeddings_model
from ..config import ServiceConfig

logger = logging.getLogger(__name__)

async def search_agent_definitions(query: str, config: ServiceConfig, limit: int = 5) -> list[dict]:
    """
    Embeds the search query and searches the agent_definition_chunks table
    for the most relevant agent definitions using cosine similarity.
    """
    logger.info(f"Searching agent definitions for query: {query}")

    # Get the embedding model
    embedding_model = get_embeddings_model(config.embedding_client)

    # Generate embedding for the query
    query_embedding = embedding_model.embed_query(query)

    # Format the embedding as a string for pgvector insertion
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    # Search the database using cosine similarity (<=>)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # PostgreSQL STRICT TYPE CASTING is required for vector parameter in asyncpg ($1::vector)
        sql_query = """
            WITH ranked_chunks AS (
                SELECT
                    agent_id,
                    content AS chunk_content,
                    1 - (embedding <=> $1::vector) AS similarity,
                    ROW_NUMBER() OVER(PARTITION BY agent_id ORDER BY embedding <=> $1::vector) as rn
                FROM agent_definition_chunks
            )
            SELECT
                ad.id,
                ad.name,
                ad.content AS full_content,
                rc.chunk_content AS top_chunk,
                rc.similarity
            FROM ranked_chunks rc
            JOIN agent_definitions ad ON ad.id = rc.agent_id
            WHERE rc.rn = 1
            ORDER BY rc.similarity DESC
            LIMIT $2
        """

        rows = await conn.fetch(sql_query, embedding_str, limit)

        results = []
        for row in rows:
            results.append({
                "id": str(row["id"]),
                "name": row["name"],
                "full_content": row["full_content"],
                "top_chunk": row["top_chunk"],
                "similarity": float(row["similarity"])
            })

    logger.info(f"Found {len(results)} matching agent definitions")
    return results
