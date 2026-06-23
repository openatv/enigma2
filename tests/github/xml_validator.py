import os
import unittest
import xml.etree.ElementTree as ET


def validate_xml_file(abs_path, repo_rel_path=None):
    """
    Validate an XML file. Intended for use inside unittest.TestCase methods.

    abs_path      -- absolute path to the XML file
    repo_rel_path -- repo-relative path used for GitHub Actions annotations
                     (e.g. "data/skin_default.xml"). Falls back to abs_path.
    """
    annotation_path = repo_rel_path or abs_path

    if not os.path.isfile(abs_path):
        raise unittest.SkipTest(f"File not found: {abs_path}")

    try:
        ET.parse(abs_path)
    except ET.ParseError as e:
        line, col = e.position
        print(f"\n::error file={annotation_path},line={line},col={col}::{e}")
        raise AssertionError(
            f"{annotation_path}: XML parse error at line {line}, col {col}: {e}"
        ) from None


class XMLFileMixin:
    """
    Mixin for XML file tests. Combine with unittest.TestCase in subclasses:

        class TestMySkin(XMLFileMixin, unittest.TestCase):
            XML_PATH  = "/abs/path/to/file.xml"
            REPO_PATH = "relative/path/for/github/annotation.xml"
    """

    XML_PATH: str = ""
    REPO_PATH: str = ""

    def test_file_exists(self):
        self.assertTrue(
            os.path.isfile(self.XML_PATH),
            f"File not found: {self.XML_PATH}",
        )

    def test_xml_is_valid(self):
        validate_xml_file(self.XML_PATH, self.REPO_PATH or self.XML_PATH)
