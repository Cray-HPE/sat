# SAT Python Dependencies

SAT specifies its Python production and development dependencies using
requirements files.

A production dependency is a Python dependency needed when running SAT. An
example of a production dependency is ``requests``, the library that SAT uses
to issue HTTP requests to interact with the Shasta API. Most SAT dependencies
are production dependencies. These are specified in ``requirements.txt``, and
only top-level dependencies are specified.

By contrast, development dependencies are Python dependencies that are only
needed when installing SAT in a development or build environment. An example
of a development dependency is ``nose``, the utility used to discover and
run SAT unit tests. These are specified in ``requirements-dev.txt``, and only
top-level dependencies are specified.

When installing into the SAT docker container or automated unit test pipeline,
SAT uses requirements files that specify exact versions of these Python
dependencies, including sub-dependencies. The names of these files end with
``.lock.txt``, e.g. ``requirements.lock.txt`` and ``requirements-dev.lock.txt``.
These "locked" requirements files are not meant to be modified by hand, but
rather generated from the output of ``pip freeze``.

Finally, since a typical development environment would contain both production
and development dependencies, the ``requirements-dev.lock.txt`` file contains
both the production and development dependencies and is therefore a superset
of ``requirements.lock.txt``.

This document contains instructions for modifying the Python dependencies to
keep all these files synchronized.

## Adding a production dependency

Create and activate a new Python virtual environment:

    user@local-mbp sat $ python3 -m venv ./sat-venv
    user@local-mbp sat $ source sat-venv/bin/activate

Install the locked production requirements in the virtual environment:

    (sat-venv) user@local-mbp sat $ pip install -r requirements.lock.txt

Install the new requirement(s) with ``pip install PACKAGE``:

    (sat-venv) user@local-mbp sat $ pip install PACKAGE

Add the package(s) to ``requirements.txt``. You should not specify a specific
version. At most, specify a minimum version of the current version and a
maximum version of the next major version. Either of the following is
acceptable:

    (sat-venv) user@local-mbp sat $ vim requirements.txt
    ...
    PACKAGE
    ...

    (sat-venv) user@local-mbp sat $ vim requirements.txt
    ...
    PACKAGE >= 1.6.1, < 2.0
    ...

Run ``pip freeze`` and save the output to ``requirements.lock.txt``:

    (sat-venv) user@local-mbp sat $ pip freeze > requirements.lock.txt

Install the dev-only requirements with pip install -r requirements-dev.lock.txt.

    (sat-venv) user@local-mbp sat $ pip install -r requirements-dev.lock.txt

Run ``pip freeze`` again and save the output to ``requirements-dev.lock.txt``.

    (sat-venv) user@local-mbp sat $ pip freeze > requirements-dev.lock.txt

This process should have modified ``requirements.txt``, ``requirements.lock.txt`` and
``requirements-dev.lock.txt``, but not ``requirements-dev.txt``.

## Adding a development dependency

Create and activate a new Python virtual environment:

    user@local-mbp sat $ python3 -m venv ./sat-venv
    user@local-mbp sat $ source sat-venv/bin/activate

Install the locked development requirements in the virtual environment:

    (sat-venv) user@local-mbp sat $ pip install -r requirements-dev.lock.txt

Install the new requirement(s) with ``pip install DEV_PACKAGE``:

    (sat-venv) user@local-mbp sat $ pip install DEV_PACKAGE

Add the package(s) to ``requirements-dev.txt``. You should not specify a specific
version. At most, specify a minimum version of the current version and a
maximum version of the next major version. Either of the following is
acceptable:

    (sat-venv) user@local-mbp sat $ vim requirements-dev.txt
    ...
    DEV_PACKAGE
    ...

    (sat-venv) user@local-mbp sat $ vim requirements-dev.txt
    ...
    DEV_PACKAGE >= 1.6.1, < 2.0
    ...

Run ``pip freeze`` and save the output to ``requirements-dev.lock.txt``.

    (sat-venv) user@local-mbp sat $ pip freeze > requirements-dev.lock.txt

This process should have modified ``requirements-dev.txt`` and
``requirements-dev.lock.txt``, but not ``requirements.txt`` or
``requirements.lock.txt``.

## Removing a production dependency

Create and activate a new Python virtual environment:

    user@local-mbp sat $ python3 -m venv ./sat-venv
    user@local-mbp sat $ source sat-venv/bin/activate

Remove the dependency from `requirements.txt`.

Install the base requirements using the locked requirements file as a
constraints file:

    (sat-venv) user@local-mbp sat $ pip install -r requirements.txt -c requirements.lock.txt

Run `pip freeze` and save the output to `requirements.lock.txt`:

    (sat-venv) user@local-mbp sat $ pip freeze > requirements.lock.txt

Install the dev-only requirements using the locked dev requirements file as a
constraints file:

    (sat-venv) user@local-mbp sat $ pip install -r requirements-dev.txt -c requirements-dev.lock.txt

Run `pip freeze` again and save the output to `requirements-dev.lock.txt`.

    (sat-venv) user@local-mbp sat $ pip freeze > requirements-dev.lock.txt

This process should have modified `requirements.txt`, `requirements.lock.txt` and
`requirements-dev.lock.txt`, but not `requirements-dev.txt`.

## Re-generating the locked requirements files

You may want to re-generate the locked requirements files to pull in newer
versions of the various dependencies. This may be needed to address security
issues.

Create and activate a new Python virtual environment:

    user@local-mbp sat $ python3 -m venv ./sat-venv
    user@local-mbp sat $ source sat-venv/bin/activate

Install the non-locked python requirements in the virtual environment:

    (sat-venv) user@local-mbp sat $ pip install -r requirements.txt

Re-generate the locked production requirements file:

    (sat-venv) user@local-mbp sat $ pip freeze > requirements.lock.txt

Install the non-locked development dependencies:

    (sat-venv) user@local-mbp sat $ pip install -r requirements-dev.txt

Re-generate the locked development requirements file:

    (sat-venv) user@local-mbp sat $ pip freeze > requirements-dev.lock.txt

Run SAT unit tests to ensure that SAT is functional with the new requirements:

    (sat-venv) user@local-mbp sat $ nosetests
