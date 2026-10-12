import hashlib
import json
import re

from django.conf import settings

from chatbot.services.document_ingestor import DocumentIngestor
from chatbot.services.ipc_page_cleaner import IPCPageCleaner
from chatbot.services.section_splitter import SectionSplitter
from chatbot.services.token_chunker import TokenChunker
from chatbot.services.vector_store import ChromaVectorStore


class StructuredChunker:
    # Recognise explanation and illustration headings in this PDF.
    BLOCK_START = re.compile(
        r"(?m)^(?:\d+\[|\[)*"
        r"(?:Explanation(?:[ \t]+\d+)?|Illustrations?)"
        r"(?=[\s.—–:\]])"
    )

    def __init__(self):
        self.chunker = TokenChunker()
        self.tokenizer = self.chunker.tokenizer

    def split(self, sections):
        chunks = []

        for section in sections:
            text = section["text"].strip()

            # The section title usually ends with ".—".
            heading_match = re.search(r"\.\s*[—–]", text)

            if heading_match:
                heading = " ".join(
                    text[:heading_match.start() + 1].split()
                )
                body = text[heading_match.end():].strip()
            else:
                heading = f"Section {section['section_number']}"
                body = text

            heading_tokens = len(
                self.tokenizer.encode(
                    heading, add_special_tokens=False
                ).ids
            )

            # Avoid an unusually long heading consuming the token budget.
            if heading_tokens > 80:
                heading = f"Section {section['section_number']}"
                body = text
                heading_tokens = len(
                    self.tokenizer.encode(
                        heading, add_special_tokens=False
                    ).ids
                )

            # Reserve room for the heading and special tokens.
            self.chunker.chunk_size = 200 - heading_tokens - 8

            # Slice at structural boundaries, preserving the original text.
            boundaries = sorted({
                0,
                len(body),
                *(match.start() for match in self.BLOCK_START.finditer(body)),
            })

            chunk_index = 0

            for start, end in zip(boundaries, boundaries[1:]):
                block = body[start:end].strip()

                if not block:
                    continue

                block_section = {**section, "text": block}

                # Long blocks still use token windows with overlap.
                for chunk in self.chunker.split([block_section]):
                    chunk["text"] = f"{heading}\n{chunk['text']}"
                    chunk["chunk_index"] = chunk_index
                    chunk["token_count"] = len(
                        self.tokenizer.encode(chunk["text"]).ids
                    )

                    if chunk["token_count"] > 256:
                        raise ValueError(
                            "Token limit exceeded in section "
                            f"{section['section_number']}"
                        )

                    chunks.append(chunk)
                    chunk_index += 1

        if not chunks:
            raise ValueError("No chunks were generated.")

        return chunks


class SearchRebuilder:
    QUERIES = [
        "Someone secretly took my phone without my permission.",
        "Someone dishonestly took my movable property without my consent.",
        "Someone took my wallet from my bag while I was distracted.",
        "Someone threatened to hurt me unless I gave them money.",
    ]

    def print_results(self, label, store):
        count = store.collection.count()

        if count == 0:
            print(f"\n{label}: collection is empty.")
            return

        results = store.collection.query(
            query_texts=self.QUERIES,
            n_results=min(5, count),
            include=["documents", "metadatas", "distances"],
        )

        print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")

        for index, query in enumerate(self.QUERIES):
            print(f"\nQuery: {query}")

            rows = zip(
                results["metadatas"][index],
                results["documents"][index],
                results["distances"][index],
            )

            for rank, (metadata, document, distance) in enumerate(
                rows, start=1
            ):
                preview = " ".join(document.split())[:140]
                print(
                    f"{rank}. Section {metadata['section_number']} | "
                    f"Chunk {metadata['chunk_index']} | "
                    f"Distance {distance:.4f}"
                )
                print(f"   {preview}")

    def run(self):
        pdf_path = settings.BASE_DIR / "data" / "raw" / "ipc.pdf"
        storage_path = settings.BASE_DIR / "data" / "chroma"

        print("Reading PDF...")
        pages = DocumentIngestor(pdf_path).extract_pages()
        cleaned_pages = IPCPageCleaner().clean(pages)
        sections = SectionSplitter().split(cleaned_pages)

        print("Creating structured chunks...")
        chunks = StructuredChunker().split(sections)

        print("Sections:", len(sections))
        print("Chunks:", len(chunks))
        print("Largest chunk:", max(c["token_count"] for c in chunks))

        # Same chunks produce the same collection name.
        # Changed chunks get a separate collection, avoiding stale records.
        fingerprint = hashlib.sha256(
            json.dumps(
                chunks, sort_keys=True, ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()[:12]

        collection_name = f"ipc_structured_v2_{fingerprint}"

        new_store = ChromaVectorStore(
            storage_path=storage_path,
            collection_name=collection_name,
        )

        print("Storing embeddings; this may take a little time...")
        stored_count = new_store.store_chunks(chunks)

        if stored_count != len(chunks):
            raise RuntimeError(
                f"Expected {len(chunks)} records, found {stored_count}."
            )

        old_store = ChromaVectorStore(
            storage_path=storage_path,
            collection_name="ipc_sample_v1",
        )

        self.print_results("ORIGINAL CHUNKING", old_store)
        self.print_results("STRUCTURED CHUNKING", new_store)

        print("\nRebuild complete.")
        print("New collection:", collection_name)
        print("Stored chunks:", stored_count)


SearchRebuilder().run()