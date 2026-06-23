import os
import unittest
from xml_validator import XMLFileMixin

_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class TestDefaultSkin(XMLFileMixin, unittest.TestCase):
    XML_PATH = os.path.normpath(os.path.join(_DATA, "skin_default.xml"))
    REPO_PATH = "data/skin_default.xml"
