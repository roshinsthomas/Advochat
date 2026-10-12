import re


class SectionSplitter:
    # Match chapter headings, including amendment prefixes such as 3[.
    CHAPTER_PATTERN = re.compile(
        r"^(?:\d+\[|\[)*CHAPTER\s+[IVXLCDM]+A?\b"
    )

    SECTION_PATTERN = re.compile(
        r"^(?:\d+\[|\[)*"
        r"(?P<number>\d{1,3}[A-Z]{0,2}"
        r"(?:[ \t]+to[ \t]+\d{1,3}[A-Z]{0,2})?)"
        r"(?:\.[ \t]+|[ \t]+(?=“Government”))"
    )

    def split(self, pages: list[dict]) -> list[dict]:
        sections = []
        current_section = None

        for page in pages:
            for raw_line in page["text"].splitlines():
                line = raw_line.strip()

                if not line:
                    continue

                # A chapter heading ends the preceding section.
                if self.CHAPTER_PATTERN.match(line):
                    if current_section is not None:
                        sections.append(current_section)
                        current_section = None
                    continue

                match = self.SECTION_PATTERN.match(line)

                if match:
                    if current_section is not None:
                        sections.append(current_section)

                    current_section = {
                        "section_number": match.group("number"),
                        "text": line,
                        "page_start": page["page_number"],
                        "page_end": page["page_number"],
                    }

                elif current_section is not None:
                    # Continue the same section, including on the next page.
                    current_section["text"] += "\n" + line
                    current_section["page_end"] = page["page_number"]

        # Save the final section because no next heading follows it.
        if current_section is not None:
            sections.append(current_section)

        if not sections:
            raise ValueError("No section headings were detected.")

        return sections