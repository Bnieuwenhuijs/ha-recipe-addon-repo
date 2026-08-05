"""
Test die bewaakt dat alles wat de app importeert ook echt in het
container-image belandt. Een ontbrekende COPY in de Dockerfile merk je
anders pas als de add-on in Home Assistant niet meer opstart. Draai met:

    python -m unittest test_packaging.py -v
"""

import ast
import fnmatch
import pathlib
import unittest

ADDON_DIR = pathlib.Path(__file__).parent
DOCKERFILE = ADDON_DIR / "Dockerfile"
APP_MODULE = ADDON_DIR / "recipe_parser.py"


def local_imports_of(path: pathlib.Path):
    """Modules die dit bestand importeert en die hier als .py-bestand staan."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {n for n in names if (ADDON_DIR / f"{n}.py").exists()}


def dockerfile_copy_sources():
    sources = []
    for line in DOCKERFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.upper().startswith("COPY "):
            parts = line.split()[1:]
            sources.extend(parts[:-1])  # laatste argument is de bestemming
    return sources


class PackagingTests(unittest.TestCase):
    def test_imported_modules_are_copied_into_the_image(self):
        patterns = dockerfile_copy_sources()
        for module in sorted(local_imports_of(APP_MODULE)):
            filename = f"{module}.py"
            copied = any(fnmatch.fnmatch(filename, p) for p in patterns)
            self.assertTrue(
                copied,
                f"{filename} wordt geïmporteerd door recipe_parser.py maar door "
                f"geen enkele COPY in de Dockerfile gedekt: {patterns}",
            )

    def test_templates_are_copied_into_the_image(self):
        patterns = dockerfile_copy_sources()
        self.assertTrue(
            any(p.rstrip("/") == "templates" for p in patterns),
            f"templates/ ontbreekt in de COPY-regels: {patterns}",
        )


if __name__ == "__main__":
    unittest.main()
