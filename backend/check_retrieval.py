import numpy as np
from django.conf import settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from chatbot.services.vector_store import ChromaVectorStore


def main():
    # Open the existing database; no PDF processing is needed.
    store = ChromaVectorStore(
        storage_path=settings.BASE_DIR / "data" / "chroma"
    )

    result = store.collection.get(
        where={"section_number": "378"},
        include=["documents", "metadatas"],
    )

    if not result["ids"]:
        print("Section 378 was not found. Check the database path and collection.")
        return

    # Find the first chunk using its metadata.
    ordered_chunks = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda item: item[0]["chunk_index"],
    )

    full_chunk = ordered_chunks[0][1]

    if "Explanation 1" not in full_chunk:
        print("Expected explanation boundary was not found.")
        return

    definition = full_chunk.split("Explanation 1", 1)[0].strip()
    query = "Someone secretly took my phone without my permission."

    embed = DefaultEmbeddingFunction()
    vectors = np.asarray(
        embed(input=[query, full_chunk, definition])
    )

    # Compare the question with both versions using cosine distance.
    query_vector = vectors[0]
    distances = 1 - (
        vectors[1:] @ query_vector
    ) / (
        np.linalg.norm(vectors[1:], axis=1)
        * np.linalg.norm(query_vector)
    )

    print("Query:", query)
    print("Full chunk distance:", round(float(distances[0]), 4))
    print("Definition-only distance:", round(float(distances[1]), 4))


main()