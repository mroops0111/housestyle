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
from ..domain.position import SourceRange
from .languages import LanguageProfile


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
            self._line_block(profile, document, group)
            for group in self._group_lines(profile, document, captures['comment'])
        )
        return tuple(sorted(blocks, key=lambda block: block.range.start))

    def _capture(self, profile: LanguageProfile, language_id: str, root: Node) -> dict[str, list[Node]]:
        query = Query(get_language(language_id), profile.query())  # pyright: ignore[reportArgumentType]
        raw = QueryCursor(query).captures(root)
        found: dict[str, list[Node]] = {'comment': [], 'docstring': []}
        for name, nodes in raw.items():
            found.setdefault(name, []).extend(nodes)
        for name, nodes in found.items():
            seen: set[int] = set()
            unique = [node for node in nodes if not (node.start_byte in seen or seen.add(node.start_byte))]
            found[name] = sorted(unique, key=lambda node: node.start_byte)
        return found

    def _group_lines(self, profile: LanguageProfile, document: Document, nodes: list[Node]) -> list[list[Node]]:
        groups: list[list[Node]] = []
        for node in nodes:
            if groups and self._continues(profile, document, groups[-1][-1], node):
                groups[-1].append(node)
            else:
                groups.append([node])
        return groups

    def _continues(self, profile: LanguageProfile, document: Document, previous: Node, node: Node) -> bool:
        if previous.start_point[0] != node.start_point[0] - 1:
            return False
        if self._is_trailing(document, previous) or self._is_trailing(document, node):
            return False
        return previous.start_point[1] == node.start_point[1]

    def _is_trailing(self, document: Document, node: Node) -> bool:
        line = document.positions.line_text(node.start_point[0])
        return bool(line[: node.start_point[1]].strip())

    def _line_block(self, profile: LanguageProfile, document: Document, nodes: list[Node]) -> CommentBlock:
        lines = tuple(self._line(profile, document, node, CommentForm.LINE) for node in nodes)
        return CommentBlock(
            range=SourceRange(lines[0].range.start, lines[-1].range.end),
            lines=lines,
            form=CommentForm.LINE,
            placement=self._placement(profile, document, nodes[-1], is_doc=False),
            attachment=self._attachment(profile, nodes[-1], is_doc=False),
        )

    def _doc_block(self, profile: LanguageProfile, document: Document, node: Node) -> CommentBlock:
        lines: list[CommentLine] = []
        for row in range(node.start_point[0], node.end_point[0] + 1):
            split = profile.split_marker(document.positions.line_text(row), CommentForm.DOC)
            lines.append(
                CommentLine(
                    range=document.positions.line_range(row),
                    indent=split.indent,
                    marker=split.marker,
                    payload=split.payload,
                    suffix=split.suffix,
                )
            )
        return CommentBlock(
            range=SourceRange(lines[0].range.start, lines[-1].range.end),
            lines=tuple(lines),
            form=CommentForm.DOC,
            placement=self._placement(profile, document, node, is_doc=True),
            attachment=self._attachment(profile, node, is_doc=True),
        )

    def _line(self, profile: LanguageProfile, document: Document, node: Node, form: CommentForm) -> CommentLine:
        row, column = node.start_point
        text = document.positions.line_text(row)
        split = profile.split_marker(text[column:], form)
        return CommentLine(
            range=document.positions.line_range(row),
            indent=text[:column] + split.indent,
            marker=split.marker,
            payload=split.payload,
            suffix=split.suffix,
        )

    def _placement(
        self,
        profile: LanguageProfile,
        document: Document,
        node: Node,
        *,
        is_doc: bool,
    ) -> CommentPlacement:
        if is_doc:
            owner = self._owning_definition(profile, node)
            return CommentPlacement.FILE_HEADER if owner is None else CommentPlacement.LEADING_DECLARATION
        if self._is_trailing(document, node):
            return CommentPlacement.TRAILING
        if self._next_definition(profile, node) is not None:
            return CommentPlacement.LEADING_DECLARATION
        parent = node.parent
        if parent is not None and parent.type in profile.root_nodes and not self._has_code_before(profile, node):
            return CommentPlacement.FILE_HEADER
        return CommentPlacement.INLINE_BODY

    def _has_code_before(self, profile: LanguageProfile, node: Node) -> bool:
        parent = node.parent
        if parent is None:
            return False
        return any(
            sibling.start_byte < node.start_byte and sibling.type != profile.comment_node
            for sibling in parent.named_children
        )

    def _next_definition(self, profile: LanguageProfile, node: Node) -> Node | None:
        candidate = node.next_named_sibling
        while candidate is not None:
            if candidate.type in profile.definition_nodes:
                return candidate
            if candidate.type != profile.comment_node:
                return None
            candidate = candidate.next_named_sibling
        return None

    def _owning_definition(self, profile: LanguageProfile, node: Node) -> Node | None:
        cursor = node.parent
        while cursor is not None:
            if cursor.type in profile.definition_nodes:
                return cursor
            if cursor.type in profile.root_nodes:
                return None
            cursor = cursor.parent
        return None

    def _attachment(self, profile: LanguageProfile, node: Node, *, is_doc: bool) -> SymbolRef | None:
        target = self._owning_definition(profile, node) if is_doc else self._next_definition(profile, node)
        if target is None:
            return None
        named = target.child_by_field_name('name')
        if named is None or named.text is None:
            return None
        name = named.text.decode('utf-8')
        return SymbolRef(
            name=name,
            kind=profile.symbol_kind(target.type),
            visibility=profile.visibility_of(name),
        )
