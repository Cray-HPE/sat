FORMAT OPTIONS
--------------
These options govern the format of the output.

**--format** {**pretty**, **yaml**, **json**}
        Select output format - defaults to pretty.

**--no-borders**
        Do not print table borders.

**--no-headings**
        Do not print table headings.

**--reverse**
        Reverses the sorting order.

**--sort-by HEADING**
        Sort by the selected heading or comma seperated list of headings.
        Can also accept a 0-based column index or comma seperated list
        of 0-based column indexes.

**--show-empty**
        Show values for columns even if every value is ``EMPTY``. By default,
        such columns will be hidden.

**--show-missing**
        Show values for columns even if every value is ``MISSING``. By default,
        such columns will be hidden.
