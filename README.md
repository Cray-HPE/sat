# Introduction

The Shasta Admin Toolkit (SAT) is a project to create a set of command-line
interfaces that cover gaps in the Shasta product which were identified by Cray
service and support staff. Various RESTful APIs currently exist in shasta, but
they return large amounts of data in a JSON format which is hard for admins and
service personnel to parse. We would like to provide CLIs that are more friendly
for human consumption.

This repository contains the python code implementing this CLI or set of CLIs.

# Installation

This repository uses setuptools for installation in a `setup.py` script. We
intend to deliver SAT through an RPM, so `setup.py` will be called in the build
and install sections of the spec file.

For development purposes, this python package can be installed either by invoking
`setup.py` directly or by installing with `pip`. It is recommended to use `pip` as
it allows for easy uninstallation. The package can be installed with pip in
editable mode, which is preferable for development as you will be able to edit code
in its checkout directory and immediately see the effects of your changes.

To install use the following pip command:

```
pip install -e $CHECKOUT_DIR
```

Where `$CHECKOUT_DIR` is the directory where the SAT repo is checked out. I.e., if
running while your current directory is the top-level of the SAT repo, you can use:

```
pip install -e .
```

To uninstall, use the following command:

```
pip uninstall sat
```