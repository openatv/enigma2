"""Exercise the actual TYPE converter and source updates without the receiver GUI."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]


def methods(path, names):
    tree = ast.parse((ROOT / path).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    constants = {
        node.targets[0].id: node.value.value
        for node in cls.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
    }
    namespace = {"cached": lambda function: function}
    nodes = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    constants.update({name: namespace[name] for name in names})
    return type("IsolatedComponent", (), constants)


class ScanTypeTest(unittest.TestCase):
    def test_all_frontend_types(self):
        component = methods("lib/python/Components/Converter/FrontendInfo.py", {"getValue"})()
        component.type = component.TUNER_TYPE
        for frontend, expected in [("DVB-S", 0), ("DVB-C", 1), ("DVB-T", 2), ("ATSC", 3), ("DAB", 4), (None, -1)]:
            component.source = SimpleNamespace(frontend_type=frontend)
            self.assertEqual(component.getValue(), expected)

    def test_dab_scan_survives_frontend_mask_updates(self):
        component = methods("lib/python/Components/Sources/FrontendInfo.py", {"updateFrontendData", "updateTunerMask"})()
        component.CHANGED_ALL = 0
        component.changed = lambda event: None
        component.getFrontendData = lambda: {}
        component.frontend_type_override = "DAB"
        component.updateFrontendData()
        self.assertEqual(component.frontend_type, "DAB")
        component.updateTunerMask(1)
        self.assertEqual(component.frontend_type, "DAB")
        component.frontend_type_override = None
        component.updateFrontendData()
        self.assertIsNone(component.frontend_type)


if __name__ == "__main__":
    unittest.main()
