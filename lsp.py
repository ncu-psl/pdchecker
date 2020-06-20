from pygls.features import TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_SAVE, TEXT_DOCUMENT_DID_CHANGE
from pygls import features
from pygls.server import LanguageServer
from pygls.types import Range, Position, Diagnostic, SignatureHelp, SignatureInformation, Hover

from checker import check
import logging

server = LanguageServer()
logging.basicConfig(level=logging.DEBUG)


class Checker:

    def validate(self, source):
        self.itpr = check(source)
        diagnostics = []
        logging.debug(f'itpr errors: {self.itpr.errors}')
        for item in self.itpr.errors:
            l1 = item['lineno'] - 1
            c1 = item['col_offset']
            l2 = item['end_lineno'] - 1
            c2 = item['end_col_offset']
            msg = item['error'].message
            diagnostics.append(Diagnostic(
                range=Range(Position(l1, c1), Position(l2, c2)),
                message=msg,
                source="PDChecker"))
        return diagnostics

    def help(self, pos):
        def inside(node):
            if not hasattr(node, 'lineno') or not hasattr(node, 'col_offset'):
                return False
            row_matched = pos.line >= (node.lineno-1)
            if hasattr(node, 'end_lineno'):
                row_matched = (node.end_lineno-1) >= pos.line and row_matched
            col_matched = pos.character >= node.col_offset
            if hasattr(node, 'end_col_offset'):
                col_matched = (node.end_col_offset) >= pos.character and col_matched
            return row_matched and col_matched
        candidates = [(n, t) for n, t in self.itpr.srcmap.items() if inside(n)]
        return candidates


checker = Checker()


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def handle_feature(ls, params):
    text_doc = ls.workspace.get_document(params.textDocument.uri)
    diagnostics = checker.validate(text_doc.source)
    logging.debug(f'sending diagnostics: {diagnostics!r}')
    ls.publish_diagnostics(params.textDocument.uri, diagnostics)


@server.feature(features.SIGNATURE_HELP)
async def handle_sighelp(ls: LanguageServer, params):
    text_doc = ls.workspace.get_document(params.textDocument.uri)
    pos = params.position
    candidates = checker.help(pos)
    return SignatureHelp(signatures=[SignatureInformation(f'{t!r}') for t in candidates])

@server.feature(features.HOVER)
async def handle_hover(ls, params):
    text_doc = ls.workspace.get_document(params.textDocument.uri)
    pos = params.position
    return Hover(contents=repr(checker.help(pos)[0][1]))


server.start_tcp('localhost', 8080)
