from pygls.features import TEXT_DOCUMENT_DID_OPEN, TEXT_DOCUMENT_DID_SAVE, TEXT_DOCUMENT_DID_CHANGE
from pygls.server import LanguageServer
from pygls.types import Range, Position, Diagnostic

from checker4 import check
import logging

server = LanguageServer()
logging.basicConfig(filename='pygls.log', filemode='w', level=logging.DEBUG)


def validate(source):
    logging.debug(f'source: {source}')
    itpr = check(source)
    diagnostics = []
    logging.debug(f'itpr: {itpr.errors}')
    for item in itpr.errors:
        l1 = item['lineno'] - 1
        c1 = item['col_offset']
        l2 = item['end_lineno'] - 1
        c2 = item['end_col_offset']
        msg = item['error'].message
        # logging.debug(f'creating diagnostics: {(l, c, msg)!r}')
        diagnostics.append(Diagnostic(
            range=Range(Position(l1, c1), Position(l2, c2)),
            message=msg,
            source="PDChecker"))
    return diagnostics

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
@server.feature(TEXT_DOCUMENT_DID_OPEN)
@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def handle_feature(ls, params):
    text_doc = ls.workspace.get_document(params.textDocument.uri)
    diagnostics = validate(text_doc.source)
    logging.debug(f'sending diagnostics: {diagnostics!r}')
    ls.publish_diagnostics(params.textDocument.uri, diagnostics)



server.start_tcp('localhost', 8080)
# server.start_io()
