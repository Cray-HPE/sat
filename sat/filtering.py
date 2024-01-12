#
# MIT License
#
# (C) Copyright 2019-2021, 2024 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Generic output filtering utilities for SAT.
"""

import abc
import fnmatch
import logging
import operator

import parsec

from sat.cached_property import cached_property
from sat.util import match_query_key


LOGGER = logging.getLogger(__name__)

# Note: this comparator matching group is order-dependent because
# Python's re module is very silly and does not use maximal munch.
COMPARATOR_RE = r'(>=|<=|<|>|!=|=)'


class BaseFilterFunction(abc.ABC):
    """A callable object which implements a filtering function.

    This function essentially emulates a closure which uses the
    query_key and value parsed from some query string to filter
    an input dictionary. A value can be a number (int or float)
    or a string.

    """
    @abc.abstractmethod
    def __call__(self, row):
        """Checks whether a row should be included in output.

        Implementations may raise the following exceptions:
            KeyError: if the key filtered against is not present
                in the row
            TypeError: if the filter comparison has two inputs of
                incompatible types
        """

    @abc.abstractmethod
    def get_filtered_fields(self):
        """Gets a set of fields this function filters on.

        This is implemented in different ways in subclasses. Complex filters
        require a recursive implementation.
        """


class ComparisonFilter(BaseFilterFunction):
    def __init__(self, query_key, fields, comparator, cmpr_val):
        """A simple filter composed of a single comparison.

        Args:
            query_key (str): a subsequence of any of the field headings
            fields (Iterable[str]): the field headings of each column
            comparator (str): the comparison symbol (see COMPARATOR_RE above)
            cmpr_val (str|float): the value against which each column entry is
                compared
        """
        self._raw_query_key = query_key
        self.fields = fields
        self.comparator = comparator
        self.cmpr_val = cmpr_val

    @cached_property
    def query_key(self):
        """The key against each row will be filtered.

        The key can be any subsequence of the desired key to filter against.
        """
        return match_query_key(self._raw_query_key, self.fields)

    @cached_property
    def cmpr_fn(self):
        """The function used to compare the column value against the comparison value."""
        return _get_cmpr_fn(self.comparator, is_number=isinstance(self.cmpr_val, float))

    def __call__(self, row):
        if self.query_key is None:
            raise KeyError(self._raw_query_key)

        try:
            return self.cmpr_fn(row[self.query_key], self.cmpr_val)
        except TypeError as err:
            raise TypeError("Cannot filter value of type '{}' with value "
                            "of type '{}'.".format(type(row[self.query_key]).__name__,
                                                   type(self.cmpr_val).__name__)) from err

    def get_filtered_fields(self):
        return set() if self.query_key is None else {self.query_key}

    def __eq__(self, other):
        return self.fields == other.fields \
            and self.query_key == other.query_key \
            and self.comparator == other.comparator \
            and self.cmpr_val == other.cmpr_val


class CombinedFilter(BaseFilterFunction):
    def __init__(self, combinator, *filter_fns):
        """Combines multiple filters into one filter.

        Args:
            combinator ([bool] -> bool): a function which takes a
                sequence of boolean values and returns a boolean value.
                Typically, this is `all` or `any`.
            filter_fns (*FilterFunction): any number of FilterFunctions
                which should be combined.

        Returns:
            A FilterFunction which runs the constituent filters
            on an input and combines the results using the given
            combinator.
        """
        self.combinator = combinator
        self.filter_fns = list(filter_fns)

    def __call__(self, row):
        return self.combinator(filter_fn(row) for filter_fn in self.filter_fns)

    def get_filtered_fields(self):
        return set.union(*(child.get_filtered_fields() for child in self.filter_fns))


class CustomFilter(BaseFilterFunction):
    def __init__(self, filter_fn, fields, children=None):
        """Creates a simple filter function from some other function.

        This is used in order to wrap arbitrary functions within the
        BaseFilterFunction class.

        Args:
            filter_fn (dict -> bool): a function, which given some row, returns a
                boolean.
            fields (Iterable[str]): fields against which this filter function filters.
            children ([FilterFunction]): Any FilterFunctions that are children
                of this filter.

        Returns:
            A BaseFilterFunction which runs filter_fn() on its input and
            returns the result.
        """
        self.filter_fn = filter_fn
        self.children = children or []
        self.fields = set(fields)

    def __call__(self, row):
        return self.filter_fn(row)

    def get_filtered_fields(self):
        return set.union(self.fields, *(child.get_filtered_fields() for child in self.children))


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


def parse_query_string(query_string, fields):
    """Compiles a query string into a function for filtering rows.

    If query_string is invalid, ParseError is raised.

    Args:
        query_string: a string against which the rows should be
            filtered
        fields: a list of strings indicating which fields this
            filter may filter against

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
        content = yield lexeme(parsec.regex(r'\S+'))
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
        cmpr_val = yield (tok_quoted_str ^ tok_rhs)

        return ComparisonFilter(query_key, fields, comparator, cmpr_val)

    @parsec.generate
    def bool_and_expr():
        """Parses an 'and' expression. (e.g. 'foo = bar and baz > 10')

        Returns:
            Result of boolean and-operation.
        """
        lhs = yield comparison
        yield tok_and
        rhs = yield (bool_and_expr ^ comparison)
        return CombinedFilter(all, lhs, rhs)

    @parsec.generate
    def bool_expr():
        """Parses a boolean expression with operators: and, or.

        Returns:
            Result of boolean operation.
        """
        lhs = yield (bool_and_expr ^ comparison)
        oper = yield (tok_or | tok_and | tok_end)
        if oper not in ['and', 'or']:
            return lhs
        rhs = yield (bool_expr ^ comparison)
        return CombinedFilter(all if oper == 'and' else any, lhs, rhs)

    # Expressions can either be a boolean expression composing >= 2
    # comparisons, or just a single comparison.
    expr = bool_expr ^ comparison

    return expr.parse_strict(query_string)


