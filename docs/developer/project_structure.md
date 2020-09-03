# SAT Project Structure

The ``sat`` command-line interface consists of subcommands that perform a wide
range of different system administration tasks. These commands are detected at
runtime based on an established project structure.

This automatic detection of subcommands simplifies the process of adding a new
subcommand since the code that sets up the main parser and executes the entry
point of each subcommand does not need to be modified for the new subcommand.

## Subcommand structure overview

The code for each subcommand is in a separate subpackage of the ``sat.cli``
package. For example, the code for the ``sat hwinv`` subcommand is located in
the ``sat.cli.hwinv`` package.

For each subcommand, the subpackage within ``sat.cli`` must contain at least
the following two Python modules (i.e. files), each of which must contain the
following attributes:

* ``parser.py``

    * Must contain a function named ``add_SUBCOMMAND_subparser``, where
      ``SUBCOMMAND`` is the exact name of the subcommand. The function should
      have the signature shown below:
      
            def add_SUBCOMMAND_subparser(subparsers):
            """Add the SUBCOMMAND subparser to the parent parser.

            Args:
                subparsers: The argparse.ArgumentParser object returned by the
                    add_subparsers method.

            Returns:
                None
            """

* ``main.py``

    * Must contain a function named `do_SUBCOMMAND` where ``SUBCOMMAND`` is the
      exact name of the subcommand. The function should have the signature shown
      below. If it needs to exit with an exit code, it can do so directly with
      a call to ``sys.exit`` or by raising a ``SystemExit``.
      
            def do_SUBCOMMAND(args):
            """Do the SUBCOMMAND.
        
            Args:
                args: The argparse.Namespace object containing the parsed arguments
                    passed to this subcommand.
        
            Returns:
                None
            """

These requirements must be followed when developing new subcommands. Otherwise,
your subcommand will not be detected and ``sat`` will not be able to run it.
