import re


class IPCPageCleaner:
    def clean(self, pages: list[dict], start_page: int = 15) -> list[dict]:
        cleaned_pages = []

        for page in pages:
            if page["page_number"] < start_page:
                continue

            text = page["text"]

            # Remove the standalone page number at the beginning.
            text = re.sub(r"\A\s*\d+\s*\n", "", text, count=1)

            # This PDF extracts its footnote separator as a whitespace line.
            parts = re.split(r"\n[ \t]{10,}\n", text, maxsplit=1)

            cleaned_pages.append({
                "page_number": page["page_number"],
                "text": parts[0].strip(),
                "footnotes": parts[1].strip() if len(parts) > 1 else "",
            })

        return cleaned_pages