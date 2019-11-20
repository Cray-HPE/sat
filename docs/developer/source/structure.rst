====================
Subcommand structure
====================

SAT subcommands are automatically detected at runtime. Subcommands
keep their code in separate packages, which are in turn also
subpackages of the ``sat.cli`` package. (For example, code relating to
the ``sat hwinv`` subcommand can be found in the ``sat.cli.hwinv``
package.) Each subcommand must have the following attributes:

1. There must be at least two Python modules in the subpackage:
   ``parser.py`` and ``main.py``. ``parser.py`` is used to construct a
   subcommand argument parser for processing command-line arguments
   specific to each subcommand. ``main.py`` contains that runs as the
   main body of a subcommand.

2. Given any subcommand, say ``foo``, the following requirements must
   be met.

   a. The module ``sat.cli.foo.parser`` *must* contain a function
      ``add_foo_subparser(subparsers)`` which accepts as its single
      argument the object returned by a call to
      ``ArgumentParser.add_subparsers()``. This function is called in
      order to build an argument parser specific to this subcommand.

   b. The module ``sat.cli.foo.main`` *must* contain a function
      ``do_foo(args)``, which accepts as its only argument the
      ``Namespace`` object returned from a call to
      ``ArgumentParser.parse_args()``.

These requirements must be followed when developing new
subcommands. Otherwise, your subcommand will not be detected and SAT
will not be able to run it.
