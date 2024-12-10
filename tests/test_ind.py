#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import xml.etree.ElementTree as ET
from argparse import Namespace
from pathlib import Path
from typing import Any, Generator

import pytest

from ind import Tree, TreeNode, main


@pytest.fixture
def temp_structure() -> Generator[Path, None, None]:
    """
    Создает временную файловую структуру для тестов.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Создаем тестовые файлы и папки
        (base_path / "folder1").mkdir()
        (base_path / "folder1" / "file1.txt").write_text("Test file 1")
        (base_path / "folder1" / "file2.txt").write_text("Test file 2")
        (base_path / "folder1" / ".hidden").write_text("Hidden file")
        (base_path / "folder2").mkdir()
        (base_path / "folder2" / "subfolder1").mkdir()
        (base_path / "folder2" / "subfolder1" / "file3.txt").write_text("Test file 3")

        yield base_path


def test_tree(temp_structure: Path) -> None:
    args = Namespace(
        a=False,
        d=False,
        f=False,
        max_depth=None,
        i=False,
    )
    tree = Tree(temp_structure, args)

    assert isinstance(tree.root, TreeNode)
    assert isinstance(tree.root.state, Path)
    assert isinstance(tree.root.children, list)
    assert isinstance(tree.root.children[0], TreeNode)
    assert isinstance(tree.root.children[0].state, Path)

    assert tree.dir_count == 3
    assert tree.file_count == 3

    folder1 = next(
        child for child in tree.root.children if child.state.name == "folder1"
    )
    folder2 = next(
        child for child in tree.root.children if child.state.name == "folder2"
    )

    assert len(folder1) == 2
    assert len(folder2) == 1

    args.a = True
    tree = Tree(temp_structure, args)

    assert tree.dir_count == 3
    assert tree.file_count == 4

    args.d = True
    tree = Tree(temp_structure, args)

    assert tree.dir_count == 3
    assert tree.file_count == 0

    folder1 = next(
        child for child in tree.root.children if child.state.name == "folder1"
    )
    folder2 = next(
        child for child in tree.root.children if child.state.name == "folder2"
    )

    assert len(folder1) == 0
    assert len(folder2) == 1

    args.i = True
    args.f = True
    args.d = False
    tree = Tree(temp_structure, args)
    s = str(tree)
    assert "folder1" in s
    assert "folder2" in s
    assert "folder1\\file1.txt" in s
    assert "folder1\\.hidden" in s

    args.max_depth = 1
    tree = Tree(temp_structure, args)
    s = str(tree)
    assert "folder1" in s
    assert "subfolder1" not in s

    for i in range(3, 210):
        (temp_structure / f"folder{i}").mkdir()

    tree = Tree(temp_structure, args)
    s = str(tree)
    assert "Output limited to 200 elements." in s


def test_tree_node(temp_structure: Path) -> None:
    node = TreeNode(temp_structure)
    node.add_child(TreeNode(temp_structure / "folder1"))
    node.add_child(TreeNode(temp_structure / "folder2"))

    assert len(node) == 2
    assert node.children == [
        TreeNode(temp_structure / "folder1"),
        TreeNode(temp_structure / "folder2"),
    ]


def test_main(capsys: pytest.CaptureFixture[Any], temp_structure: Path) -> None:
    args = "-a -i ".split() + [str(temp_structure)]
    main(args)

    captured = capsys.readouterr()

    assert "folder1" in captured.out
    assert "folder2" in captured.out

    assert "folder1\\file1.txt" not in captured.out
    assert ".hidden" in captured.out

    args = ["example"]

    with pytest.raises((FileNotFoundError, SystemExit)):
        main(args)


def test_save_to_xml(temp_structure: Path, tmp_path: Path) -> None:
    args = Namespace(
        a=True,
        d=False,
        f=False,
        max_depth=None,
        i=False,
        output="output.xml",
    )
    output_path = tmp_path / args.output

    tree = Tree(temp_structure, args)
    tree.save_xml(output_path)

    assert output_path.exists()

    xml_tree = ET.parse(output_path)
    root = xml_tree.getroot()

    assert root.tag == "node"
    assert root.attrib["name"] == f"{temp_structure.name}/"

    folder1 = next(child for child in root if child.attrib["name"] == "folder1/")
    folder2 = next(child for child in root if child.attrib["name"] == "folder2/")

    assert folder1.tag == "node"
    assert folder2.tag == "node"

    file1 = next(child for child in folder1 if child.attrib["name"] == "file1.txt")
    hidden_file = next(child for child in folder1 if child.attrib["name"] == ".hidden")

    assert file1.tag == "node"
    assert hidden_file.tag == "node"

    subfolder1 = next(
        child for child in folder2 if child.attrib["name"] == "subfolder1/"
    )
    assert subfolder1.tag == "node"
    file3 = next(child for child in subfolder1 if child.attrib["name"] == "file3.txt")
    assert file3.tag == "node"
