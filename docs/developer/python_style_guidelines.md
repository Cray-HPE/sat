# Python Style Guidelines

The ``sat`` Python project has minimal Python style guidelines, described
below.

## Conform to PEP8 with ``pycodestyle``

Use pycodestyle to catch styling errors with Python code, and use the
``pycodestyle.conf`` file at the root of this repository. For example, to run
against all the files in the ``sat`` and ``tests`` directory:

    (sat) user@local-mbp sat $ pycodestyle --config=./pycodestyle.conf sat tests

pycodestyle can be installed with ``pip3 install pycodestyle``.

## Line Length

Keep lines to a maximum length of 80 characters if you can keep it pretty, and
do not exceed a maximum of 120 characters per line. This is the limit set in
our ``pycodestyle.conf`` that will be enforced by that program.

## Docstrings

Use Google-style docstrings when writing Python docstrings, except use 4
spaces for indentation. A description for Google-style can be found at the
link below.

http://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

Further examples can be found in the documentation for Napoleon, a google-style
docstring plugin for Sphinx:

https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html
