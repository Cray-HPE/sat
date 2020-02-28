FILTER OPTION
-------------

**--filter** *QUERY* 
        Filter rows of the output.

The **--filter** option accepts a simple query language that is used to filter
rows in a table. Rows can be filtered by column using comparisons with the
operators =, !=, >, <, >=, and <=. Comparisons using the = operator support
the wildcards '*' (anything) and '?' (one character). Multiple comparisons can
be combined with the boolean operators 'and' and 'or', where 'and' has higher
precedence and parentheses are not supported. Filtering is not case sensitive.

Two example queries:

'fruit=apple and quantity>2' selects all rows where the fruit column is 'apple'
and the quantity column is greater than 2.

'xname = x1000c0* and hostname = nid??????' selects all rows where the xname
column starts with 'x1000c0' and the hostname column starts with 'nid' followed
by 6 characters.

A column can be specified by a subsequence of its name, meaning that characters
in the name can be left out. For example, a column name of 'citrus_fruit' can
be specified as 'citrus', 'fruit', or 'cit_fr'. A subsequence must match only
one column. If an output table has columns 'citrus_fruit' and 'tropical_fruit',
a query with 'fruit' is ambiguous, whereas 'citrus' and 'tropical' are not.


