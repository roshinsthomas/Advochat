from unittest.mock import Mock

from django.test import SimpleTestCase

from .services.section_lookup import (
    SectionLookup,
    extract_section_numbers,
)


class SectionLookupTests(SimpleTestCase):
    def test_explicit_section_numbers(self):
        self.assertEqual(
            extract_section_numbers("Is there a section 321?"),
            ["321"],
        )
        self.assertEqual(
            extract_section_numbers("Compare sections 321 and 324"),
            ["321", "324"],
        )
        self.assertEqual(
            extract_section_numbers("Explain section 498a"),
            ["498A"],
        )

    def test_ordinary_numbers_are_not_section_references(self):
        self.assertEqual(
            extract_section_numbers("Someone took 321 rupees."),
            [],
        )

    def test_missing_section_returns_no_substitute(self):
        collection = Mock()
        collection.get.return_value = {
            "ids": [],
            "documents": [],
            "metadatas": [],
        }

        results = SectionLookup(collection).fetch(["321"])

        self.assertEqual(results, [])
        collection.get.assert_called_once_with(
            where={"section_number": "321"},
            include=["documents", "metadatas"],
        )
        collection.query.assert_not_called()