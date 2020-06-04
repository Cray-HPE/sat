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

See [instructions in CONTRIBUTING.md](CONTRIBUTING.md).


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
