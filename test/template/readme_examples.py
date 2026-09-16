"""Locate runnable examples in generated guides independently of translated headings."""

import re


def example_code(markdown, name):
    marker = '<!-- example:%s -->' % name
    assert markdown.count(marker) == 1, 'Expected one example: %s' % name
    text = markdown.split(marker, 1)[1]
    match = re.search(r'```(?:python|c|cpp)\n(.*?)\n```', text, re.S)
    assert match is not None, 'Missing code for example: %s' % name
    return match.group(1)


def extend_native_main(source, fragment):
    position = source.rindex('    return 0;')
    return source[:position] + fragment + '\n' + source[position:]
