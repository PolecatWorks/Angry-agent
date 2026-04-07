import logging
from ..database import get_db_pool
from .embeddings import get_embeddings_model
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from ..config import ServiceConfig

logger = logging.getLogger(__name__)

async def save_agent_definition(name: str, content: str, config: ServiceConfig, agent_id: str = None) -> str:
    """
    Chunks, embeds, and saves an agent definition to the database.
    If agent_id is provided, it updates the existing agent (by deleting and re-inserting chunks).
    """
    logger.info(f"Splitting content into chunks for agent: {name}")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(content)
    logger.info(f"Created {len(chunks)} chunks")

    embedding_model = get_embeddings_model(config.embedding_client)
    logger.info("Generating embeddings for chunks...")
    embeddings = embedding_model.embed_documents(chunks)

    is_update = bool(agent_id)
    if not agent_id:
        agent_id = str(uuid.uuid4())

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if is_update:
                # Update existing record
                await conn.execute(
                    "UPDATE agent_definitions SET name = $1, content = $2 WHERE id = $3::uuid",
                    name, content, agent_id
                )
                # Delete existing chunks to replace them
                await conn.execute(
                    "DELETE FROM agent_definition_chunks WHERE agent_id = $1::uuid",
                    agent_id
                )
            else:
                # Insert new record
                await conn.execute(
                    "INSERT INTO agent_definitions (id, name, content) VALUES ($1::uuid, $2, $3)",
                    agent_id, name, content
                )

            # Insert chunks
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = str(uuid.uuid4())
                # Format list as postgres vector string: "[1.0, 2.0, ...]"
                embedding_str = "[" + ",".join(map(str, embedding)) + "]"

                await conn.execute(
                    """
                    INSERT INTO agent_definition_chunks (id, agent_id, chunk_index, content, embedding)
                    VALUES ($1::uuid, $2::uuid, $3, $4, $5::vector)
                    """,
                    chunk_id, agent_id, i, chunk, embedding_str
                )

    logger.info(f"Successfully saved agent '{name}' with ID: {agent_id}")
    return agent_id

async def delete_agent_definition(agent_id: str) -> None:
    """Deletes an agent definition and its chunks from the database."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Chunks should be deleted automatically if there's a cascade, but doing it explicitly just in case
            await conn.execute("DELETE FROM agent_definition_chunks WHERE agent_id = $1::uuid", agent_id)
            await conn.execute("DELETE FROM agent_definitions WHERE id = $1::uuid", agent_id)

async def get_all_agent_definitions() -> list[dict]:
    """Retrieves all agent definitions (without chunks)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, content FROM agent_definitions ORDER BY name")
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "content": row["content"]
            }
            for row in rows
        ]

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
