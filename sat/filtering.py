"""
Generic output filtering utilities for SAT.

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
"""

import fnmatch
import logging
import operator

from parsec import ParseError
import parsec

from sat.util import (
    get_rst_header,
    match_query_key,
    yaml_dump
)

LOGGER = logging.getLogger(__name__)

# Note: this comparator matching group is order-dependent because
# Python's re module is very silly and does not use maximal munch.
COMPARATOR_RE = r'(>=|<=|<|>|!=|=)'


class FilterFunction:
    """A callable object which implements a filtering function.

    This function essentially emulates a closure which uses the
    query_key and value parsed from some query string to filter
    an input dictionary. A value can be a number (int or float)
    or a string.

    The 'query_key' argument passed to the constructor can be any
    subsequence of the desired key to filter against. The actual
    underlying dictionary key is computed the first time the function
    is called. This optimization is made since it is assumed that
    headings (i.e. keys) are identical for each dictionary in the
    iterable being filtered.
    """

    def __init__(self, query_key, comparator, cmpr_val):
        """Creates a new FilterFunction.

        Args:
            query_key: a subsequence of some key to filter against.
            comparator: a comparator string (i.e. =, !=, >, <, >=,
                or <=)
            cmpr_val: a string or number which defines the filter.
        """
        self._cmpr_fn = _get_cmpr_fn(comparator, is_number=isinstance(cmpr_val, float))
        self._cmpr_val = cmpr_val

        # The true key will be computed on the first run, so just
        # store whatever we're given here for now.
        self._raw_query_key = query_key

    def __call__(self, row):
        """Checks whether the given row matches the filter.

        Note that this function has side-effects; the query_key passed
        to the constructor can be a subsequence of the actual
        dictionary key to be filtered against, thus the underlying
        dictionary key will be computed based on the keys present in
        the first dictionary being filtered. This key will be stored
        and used in future comparisons. Care should be used if the
        same filter is applied to multiple lists with differing
        headers.

        Args:
            row: a dictionary which is to be filtered.

        Returns:
            True if row matches the filter, False otherwise.

        Raises:
            TypeError: if the value for the query key in the row can't be
                compared to the given value with the given comparison.
        """
        if not hasattr(self, '_computed_query_key'):
            self._computed_query_key = \
                match_query_key(self._raw_query_key, row.keys())
            if not self._computed_query_key:
                raise KeyError(f"Query key '{self._raw_query_key}' is invalid because it does not exist.")

        try:
            return self._cmpr_fn(row[self._computed_query_key],
                                 self._cmpr_val)

        except TypeError as err:
            raise TypeError("Cannot filter value of type '{}' with value "
                            "of type '{}'.".format(type(row[self._computed_query_key]).__name__,
                                                   type(self._cmpr_val).__name__)) from err


def combine_filter_fns(fns, combine_fn=all):
    """Creates a function which is the logical combination of input functions.

    Args:
        fns: iterable of functions which take a single argument
            and return a bool.
        combine_fn: a function which takes an iterable of booleans and
            returns a boolean. By default, this is `all`. (i.e., the
            logical 'and' of the input functions. For a logical 'or'
            behavior, `any` can be passed instead.

    Returns:
        a function which takes a single argument and returns
        the logical combination of all argument functions according to
        combine_fn.
    """
    def inner(x):
        return combine_fn(fn(x) for fn in list(fns))
    return inner


def _str_eq_cmpr(name, pattern):
    """Compares name to pattern with wildcards.

    Comparison is case insensitive. Pattern matching is based on the
    fnmatch module.

    Args:
        name (str): some value to check.
        pattern (str): a wildcard pattern which might
            match name.

    Returns:
        bool: True if name matches the pattern after wildcard
            expansion, and False otherwise.
    """
    return fnmatch.fnmatch(str(name).lower(),
                           pattern.lower())


