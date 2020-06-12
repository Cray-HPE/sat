==========
 SAT-AUTH
==========

------------------------------------------------
Acquire authentication tokens and save for reuse
------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **auth**

DESCRIPTION
===========

The auth subcommand performs tasks that involve authentication and authorization
of **sat** with respect to access to the API.

This entails the acquisition of authentication tokens for a given username.
The username will have a default value that is taken from (in order, if
defined): **--username** global command-line option, **username** option
from **sat** configuration, or the login account of the user running **sat**.
The password must be provided by the user when prompted.

FILES
=====

This subcommand requires extra files for its operation, and this section
details the purpose and default location of those files.

config - /etc/sat.toml
        This subcommand can read its default username from the global sat
        configuration file.

token files - $HOME/.config/sat/tokens/
        The obtained token will be stored, by default, in
        **$HOME/.config/sat/tokens/** with filename *hostname.username*.json,
        where *hostname* is the hostname of the API gateway (with appropriate
        substitutions to suit a filename), and *username* is the username used
        when acquiring the token.

        This may be overriden with the global command-line argument
        **--token-file** or the **token_file** option from **sat**
        configuration, which is ignored if blank.

EXAMPLES
========

The following command creates a new token for a user named "uastest".

::

    # sat --username uastest auth

And the token file will be created at
~/.config/sat/tokens/api_gw_service_nmn_local.uastest.json

Since the file is written in json format, jq can be used to print the access
token to the screen.

::

    # jq '.access_token' ~/.config/sat/tokens/api_gw_service_nmn_local.uastest.json

SEE ALSO
========

sat(8)

.. include:: _notice.rst
