import typing

from ...domain.comment import CommentForm, CommentGroup, CommentPlacement
from ...domain.diagnostic import Diagnostic, Fix, FixKind, RuleMeta
from ...domain.rules import RuleContext
from ..languages.base import LanguageConventions


NO_FILE_HEADER = RuleMeta(
    rule_id='no-file-header',
    summary='A file must not open with a banner comment before its first declaration.',
    fix_kind=FixKind.REWRITE,
)

DOC_COMMENT_FORM = RuleMeta(
    rule_id='doc-comment-form',
    summary='A public symbol must be documented in the doc comment form its language renders.',
    fix_kind=FixKind.REWRITE,
)

NO_SIGNATURE_RESTATING = RuleMeta(
    rule_id='no-signature-restating',
    summary='A doc comment must not restate what the type signature already carries.',
    fix_kind=FixKind.REWRITE,
)


class NoFileHeaderRule:
    meta = NO_FILE_HEADER

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        if block.placement is not CommentPlacement.FILE_HEADER:
            return
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                'This comment opens the file before any declaration. '
                'A reader has the file, not a banner about it, so delete it. '
                'If it states a constraint, move that to the declaration the constraint applies to.'
            ),
            fix=Fix.rewrite(),
        )


class DocCommentFormRule:
    def __init__(self, conventions: LanguageConventions) -> None:
        self._conventions = conventions
        self.meta = DOC_COMMENT_FORM

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        if not block.attaches_to_public_symbol or block.form is CommentForm.DOC:
            return
        if block.placement is not CommentPlacement.LEADING_DECLARATION:
            return
        delimiter = self._conventions.doc_delimiter
        name = block.attachment.name if block.attachment else 'the symbol'
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                f'{name} is public but documented with a plain comment. '
                f'Move the text into a {delimiter} doc comment so tooling renders it on hover.'
            ),
            fix=Fix.rewrite(),
        )


class NoSignatureRestatingRule:
    def __init__(self, conventions: LanguageConventions) -> None:
        self._conventions = conventions
        self.meta = NO_SIGNATURE_RESTATING

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        if block.form is not CommentForm.DOC:
            return
        for line in block.lines:
            tag = self._tag(line.text)
            if tag is None:
                continue
            yield Diagnostic(
                rule_id=self.meta.rule_id,
                range=block.range,
                message=(
                    f'The tag "{tag}" restates the signature, which the annotations already carry. '
                    'Delete the tag and its block. '
                    'If a parameter needs explaining, say why it matters in prose instead.'
                ),
                fix=Fix.rewrite(),
            )
            return

    def _tag(self, text: str) -> str | None:
        stripped_text = text.strip()
        for tag in self._conventions.signature_tags:
            if stripped_text.startswith(tag):
                return tag
        return None


BLOCK_TOO_LONG = RuleMeta(
    rule_id='block-too-long',
    summary='A comment block long enough to restate the code has stopped earning its place.',
    fix_kind=FixKind.REWRITE,
)

DEFAULT_LIMITS = {
    'line': 4,
    'doc-internal': 13,
    'doc-public': 17,
}


class BlockTooLongRule:
    meta = BLOCK_TOO_LONG

    def check(self, block: CommentGroup, context: RuleContext) -> typing.Iterable[Diagnostic]:
        group = self._group(block)
        limit = context.settings(self.meta.rule_id).integer(group, DEFAULT_LIMITS[group])
        if block.line_count <= limit:
            return
        yield Diagnostic(
            rule_id=self.meta.rule_id,
            range=block.range,
            message=(
                f'This comment runs to {block.line_count} lines against a {limit} line limit for {group} '
                'comments. A comment earns its place by stating one constraint the code cannot show. '
                'Cut it to that constraint, or move the explanation into a name.'
            ),
            fix=Fix.rewrite(),
        )

    def _group(self, block: CommentGroup) -> str:
        if block.form is not CommentForm.DOC:
            return 'line'
        return 'doc-public' if block.attaches_to_public_symbol else 'doc-internal'
