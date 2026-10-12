from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class ChromaVectorStore:
    def __init__(
        self,
        storage_path: str | Path,
        collection_name: str = "ipc_sample_v1",
    ):
        self.client = chromadb.PersistentClient(
            path=str(storage_path)
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=DefaultEmbeddingFunction(),
            configuration={"hnsw": {"space": "cosine"}},
        )

    def store_chunks(self, chunks: list[dict]) -> int:
        # Process smaller batches to limit memory use.
        for start in range(0, len(chunks), 100):
            batch = chunks[start:start + 100]

            self.collection.upsert(
                ids=[
                    f"section_{chunk['section_number']}"
                    f"_chunk_{chunk['chunk_index']}"
                    for chunk in batch
                ],
                documents=[
                    chunk["text"] for chunk in batch
                ],
                metadatas=[
                    {
                        "section_number": chunk["section_number"],
                        "chunk_index": chunk["chunk_index"],
                        "section_page_start": chunk["section_page_start"],
                        "section_page_end": chunk["section_page_end"],
                        "token_count": chunk["token_count"],
                        "source_file": "ipc.pdf",
                        "source_scope": "historical_development_sample",
                    }
                    for chunk in batch
                ],
            )

        return self.collection.count()