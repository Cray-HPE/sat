# Introduction

The System Admin Toolkit (SAT) is a project to create a set of command-line
interfaces that cover gaps in the Shasta product which were identified by Cray
service and support staff. Various RESTful APIs currently exist in the system, but
they return large amounts of data in a JSON format which is hard for admins and
service personnel to parse. We would like to provide CLIs that are more friendly
for human consumption.

This repository contains the python code implementing this CLI or set of CLIs.

# Installation

There are a few different ways that this software can be installed. At the
lowest level, this software is python code that implements a `setup.py` script
that uses `setuptools`. This level of installation is useful for the developer
who would like to quickly install and test changes in a python virtual
environment on a system.

In the product as the customer will see it, SAT is delivered as an RPM package.
The spec file in this repository uses the `setup.py` script in its build and
install sections to build and install in the RPM buildroot and generate the RPM.

This repository also includes an Ansible role named `cray_sat`. This role is
responsible for installing and configuring the SAT software on a system
within the installation framework that is based on Ansible. This role is
packaged into a crayctldeploy subpackage of cray-sat. This package will be
installed automatically by the installer, named `crayctl`. The `crayctl`
command will then include the `cray_sat` role at an appropriate stage of the
installer, which will result in the installation and configuration of the SAT
software.

## Installation via pip

To install, use `pip3`:

```
pip3 install $CHECKOUT_DIR
```

Where `$CHECKOUT_DIR` is the directory where the SAT repo is checked out.

To uninstall, use the following command:

```
pip3 uninstall sat
```

# Contributing

If you would like to contribute to this project, please open a pull request.

Contributors must follow the guidelines below:

1. Include detailed commit messages that start with a short subject line,
   followed by a blank line, followed by a longer description that documents
   what the commit changes and why. See
   [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)
   for further helpful guidance.
2. Organize commits into cohesive, functional units, such that each commit
   fully implements an entire feature or bugfix, and the code works at each
   point in the commit history. I.e., don't include multiple commits where
   the first commit is a buggy implementation of a feature, and the following
   commits fix bugs that exist in the first commit. It is okay to develop in
   this way, but these commits must be squashed before opening the pull
   request.
3. Address feedback received in the pull request as additional commits. Then
   once approval is attained, squash bugfixes and feedback commits into the
   original commit(s) as appropriate per guideline #2 above. The reason for the
   separate commits addressing feedback is that it provides an easy way for
   reviewers to see only what changed if desired.
4. Update the ``CHANGELOG.md`` file with your changes. This project follows the
   conventions described by the [Keep a Changelog project](https://keepachangelog.com/en/1.0.0/).
   Add a description of changes to the ``[Unreleased]`` section of
   ``CHANGELOG.md``, and add them to the appropriate subsection based on the
   type of changes: Added, Changed, Deprecated, Removed, Fixed, or Security.
   The maintainers of this project will decide when to issue a new release, and
   at that time, the ``[Unreleased]`` section will be renamed to indicate the
   release version based on [Semantic Versioning](https://semver.org/), and a
   new ``[Unreleased]`` section will be created to track changes for the next
   release.

# Copying

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
