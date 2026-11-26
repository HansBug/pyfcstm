"""Print the Pygments token types of the region and active() constructs."""
from pathlib import Path

from pyfcstm.highlight.pygments_lexer import FcstmLexer
from pygments.token import Token

lexer = FcstmLexer()
text = Path("region_highlight.fcstm").read_text()

wanted = ("region", "Motor", "Sensor", "active", "active_count", "state", "Root")
for line_no, line in enumerate(text.splitlines(), 1):
    for token_type, value in lexer.get_tokens(line):
        if value in wanted and token_type is not Token.Text:
            print("line %d: %-14r %s" % (line_no, value, token_type))
