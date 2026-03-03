"""
Project metadata for the :mod:`pyfcstm` package.

This module defines immutable, public metadata constants used throughout the
project and by packaging tools such as ``setup.py``. These values provide the
project title, version, description, and author contact information.

The module exposes the following public attributes:

* :data:`__TITLE__` - Project name
* :data:`__VERSION__` - Current project version
* :data:`__DESCRIPTION__` - Short project description
* :data:`__AUTHOR__` - Author name
* :data:`__AUTHOR_EMAIL__` - Author contact email

Example::

    >>> from pyfcstm.config import meta
    >>> meta.__TITLE__
    'pyfcstm'
    >>> meta.__VERSION__
    '0.2.1'

.. note::
   These values are intended to be constants and should not be modified at
   runtime. They are consumed by packaging and documentation tools.

"""

#: Title of this project (should be `pyfcstm`).
__TITLE__: str = 'pyfcstm'

#: Version of this project.
__VERSION__: str = '0.2.1'

#: Short description of the project, will be included in ``setup.py``.
__DESCRIPTION__: str = (
    'A Python framework for parsing finite state machine DSL and '
    'generating executable code in multiple target languages.'
)

#: Author of this project.
__AUTHOR__: str = 'HansBug'

#: Email of the authors'.
__AUTHOR_EMAIL__: str = 'hansbug@buaa.edu.cn'