def _get_cmpr_fn(fn_sym, is_number=False):
    """Returns a comparator function given some symbol.

    Comparator functions are built-in operators for >, >=, <, <=, =,
    and !=. For =, if is_number is True, then the built-in equals
    operator is returned. Otherwise, a wildcard matching function is
    returned.

    If fn_sym is an unrecognized operator, ValueError is raised.

    Args:
        fn_sym: a character containing a comparison symbol.
        is_number: whether the given function should just compare
            numbers or strings.

    Returns:
        a function which implements the given comparator.

    Raises:
        ValueError: if fn_sym is not a valid operator.
    """
    fns = {
        '>':   operator.gt,
        '>=':  operator.ge,
        '<':   operator.lt,
        '<=':  operator.le,
        '!=': (operator.ne if is_number
               else lambda n, p: not _str_eq_cmpr(n, p)),
        '=':  (operator.eq if is_number
               else _str_eq_cmpr)
    }

    if fn_sym not in fns:
        raise ValueError('Invalid comparison symbol')

    return fns.get(fn_sym)


def parse_query_string(query_string):
    """Compiles a query string into a function for filtering rows.

    If query_string is invalid, ParseError is raised.

    Args:
        query_string: a string against which the rows should be
            filtered

    Returns:
        a function which returns True if a given row matches
        the query string, and False otherwise.

    Raises:
        ParseError: if query_string is not a valid query.
    """

    def lexeme(p):
        """Creates subparsers (potentially) surrounded by whitespace.

        Args:
            p: a parsec.Parser object

        Returns:
            a parser which is followed by optional whitespace.
        """
        whitespace = parsec.regex(r'\s*')
        return p << whitespace

    tok_dq = lexeme(parsec.string('"'))
    tok_sq = lexeme(parsec.string('\''))
    tok_and = lexeme(parsec.string('and'))
    tok_or = lexeme(parsec.string('or'))
    tok_cmpr = lexeme(parsec.regex(COMPARATOR_RE))
    tok_lhs = lexeme(parsec.regex(r'[a-zA-Z_\-0-9]+'))
    tok_end = lexeme(parsec.regex(r'$'))

    @lexeme
    @parsec.generate
    def tok_double_quoted_str():
        """Parses a double-quoted string.

        Double-quoted strings can contain any non-double-quote
        character.

        Returns:
            a string containing the contents of the quoted string.
        """
        yield tok_dq
        content = yield parsec.regex(r'[^"]*')
        yield tok_dq

        return content

    @lexeme
    @parsec.generate
    def tok_single_quoted_str():
        """Parses a single-quoted string.

        Single-quoted strings can contain any non-single-quote
        character.

        Returns:
            a string containing the contents of the quoted string.
        """
        yield tok_sq
        content = yield parsec.regex(r'[^\']*')
        yield tok_sq

        return content

    tok_quoted_str = tok_double_quoted_str ^ tok_single_quoted_str

    @lexeme
    @parsec.generate
    def tok_rhs():
        """Parse the right hand side of an expression.

        The right hand side can be a number or some wildcard. Numbers
        are parsed into floats, and wildcards are returned as
        strings. These are handled separately from quoted strings,
        which are always interpreted as strings.

        Returns:
             a float if the value can be parsed as a number, or a
             string otherwise.
        """
        content = yield lexeme(parsec.regex(r'(\w|[*?.])+'))
        try:
            return float(content)
        except ValueError:
            return content

    @parsec.generate
    def comparison():
        r"""Parses a comparison expression (e.g. 'foo=bar')

        Comparison expressions have the following grammar, in pseudo-BNF:
            <ident> ::= tok_lhs
            <single_quoted_str> ::= ' <str> '
            <double_quoted_str> ::= " <str> "
            <wildcard> ::= tok_rhs
            <num> ::= FLOAT_RE
            <comparator> ::= '>=' | '>' | '<' | '<=' | '=' | '!='
            <cmpr_val> ::= <wildcard> | <num>
            <comparison> ::= <ident> <comparator> <cmpr_val>

        If the given value is a string, then the value in the
        row will be filtered using fnmatch.fnmatch (i.e.,
        wildcards will be expanded.) If the value is instead a
        number, a numerical comparison will be used.

        Returns:
            a function which can filter rows according to the
            comparison sub-expression which this parser parses.
        """
        # TODO: It might be a "good" idea in the future to refactor
        # the grammar a little bit to enforce types on certain
        # comparisons (e.g., only allow comparisons to numbers for
        # greater-than or less-than), but if this doesn't turn out to
        # be an issue, it probably isn't all that necessary.
        query_key = yield (tok_lhs ^ tok_quoted_str)
        comparator = yield tok_cmpr
        cmpr_val = yield (tok_rhs ^ tok_quoted_str)

        return FilterFunction(query_key, comparator, cmpr_val)

    @parsec.generate
    def bool_and_expr():
        """Parses an 'and' expression. (e.g. 'foo = bar and baz > 10')

        Returns:
            Result of boolean and-operation.
        """
        lhs = yield comparison
        yield tok_and
        rhs = yield (bool_and_expr ^ comparison)
        return combine_filter_fns([lhs, rhs], combine_fn=all)

    @parsec.generate
    def bool_expr():
        """Parses a boolean expression with operators: and, or.

        Returns:
            Result of boolean operation.
        """
        lhs = yield (bool_and_expr ^ comparison)
        oper = yield (tok_or | tok_and | tok_end)
        if oper not in ['and', 'or']:
            return combine_filter_fns([lhs], combine_fn=all)
        rhs = yield (bool_expr ^ comparison)
        return combine_filter_fns([lhs, rhs],
                                  combine_fn=all if oper == 'and' else any)

    # Expressions can either be a boolean expression composing >= 2
    # comparisons, or just a single comparison.
    expr = bool_expr ^ comparison

    return expr.parse_strict(query_string)


