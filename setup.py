import os
import re
from codecs import open
from distutils.core import setup

from setuptools import find_packages

_MODULE_NAME = "pyfcstm"
_PACKAGE_NAME = 'pyfcstm'

here = os.path.abspath(os.path.dirname(__file__))
meta = {}
with open(os.path.join(here, _MODULE_NAME, 'config', 'meta.py'), 'r', 'utf-8') as f:
    exec(f.read(), meta)


def _load_req(file: str):
    with open(file, 'r', 'utf-8') as f:
        return [line.strip() for line in f.readlines() if line.strip()]


requirements = _load_req('requirements.txt')

_REQ_PATTERN = re.compile(r'^requirements-(\w+)\.txt$')
_REQ_BLACKLIST = {'zoo'}
group_requirements = {
    item.group(1): _load_req(item.group(0))
    for item in [_REQ_PATTERN.fullmatch(reqpath) for reqpath in os.listdir()] if item
    if item.group(1) not in _REQ_BLACKLIST
}

with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setup(
    # information
    name=_PACKAGE_NAME,
    version=meta['__VERSION__'],
    packages=find_packages(include=(_MODULE_NAME, "%s.*" % _MODULE_NAME)),
    package_data={
        package_name: ['*.yaml', '*.yml', '*.json', '*.png', '*.g4', '*.tokens', '*.interp']
        for package_name in find_packages(include=('*'))
    },
    description=meta['__DESCRIPTION__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    author=meta['__AUTHOR__'],
    author_email=meta['__AUTHOR_EMAIL__'],
    license='GNU Lesser General Public License v3 (LGPLv3)',
    keywords='state-machine, code-generation, compiler, template-engine, modelling',
    url='https://github.com/hansbug/pyfcstm',

    # environment
    python_requires=">=3.7",
    install_requires=requirements,
    tests_require=group_requirements['test'],
    extras_require=group_requirements,
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        # Intended Audience
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Manufacturing',
        'Intended Audience :: System Administrators',

        # License
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',

        # Programming Language
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',

        # Operating System
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',

        # Technical Topics
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Compilers',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Software Development :: Pre-processors',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Text Processing',
        'Topic :: Text Processing :: Linguistic',
        'Topic :: Text Processing :: Markup',
        'Topic :: System :: Systems Administration',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities',
        'Topic :: Documentation',

        # Data Processing Features
        'Typing :: Typed',
        'Natural Language :: English'
    ],
    entry_points={
        'console_scripts': [
            'pyfcstm=pyfcstm.entry:pyfcstmcli'
        ]
    },
    project_urls={
        'Homepage': 'https://github.com/hansbug/pyfcstm',
        'Documentation': 'https://hansbug.github.io/pyfcstm/',
        'Source': 'https://github.com/hansbug/pyfcstm',
        'Download': 'https://pypi.org/project/pyfcstm/#files',
        'Bug Reports': 'https://github.com/hansbug/pyfcstm/issues',
        # 'Changelog': 'https://github.com/hansbug/pyfcstm/blob/main/CHANGELOG.md',
        'Contributing': 'https://github.com/hansbug/pyfcstm/blob/main/CONTRIBUTING.md',
        'Pull Requests': 'https://github.com/hansbug/pyfcstm/pulls',
        'CI': 'https://github.com/hansbug/pyfcstm/actions',
        'Coverage': 'https://codecov.io/gh/hansbug/pyfcstm',
        'Wiki': 'https://github.com/hansbug/pyfcstm/wiki',
        'License': 'https://github.com/hansbug/pyfcstm/blob/main/LICENSE',
    },
)
