"""Load every region_bad_*.fcstm.txt file and print what the loader reports."""
import glob

from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.utils.validate import ModelValidationError

for path in sorted(glob.glob('region_bad_*.fcstm.txt')):
    with open(path) as stream:
        text = stream.read()
    print('== %s' % path[len('region_bad_'):-len('.fcstm.txt')])
    print(text.rstrip())
    try:
        load_state_machine_from_text(text)
    except GrammarParseError as error:
        lines = str(error).splitlines()
        print('-> syntax error (GrammarParseError): %s' % ' | '.join(lines[:2]))
    except ModelValidationError as error:
        for item in error.diagnostics:
            reason = item.refs.get('reason')
            print('-> %s%s: %s' % (item.code, ' (reason=%s)' % reason if reason else '',
                                   ' '.join(item.message.split())))
    else:
        print('-> accepted')
    print()