def _dont_care_call(excepts, fn, *args):
    """Use to wrap exception handling around a function.

    This is useful when you need to add exception handling to a function
    before passing that function around.

        eg. newfun = lambda x, y: _dont_care_call((TypeError), fun, x, y)

    Args:
        excepts: Exception or tuple of exceptions which should be caught.
        fn: A function that accepts args.
        args: Args to fn.

    Returns:
        The return value of fn(x). None will be returned if one of the
        exceptions in excepts was caught.
    """
    try:
        return fn(*args)
    except excepts:
        return None


def filter_list(dicts, query_strings):
    """Filters a list of dicts according to some query strings.

    If the filter string is invalid, then dicts will be returned as a
    list, contents unchanged. It is assumed that every dict in dicts
    will have identical keys. If not, ValueError will be raised.

    Args:
        dicts: a list or iterable of OrderedDicts which is to be
            filtered.
        query_strings: an iterable of some query strings against
            which to filter the input list.

    Returns:
        A list of dicts filtered according to query_string.

    Raises:
        ValueError: if keys in dicts are inconsistent.
        ParseError: if any of query_strings is invalid.
        KeyError: if attempting to filter against an invalid key.
        TypeError: if a value for the query key can't be compared to the given
            comparison value.
    """
    if not dicts:
        return []

    if not query_strings:
        return dicts

    # Assume the first row's headings are the "right ones."
    first, rest = dicts[0], dicts[1:]
    fkeys = first.keys()
    if any(d.keys() != fkeys for d in rest):
        raise ValueError('All input dicts must have same keys.')

    all_filter_fns = [parse_query_string(query_string)
                      for query_string in query_strings]
    combined_filters = combine_filter_fns(all_filter_fns)

    def filter_fn(x): return _dont_care_call(TypeError, combined_filters, x)

    return list(filter(filter_fn, dicts))


def remove_constant_values(dicts, constant_value):
    """Filters the keys in each dict to remove keys that have a constant value

    Takes a list of dictionaries, which are all assumed to have the same keys,
    and removes any keys from all the dictionaries if the key has the same value
    for every dictionary in the list of dictionaries.

    Args:
        dicts (list): A list of dicts.
        constant_value: A value which must match the constant value of a key for
            that key to be removed from the dictionaries.

    Returns:
        A list of dicts with keys removed from all dicts if that key has the
        given `constant_value` across all the dicts.
    """
    if not dicts:
        return []

    # All dicts are assumed to have the same keys and type
    keys = dicts[0].keys()
    # This is to preserve OrderedDict if given.
    dict_type = type(dicts[0])

    keys_to_keep = []
    for key in keys:
        if all(d[key] == constant_value for d in dicts):
            LOGGER.info("All values for '%s' are '%s', omitting key.",
                        key, constant_value)
        else:
            keys_to_keep.append(key)

    return [dict_type([(key, d[key]) for key in keys_to_keep])
            for d in dicts]