def parse_multiple_query_strings(query_strings, fields, filter_fns=None):
    """Helper function to parse and combine query strings and functions.

    All filter functions passed in and built from the given query strings are
    combined with a boolean "and".

    Args:
        query_strings ([str]): filter strings to be parsed and combined.
        fields ([str]): fields the given filter strings and functions can
            filter against.
        filter_fns ([callable]): optional custom filter functions which should
            be combined with the given filter strings

    Returns:
        an instance of BaseFilterFunction which takes a row dictionary as its
        only positional argument and returns a boolean representing whether the
        given row should be included in the output, or None if no strings or
        filter functions are supplied.
    """
    if filter_fns is None:
        filter_fns = []

    all_filter_fns = [parse_query_string(query_string, fields)
                      for query_string in query_strings] + filter_fns

    if not all_filter_fns:
        return None
    if len(all_filter_fns) == 1:
        return all_filter_fns[0]
    return CombinedFilter(all, *all_filter_fns)


def remove_constant_values(dicts, constant_value, protect=None):
    """Filters the keys in each dict to remove keys that have a constant value

    Takes a list of dictionaries, which are all assumed to have the same keys,
    and removes any keys from all the dictionaries if the key has the same value
    for every dictionary in the list of dictionaries.

    Args:
        dicts (list): A list of dicts.
        constant_value: A value which must match the constant value of a key for
            that key to be removed from the dictionaries.
        protect: a set of column keys which may not have their contents removed
            if every row is the constant_value.

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

    if protect is None:
        protect = set()

    keys_to_keep = []
    for key in keys:
        if all(d[key] == constant_value for d in dicts):
            if key in protect:
                LOGGER.debug("All values for '%s' are '%s', but '%s' is a protected "
                             "key. Not discarding.", key, constant_value, key)
            else:
                LOGGER.info("All values for '%s' are '%s', omitting key.",
                            key, constant_value)
                continue

        keys_to_keep.append(key)

    return [dict_type([(key, d[key]) for key in keys_to_keep])
            for d in dicts]
