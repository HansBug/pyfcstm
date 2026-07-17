import os
import re
import sys

from setuptools import find_packages, setup

_MODULE_NAME = "pyfcstm"
_PACKAGE_NAME = "pyfcstm"

here = os.path.abspath(os.path.dirname(__file__))
meta = {}
with open(
    os.path.join(here, _MODULE_NAME, "config", "meta.py"), "r", encoding="utf-8"
) as f:
    exec(f.read(), meta)


def _load_req(file: str):
    with open(file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


requirements = _load_req("requirements.txt")

_REQ_PATTERN = re.compile(r"^requirements-(\w+)\.txt$")
_REQ_BLACKLIST = {"zoo"}
group_requirements = {
    item.group(1): _load_req(item.group(0))
    for item in [_REQ_PATTERN.fullmatch(reqpath) for reqpath in os.listdir()]
    if item
    if item.group(1) not in _REQ_BLACKLIST
}

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

templates_source_dir = os.path.join(here, "templates")
packaged_template_dir = os.path.join(here, _MODULE_NAME, "template")
if os.path.isdir(templates_source_dir):
    from tools.package_templates import package_templates

    package_templates(
        templates_source_dir,
        packaged_template_dir,
        verbose=os.environ.get("PYFCSTM_SETUP_TPL_VERBOSE") == "1",
    )

package_data = {
    package_name: [
        "*.yaml",
        "*.yml",
        "*.json",
        "*.png",
        "*.zip",
        "*.g4",
        "*.tokens",
        "*.interp",
    ]
    for package_name in find_packages(include=("*"))
}
package_data.setdefault("pyfcstm.llm", []).extend(["*.md", "*.sha256"])
package_data.setdefault("pyfcstm.assets", []).extend(
    [
        "*.js",
        "*.wasm",
        "*.json",
        "*.txt",
        "fonts/*.ttf",
        "fonts/*.ttc",
    ]
)


def _require_diagram_assets_for_distribution() -> None:
    """Fail closed when a distribution build would omit diagram resources."""
    distribution_commands = {
        "build",
        "build_py",
        "sdist",
        "bdist",
        "bdist_wheel",
        "install",
    }
    if not distribution_commands.intersection(sys.argv[1:]):
        return
    required_assets = [
        os.path.join(here, _MODULE_NAME, "assets", "renderer.js"),
        os.path.join(here, _MODULE_NAME, "assets", "resvg.wasm"),
        os.path.join(here, _MODULE_NAME, "assets", "manifest.json"),
        os.path.join(
            here,
            _MODULE_NAME,
            "assets",
            "fonts",
            "JetBrainsMono-Regular.ttf",
        ),
    ]
    missing = [path for path in required_assets if not os.path.isfile(path)]
    if missing:
        raise RuntimeError(
            "diagram distribution assets are missing; run `make build_assets` "
            "before building a wheel or sdist: %s" % ", ".join(missing)
        )


_require_diagram_assets_for_distribution()

setup(
    # information
    name=_PACKAGE_NAME,
    version=meta["__VERSION__"],
    packages=find_packages(include=(_MODULE_NAME, "%s.*" % _MODULE_NAME)),
    package_data=package_data,
    description=meta["__DESCRIPTION__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    author=meta["__AUTHOR__"],
    author_email=meta["__AUTHOR_EMAIL__"],
    license="GNU Lesser General Public License v3 (LGPLv3)",
    keywords="state-machine, code-generation, compiler, template-engine, modelling",
    url="https://github.com/hansbug/pyfcstm",
    # environment
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require=group_requirements,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        # Intended Audience
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: System Administrators",
        # License
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        # Programming Language
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        # Operating System
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        # Technical Topics
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Compilers",
        "Topic :: Software Development :: Interpreters",
        "Topic :: Software Development :: Pre-processors",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Text Processing",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Text Processing :: Markup",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
        "Topic :: Documentation",
        # Data Processing Features
        "Typing :: Typed",
        "Natural Language :: English",
    ],
    entry_points={
        "console_scripts": ["pyfcstm=pyfcstm.__main__:main"],
        "pygments.lexers": [
            "fcstm = pyfcstm.highlight.pygments_lexer:FcstmLexer",
            "fbmcq = pyfcstm.highlight.bmc_query_lexer:FcstmBmcQueryLexer",
        ],
    },
    project_urls={
        "Homepage": "https://github.com/hansbug/pyfcstm",
        "Documentation": "https://pyfcstm.readthedocs.io/",
        "Source": "https://github.com/hansbug/pyfcstm",
        "Download": "https://pypi.org/project/pyfcstm/#files",
        "Bug Reports": "https://github.com/hansbug/pyfcstm/issues",
        # 'Changelog': 'https://github.com/hansbug/pyfcstm/blob/main/CHANGELOG.md',
        "Contributing": "https://github.com/hansbug/pyfcstm/blob/main/CONTRIBUTING.md",
        "Pull Requests": "https://github.com/hansbug/pyfcstm/pulls",
        "CI": "https://github.com/hansbug/pyfcstm/actions",
        "Coverage": "https://codecov.io/gh/hansbug/pyfcstm",
        "Wiki": "https://github.com/hansbug/pyfcstm/wiki",
        "License": "https://github.com/hansbug/pyfcstm/blob/main/LICENSE",
    },
)
