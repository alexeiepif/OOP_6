#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Разработайте аналог утилиты tree в Linux.
# Используйте возможности модуля argparse для
# управления отображением дерева каталогов файловой системы.
# Добавьте дополнительные уникальные возможности в данный программный продукт.
# Выполнить индивидуальное задание 2 лабораторной работы 2.19,
# добавив аннтотации типов.
# Выполнить проверку программы с помощью утилиты mypy.
# Выполнить индивидуальное задание лабораторной работы 4.5, использовав классы данных, а
# также загрузку и сохранение данных в формат XML.

import argparse
import bisect
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from xml.dom import minidom

from colorama import Fore, Style


@dataclass
class TreeNode:
    state: Path
    children: list["TreeNode"] = field(default_factory=list)

    def add_child(self, child: "TreeNode") -> None:
        bisect.insort(self.children, child)

    def __repr__(self) -> str:
        return f"<{self.state}>"

    def __len__(self) -> int:
        return len(self.children)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TreeNode):
            return NotImplemented
        return self.state == other.state and self.children == other.children

    def __lt__(self, other: "TreeNode") -> bool:
        return len(self) < len(other)


@dataclass
class Tree:
    directory: Path
    args: argparse.Namespace = field(default_factory=argparse.Namespace)
    root: TreeNode = field(init=False)
    dir_count: int = field(init=False, default=0)
    file_count: int = field(init=False, default=0)
    full: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self.root = TreeNode(self.directory)
        self.generate_tree(self.root, 0)

    def expand(self, node: TreeNode) -> None:
        try:
            for child in node.state.iterdir():
                if not self.__should_include(child):
                    continue
                self.__increment_counts(child)
                if self.full:
                    break
                node.add_child(TreeNode(child))
        except PermissionError:
            pass

    def generate_tree(self, node: TreeNode, level: int) -> None:
        if self.full or level == self.args.max_depth:
            return
        self.expand(node)
        for child in node.children:
            if child.state.is_dir():
                self.generate_tree(child, level + 1)

    def __should_include(self, child: Path) -> bool:
        if not self.args.a and child.name.startswith((".", "__")):
            return False
        if self.args.d and child.is_file():
            return False
        return True

    def __increment_counts(self, child: Path) -> None:
        if child.is_dir():
            self.dir_count += 1
        else:
            self.file_count += 1
        if self.dir_count + self.file_count >= 200:
            self.full = True

    def __format_tree(self, node: TreeNode, branch: str = "") -> str:
        result = StringIO()
        for i, child in enumerate(node.children):
            item = f"{branch}{'└── ' if i == len(node.children) - 1 else '├── '}"
            name = (
                child.state.name
                if not self.args.f
                else child.state.relative_to(self.directory)
            )
            color = Fore.GREEN if child.state.is_file() else Fore.YELLOW
            result.write(f"{item}{color}{name}{Style.RESET_ALL}\n")
            new_branch = f"{branch}{'    ' if i == len(node.children) - 1 else '│   '}"
            result.write(self.__format_tree(child, new_branch))
        return result.getvalue()

    def __str__(self) -> str:
        header = f"{Fore.BLUE}{self.root.state.name}{Style.RESET_ALL}\n"
        body = self.__format_tree(self.root)
        footer = f"\n{Fore.YELLOW}Directories: {self.dir_count}, "
        footer += f"{Fore.GREEN}Files: {self.file_count}{Style.RESET_ALL}"
        if self.full:
            footer += f"{Fore.RED}\nOutput limited to 200 elements.{Style.RESET_ALL}"
        return header + body + footer

    def save_xml(self, file_path: Path) -> None:
        def build_xml_element(node: TreeNode) -> ET.Element:
            is_folder = node.state.is_dir()
            name = f"{node.state.name}/" if is_folder else node.state.name
            # Создаём элемент для текущего узла
            element = ET.Element("node", attrib={"name": name})

            # Рекурсивно добавляем детей
            for child in node.children:
                child_element = build_xml_element(child)
                element.append(child_element)

            return element

        tree = ET.ElementTree(build_xml_element(self.root))

        raw_string = ET.tostring(tree.getroot(), encoding="unicode")
        parsed = minidom.parseString(raw_string)
        formated_xml = parsed.toprettyxml(indent="  ")

        with file_path.open("w", encoding="utf-8") as f:
            f.write(formated_xml)


def main(command_line: list[str] | None = None) -> None:
    """
    Главная функция программы.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", action="store_true", help="All files are printed.")
    parser.add_argument("-d", action="store_true", help="Print directories only.")
    parser.add_argument("-f", action="store_true", help="Print relative path.")
    parser.add_argument(
        "-m",
        "--max_depth",
        type=int,
        default=None,
        help="Max depth of directories.",
    )
    parser.add_argument(
        "-i",
        action="store_true",
        help="Tree does not print the indentation lines."
        " Useful when used in conjunction with the -f option.",
    )
    parser.add_argument("directory", nargs="?", default=".", help="Directory to scan.")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output the tree to the specified file in XML format.",
    )
    args = parser.parse_args(command_line)

    try:
        directory = Path(args.directory).resolve(strict=True)
    except FileNotFoundError:
        print(f"Directory '{Path(args.directory).resolve()}' does not exist.")
        sys.exit(1)

    tree = Tree(directory, args)
    if args.output:
        out_file = Path("XML") / args.output
        tree.save_xml(out_file)
    else:
        print(tree)


if __name__ == "__main__":
    main()
