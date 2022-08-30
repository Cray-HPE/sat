# Introduction

The System Admin Toolkit (SAT) is a project to create a set of command-line
interfaces that cover gaps in the Shasta product which were identified by Cray
service and support staff. Various RESTful APIs currently exist in the system, but
they return large amounts of data in a JSON format which is hard for admins and
service personnel to parse. We would like to provide CLIs that are more friendly
for human consumption.

This repository contains the Python code implementing this CLI or set of CLIs.

# Installation

There are a few different ways that this software can be installed. At the
lowest level, this software is Python code that implements a `setup.py` script
that uses `setuptools`. This level of installation is useful for the developer
who would like to quickly install and test changes in a Python virtual
environment on a system.

In the product as the customer will see it, SAT is delivered as a container
image and run using a wrapper script that runs the container using `podman`.
This wrapper script is packaged and installed as an RPM package.

The complete SAT product, including the container image, wrapper script RPM and
necessary configuration is delivered in the SAT release distribution, also
known as the SAT product stream.

## Installation via pip

To install, use `pip3`:

```
pip3 install $CHECKOUT_DIR
```

Where `$CHECKOUT_DIR` is the directory where the SAT repository is checked out.

To uninstall, use the following command:

```
pip3 uninstall sat
```

# Contributing

See [instructions in CONTRIBUTING.md](CONTRIBUTING.md).


# Copying

See [License](LICENSE).

# See Also

- [SAT Podman wrapper script RPM](https://github.com/Cray-HPE/sat-podman)

- [SAT Product Stream](https://github.com/Cray-HPE/sat-product-stream)

- [SAT Documentation](https://github.com/Cray-HPE/docs-sat)
