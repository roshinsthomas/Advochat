import re


# Supports "section 321", "sec. 324", and "sections 321 and 324".
NUMBER = r"\d{1,4}[A-Za-z]{0,2}\b"
LABEL = r"(?:sections?|secs?\.?)"

SECTION_PATTERN = re.compile(
    rf"\b{LABEL}\s*(?:no\.?\s*)?"
    rf"(?P<numbers>{NUMBER}"
    rf"(?:\s*(?:,|and\b|&|versus\b|vs\.?)\s*"
    rf"(?:{LABEL}\s*)?{NUMBER})*)",
    re.IGNORECASE,
)


def extract_section_numbers(query):
    numbers = []

    for match in SECTION_PATTERN.finditer(query):
        for number in re.findall(NUMBER, match.group("numbers")):
            number = number.upper()

            if number not in numbers:
                numbers.append(number)

    return numbers


class SectionLookup:
    def __init__(self, collection):
        self.collection = collection

    def fetch(self, section_numbers):
        results = []

        for section_number in section_numbers:
            data = self.collection.get(
                where={"section_number": section_number},
                include=["documents", "metadatas"],
            )

            # A missing section must not be replaced with a similar one.
            if not data["ids"]:
                continue

            ordered = sorted(
                zip(data["metadatas"], data["documents"]),
                key=lambda item: item[0]["chunk_index"],
            )

            metadata = ordered[0][0]

            # Preserve every indexed chunk, in its original chunk order.
            passages = list(dict.fromkeys(
                document for _, document in ordered
            ))

            results.append({
                "section_number": section_number,
                "matched_chunk": "\n\n".join(passages),
                "opening_chunk": "",
                "chunk_index": 0,
                "page_start": metadata["section_page_start"],
                "page_end": metadata["section_page_end"],
                "source_file": metadata["source_file"],
                "source_scope": metadata["source_scope"],
                "retrieval_method": "exact_section",
                "vector_distance": None,
                "reranker_score": None,
            })

        return results