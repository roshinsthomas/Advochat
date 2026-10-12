import chromadb

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from django.conf import settings
from sentence_transformers import CrossEncoder


class SemanticSearchService:
    COLLECTION_NAME = "ipc_structured_v2_d0950579cf0e"
    RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"

    def __init__(self):
        client = chromadb.PersistentClient(
            path=str(settings.BASE_DIR / "data" / "chroma")
        )

        # Open the existing collection; do not create an empty one.
        self.collection = client.get_collection(
            name=self.COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
        )

        self.reranker = CrossEncoder(
            self.RERANKER_MODEL,
            max_length=512,
            device="cpu",
        )

    def search(self, query, limit=5, candidate_count=60):
        query = query.strip()

        if not query:
            raise ValueError("Please provide a search question.")

        if not 1 <= limit <= candidate_count:
            raise ValueError(
                "Use 1 <= limit <= candidate_count."
            )

        count = self.collection.count()

        if count == 0:
            return []

        # Stage 1: retrieve a wider set using vector similarity.
        candidates = self.collection.query(
            query_texts=[query],
            n_results=min(candidate_count, count),
            include=["documents", "metadatas", "distances"],
        )

        documents = candidates["documents"][0]
        metadatas = candidates["metadatas"][0]
        distances = candidates["distances"][0]

        # Stage 2: score the question and each passage together.
        scores = self.reranker.predict(
            [(query, document) for document in documents],
            batch_size=16,
            show_progress_bar=False,
        )

        ranked = sorted(
            zip(documents, metadatas, distances, scores),
            key=lambda item: float(item[3]),
            reverse=True,
        )

        results = []
        seen_sections = set()

        # Return distinct sections, keeping each one's best passage.
        for document, metadata, distance, score in ranked:
            section_number = metadata["section_number"]

            if section_number in seen_sections:
                continue

            seen_sections.add(section_number)

            results.append({
                "section_number": section_number,
                "matched_chunk": document,
                "chunk_index": metadata["chunk_index"],
                "page_start": metadata["section_page_start"],
                "page_end": metadata["section_page_end"],
                "source_file": metadata["source_file"],
                "source_scope": metadata["source_scope"],
                "vector_distance": float(distance),
                "reranker_score": float(score),
            })

            if len(results) == limit:
                break

        # Include the opening provision even when an illustration matched.
        opening_ids = [
            f"section_{item['section_number']}_chunk_0"
            for item in results
        ]

        openings = self.collection.get(
            ids=opening_ids,
            include=["documents"],
        )

        opening_map = dict(
            zip(openings["ids"], openings["documents"])
        )

        for item, opening_id in zip(results, opening_ids):
            item["opening_chunk"] = opening_map.get(opening_id, "")

        return results

    def demo(self):
        queries = [
            "Someone secretly took my phone without my permission.",
            "Someone dishonestly took my movable property without my consent.",
            "Someone took my wallet from my bag while I was distracted.",
            "Someone threatened to hurt me unless I gave them money.",
        ]

        for query in queries:
            print("\n" + "=" * 60)
            print("Query:", query)

            for rank, result in enumerate(
                self.search(query), start=1
            ):
                preview = " ".join(
                    result["matched_chunk"].split()
                )[:180]

                print(
                    f"{rank}. Section {result['section_number']} | "
                    f"Score: {result['reranker_score']:.4f}"
                )
                print("  ", preview)