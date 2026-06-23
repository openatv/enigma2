import os
import pytest
from xml_validator import validate_xml_file

_REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _collect(*dirs):
    result = []
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in sorted(files):
                if f.endswith(".xml"):
                    result.append(os.path.join(root, f))
    return result


_XML_FILES = _collect(
    os.path.join(_REPO, "data"),
    os.path.join(_REPO, "lib"),
)


@pytest.mark.parametrize(
    "xml_path",
    _XML_FILES,
    ids=lambda p: os.path.relpath(p, _REPO),
)
def test_xml_valid(xml_path):
    validate_xml_file(xml_path, os.path.relpath(xml_path, _REPO))
