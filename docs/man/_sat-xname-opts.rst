XNAME OPTIONS
-------------

**-x** *XNAME*, **--xname** *XNAME*, **--xnames** *XNAME*
        This flag can be used to specify an xname on which to operate.
        This flag can be used multiple times to specify multiple xnames,
        or xnames can be provided in a single comma-separated string.

**-f** *PATH*, **--xname-file** *PATH*
        Specify a path to a newline-delimited file containing a list
        of xnames on which to operate. In order to share the path between
        the host and container when sat is run in a container environment,
        the path should be either an absolute or relative path of a file
        in or below the home or current directory.
