from tokenizers import Tokenizer


class TokenChunker:
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    MODEL_TOKEN_LIMIT = 256

    def __init__(self, chunk_size: int = 200, overlap: int = 30):
        if not 0 <= overlap < chunk_size <= 254:
            raise ValueError(
                "Use 0 <= overlap < chunk_size <= 254."
            )

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.tokenizer = Tokenizer.from_pretrained(self.MODEL_NAME)

        # Read all tokens without truncating or adding padding.
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()

    def split(self, sections: list[dict]) -> list[dict]:
        chunks = []

        for section in sections:
            text = section["text"]
            encoding = self.tokenizer.encode(
                text, add_special_tokens=False
            )
            offsets = encoding.offsets
            start = 0
            chunk_index = 0

            while start < len(offsets):
                end = min(start + self.chunk_size, len(offsets))

                # Slice the original text using token character positions.
                char_start = offsets[start][0]
                char_end = offsets[end - 1][1]
                chunk_text = text[char_start:char_end]

                # Recheck the actual chunk, including model special tokens.
                token_count = len(
                    self.tokenizer.encode(chunk_text).ids
                )

                if token_count > self.MODEL_TOKEN_LIMIT:
                    raise ValueError(
                        f"Chunk exceeds token limit in "
                        f"section {section['section_number']}."
                    )

                chunks.append({
                    "section_number": section["section_number"],
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "section_page_start": section["page_start"],
                    "section_page_end": section["page_end"],
                    "token_count": token_count,
                })

                if end == len(offsets):
                    break

                start = end - self.overlap
                chunk_index += 1

        return chunks