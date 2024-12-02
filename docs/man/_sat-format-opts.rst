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
        Sort by the selected heading or comma-separated list of headings.
        Can also accept a 0-based column index or comma-separated list
        of 0-based column indexes.
        E.g. "--sort-by product_name,product_version" will sort
        results by product name and then by product version. Can accept a column
        name or a 0-based index. Enclose the column name in
        double quotes if it contains a space.

**--show-empty**
        Show values for columns even if every value is ``EMPTY``. By default,
        such columns will be hidden.

**--show-missing**
        Show values for columns even if every value is ``MISSING``. By default,
        such columns will be hidden.
