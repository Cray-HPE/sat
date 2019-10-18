==========
 SAT-AUTH
==========

------------------------------------------------
Acquire authentication tokens and save for reuse
------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **auth**

DESCRIPTION
===========

The auth subcommand performs tasks that involve authentication and authorization
of **sat** with respect to access to the Shasta API.

The only task available at this time is the acquisition of authentication tokens.
The user is prompted for username and password. The username will have a default
value that is taken from (in order, if defined): **--username** global command-
line option, **username** option from **sat** configuration, or the login account
of the user running **sat**.

The token obtained will be stored, by default, in **$HOME/.config/sat/tokens/**
with filename *hostname.username*.json, where *hostname* is the hostname
of the API gateway (with appropriate substitutions to suit a filename), and
*username* is the username used when acquiring the token. This may be overriden
with the global command-line argument **--token-filename**.

SEE ALSO
========

sat(8)
