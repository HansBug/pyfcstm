import sys

from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.model import load_state_machine_from_text

CASES = [
    ("history written on an owner", "state Root { [*] -> P; state P { [H] -> A; region R { [*] -> A; state A; } } }"),
    ("child states mixed with a region", "state Root { [*] -> P; state P { state X; region R { [*] -> A; state A; } } }"),
    ("enter block inside a region", "state Root { [*] -> P; state P { region R { enter { } [*] -> A; state A; } } }"),
    ("a variable declared in a region", "state Root { [*] -> P; state P { region R { def int x = 0; [*] -> A; state A; } } }"),
]

failed = 0
for title, text in CASES:
    print("==", title)
    try:
        load_state_machine_from_text(text)
    except GrammarParseError as error:
        failed += 1
        print("GrammarParseError:", str(error).splitlines()[0])
        print("GrammarParseError:", str(error).splitlines()[1])
    else:
        print("accepted")
sys.exit(1 if failed else 0)
