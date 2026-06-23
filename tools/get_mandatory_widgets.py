import ast
import os


def extract_string_list(node):
	"""
		["a", "b"]
		("a", "b")
	"""
	if isinstance(node, (ast.List, ast.Tuple)):
		result = []

		for item in node.elts:
			if isinstance(item, ast.Constant) and isinstance(item.value, str):
				result.append(item.value)

		return result

	return None


def extract_skin_names(init_func):
	"""
		self.skinName = "Name"
		self.skinName = ["Name1", "Name2"]
	"""

	for stmt in init_func.body:
		if not isinstance(stmt, ast.Assign):
			continue

		for target in stmt.targets:
			if (
				isinstance(target, ast.Attribute)
				and isinstance(target.value, ast.Name)
				and target.value.id == "self"
				and target.attr == "skinName"
			):
				value = stmt.value

				if isinstance(value, ast.Constant) and isinstance(value.value, str):
					return [value.value]

				names = extract_string_list(value)
				if names:
					return names

	return None


def extract_mandatory_widgets(init_func):
	"""
	Screen.__init__(..., mandatoryWidgets=[...])
	"""

	for node in ast.walk(init_func):
		if not isinstance(node, ast.Call):
			continue

		func = node.func

		if not (
			isinstance(func, ast.Attribute)
			and isinstance(func.value, ast.Name)
			and func.value.id == "Screen"
			and func.attr == "__init__"
		):
			continue

		for kw in node.keywords:
			if kw.arg == "mandatoryWidgets":
				widgets = extract_string_list(kw.value)
				if widgets:
					return widgets

	return None


def build_widget_dict(root_dir):
	result = {}

	for root, _, files in os.walk(root_dir):
		for filename in files:
			if not filename.endswith(".py"):
				continue

			path = os.path.join(root, filename)

			try:
				with open(path, "r", encoding="utf-8") as f:
					source = f.read()

				tree = ast.parse(source, filename=path)

			except Exception as e:
				print(f"Fehler: {path}: {e}")
				continue

			for node in tree.body:
				if not isinstance(node, ast.ClassDef):
					continue

				init_func = None

				for item in node.body:
					if isinstance(item, ast.FunctionDef) and item.name == "__init__":
						init_func = item
						break

				if init_func is None:
					continue

				widgets = extract_mandatory_widgets(init_func)

				if not widgets:
					continue

				skin_names = extract_skin_names(init_func)

				if skin_names:
					names = skin_names
				else:
					names = [node.name]

				for name in names:
					result[name] = widgets

	return result


def format_widget_dict(data):
	lines = ["MANDATORY_WIDGETS = {"]
	for key in sorted(data.keys()):
		values = ", ".join(f'"{v}"' for v in data[key])
		lines.append(f'\t"{key}": [{values}],')
	lines.append("}")
	return "\n".join(lines)


def update_skin_py(skin_path, data):
	with open(skin_path, encoding="utf-8") as f:
		content = f.read()

	start_marker = "# START\n"
	end_marker = "\n# END"
	start = content.find(start_marker)
	end = content.find(end_marker)

	if start == -1 or end == -1:
		print("ERROR: Markers '# START' / '# END' not found in skin.py")
		return False

	new_block = format_widget_dict(data)
	new_content = content[:start + len(start_marker)] + new_block + content[end:]

	if new_content == content:
		print("skin.py is already up to date.")
		return False

	with open(skin_path, "w", encoding="utf-8") as f:
		f.write(new_content)

	print(f"skin.py updated: {len(data)} entries written.")
	return True


if __name__ == "__main__":
	root_dir = os.path.abspath(
		os.path.join(
			os.path.dirname(__file__),
			"..",
			"lib",
			"python"
		)
	)
	skin_py = os.path.join(root_dir, "skin.py")

	data = build_widget_dict(root_dir)
	update_skin_py(skin_py, data)
