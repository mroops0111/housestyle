from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language, get_parser

from ..domain.comment import (
    CommentBlock,
    CommentForm,
    CommentLine,
    CommentPlacement,
    SymbolRef,
)
from ..domain.document import Document
from ..domain.ports import LanguageProfile
from ..domain.position import SourceRange


_DEFINITION_TYPES = frozenset({'function_definition', 'class_definition', 'decorated_definition'})


class TreeSitterParser:
    def __init__(self, profiles: tuple[LanguageProfile, ...]) -> None:
        self._profiles = {profile.language_id: profile for profile in profiles}

    def supports(self, language_id: str) -> bool:
        return language_id in self._profiles

    def parse(self, document: Document) -> tuple[CommentBlock, ...]:
        profile = self._profiles.get(document.language_id)
        if profile is None:
            return ()
        data = document.text.encode('utf-8')
        tree = get_parser(document.language_id).parse(data)  # pyright: ignore[reportArgumentType]
        captures = self._capture(profile, document.language_id, tree.root_node)
        blocks = [self._doc_block(profile, document, node) for node in captures['docstring']]
        blocks.extend(
            self._line_block(profile, document, group) for group in self._group_lines(document, captures['comment'])
        )
        return tuple(sorted(blocks, key=lambda block: block.range.start))

    def _capture(self, profile: LanguageProfile, language_id: str, root: Node) -> dict[str, list[Node]]:
        query = Query(get_language(language_id), profile.query())  # pyright: ignore[reportArgumentType]
        raw = QueryCursor(query).captures(root)
        found: dict[str, list[Node]] = {'comment': [], 'docstring': []}
        for name, nodes in raw.items():
            found.setdefault(name, []).extend(nodes)
        seen: set[int] = set()
        for name in found:
            unique = [node for node in found[name] if not (node.start_byte in seen or seen.add(node.start_byte))]
            found[name] = sorted(unique, key=lambda node: node.start_byte)
        return found

    def _group_lines(self, document: Document, nodes: list[Node]) -> list[list[Node]]:
        groups: list[list[Node]] = []
        for node in nodes:
            row = node.start_point[0]
            if groups and self._continues(document, groups[-1][-1], node, row):
                groups[-1].append(node)
            else:
                groups.append([node])
        return groups

    def _continues(self, document: Document, previous: Node, node: Node, row: int) -> bool:
        if previous.start_point[0] != row - 1:
            return False
        if self._is_trailing(document, previous) or self._is_trailing(document, node):
            return False
        return previous.start_point[1] == node.start_point[1]

    def _is_trailing(self, document: Document, node: Node) -> bool:
        line = document.positions.line_text(node.start_point[0])
        return bool(line[: node.start_point[1]].strip())

    def _line_block(self, profile: LanguageProfile, document: Document, nodes: list[Node]) -> CommentBlock:
        lines = tuple(self._line(profile, document, node, CommentForm.LINE) for node in nodes)
        placement = self._placement(document, nodes[-1], is_doc=False)
        return CommentBlock(
            range=SourceRange(lines[0].range.start, lines[-1].range.end),
            lines=lines,
            form=CommentForm.LINE,
            placement=placement,
            attachment=self._attachment(profile, nodes[-1], is_doc=False),
        )

    def _doc_block(self, profile: LanguageProfile, document: Document, node: Node) -> CommentBlock:
        first_row, last_row = node.start_point[0], node.end_point[0]
        lines: list[CommentLine] = []
        for row in range(first_row, last_row + 1):
            text = document.positions.line_text(row)
            span = document.positions.line_range(row)
            indent, marker, payload, suffix = profile.split_marker(text, CommentForm.DOC)
            lines.append(CommentLine(range=span, indent=indent, marker=marker, payload=payload, suffix=suffix))
        return CommentBlock(
            range=SourceRange(lines[0].range.start, lines[-1].range.end),
            lines=tuple(lines),
            form=CommentForm.DOC,
            placement=self._placement(document, node, is_doc=True),
            attachment=self._attachment(profile, node, is_doc=True),
        )

    def _line(self, profile: LanguageProfile, document: Document, node: Node, form: CommentForm) -> CommentLine:
        row, column = node.start_point
        text = document.positions.line_text(row)
        prefix = text[:column]
        indent, marker, payload, suffix = profile.split_marker(text[column:], form)
        return CommentLine(
            range=document.positions.line_range(row),
            indent=prefix + indent,
            marker=marker,
            payload=payload,
            suffix=suffix,
        )

    def _placement(self, document: Document, node: Node, *, is_doc: bool) -> CommentPlacement:
        if is_doc:
            owner = self._owning_definition(node)
            return CommentPlacement.FILE_HEADER if owner is None else CommentPlacement.LEADING_DECLARATION
        if self._is_trailing(document, node):
            return CommentPlacement.TRAILING
        if self._next_definition(node) is not None:
            return CommentPlacement.LEADING_DECLARATION
        if node.parent is not None and node.parent.type == 'module' and not self._has_code_before(node):
            return CommentPlacement.FILE_HEADER
        return CommentPlacement.INLINE_BODY

    def _has_code_before(self, node: Node) -> bool:
        parent = node.parent
        if parent is None:
            return False
        return any(
            sibling.start_byte < node.start_byte and sibling.type != 'comment' for sibling in parent.named_children
        )

    def _next_definition(self, node: Node) -> Node | None:
        candidate = node.next_named_sibling
        while candidate is not None:
            if candidate.type in _DEFINITION_TYPES:
                return candidate
            if candidate.type != 'comment':
                return None
            candidate = candidate.next_named_sibling
        return None

    def _owning_definition(self, node: Node) -> Node | None:
        cursor = node.parent
        while cursor is not None:
            if cursor.type in _DEFINITION_TYPES:
                return cursor
            if cursor.type == 'module':
                return None
            cursor = cursor.parent
        return None

    def _attachment(self, profile: LanguageProfile, node: Node, *, is_doc: bool) -> SymbolRef | None:
        target = self._owning_definition(node) if is_doc else self._next_definition(node)
        if target is None:
            return None
        named = target.child_by_field_name('name')
        if named is None or named.text is None:
            return None
        name = named.text.decode('utf-8')
        kind = 'class' if target.type == 'class_definition' else 'function'
        return SymbolRef(name=name, kind=kind, visibility=profile.visibility_of(name))
