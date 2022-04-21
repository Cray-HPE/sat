"""
Tools for adding information to `sat status` output.

(C) Copyright 2022 Hewlett Packard Enterprise Development LP.

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

from abc import ABC, abstractmethod
from collections import defaultdict
import logging

from sat.apiclient.cfs import CFSClient
from sat.apiclient.gateway import APIError
from sat.apiclient.hsm import HSMClient
from sat.apiclient.sls import SLSClient
from sat.util import get_val_by_path


LOGGER = logging.getLogger(__name__)


class StatusModuleException(Exception):
    """An exception which occurs during status module execution."""


class StatusModule(ABC):
    """An abstract base class for inserting data into a status table.

    Modules can return rows containing information from a particular CSM service.
    One module may be specified as the "primary" module, which returns a list of
    values for the primary key that other modules "join" their information on.
    (Typically, the primary module should be the HSM module, as it returns a
    list of xnames that are used by other modules to get CFS configurations, SLS
    hostnames, etc.) The primary module is specified by setting its class
    attribute `primary` to `True`. Only one class may be marked as primary.

    Modules may optionally specify a set of component types that they are
    relevant to by specifying a set of component type names in the
    `component_types` class attribute. For instance, only `Node` components
    retrieve hostnames from SLS, so the SLSStatusModule class sets its
    `component_types` attribute to `{"Node"}`. If a set of relevant component
    types is not supplied, then the module is implicitly relevant to all
    component types.
    """

    # The `modules` class attribute should not be set by subclasses; if it is,
    # then the child class will not be automatically added to the
    # `StatusModule.modules` list.
    modules = []
    primary = False
    component_types = set()

    def __init__(self, *, session, **_):
        """Construct a StatusModule.

        Subclasses may accept arbitrary keyword arguments, as well as the
        optional `primary_keys` argument, described below. Keyword arguments are
        passed through the `get_populated_rows()` method.

        Args:
            session (sat.session.SATSession): a session for connecting to the
                API gateway

        Keyword Args:
            primary_keys (optional, Iterable[str]): a list of the primary keys retrieved
                from the primary module. Should only be used by non-primary
                modules.
        """
        self.session = session

    @property
    @abstractmethod
    def headings(self):
        """[str]: the headings of the columns the module adds to the table

        This property should be added as a class attribute.
        """

    @property
    @abstractmethod
    def source_name(self):
        """str: the name of the data source used by this status module.

        E.g., for a module querying HSM, this should equal 'HSM'.

        This property should be added as a class attribute.
        """

    @property
    @abstractmethod
    def rows(self):
        """[dict]: the rows that the module should add to the table.

        The keys of the dicts returned by this property should match the
        headings given in the `headings` attribute.

        Raises:
            StatusModuleException: if there is an error while retrieving
                status information
        """

    def __init_subclass__(cls):
        cls.modules.append(cls)

    @staticmethod
    def _module_index(module):
        """Helper function to order retrieval of module data.

        This function is to be used as the `key` argument to a `sorted()` call.

        Args:
            module (StatusModule): a status module

        Returns:
            0 if the module is primary, 1 otherwise.
        """
        return (1, 0)[module.primary]

    @staticmethod
    def map_heading(heading):
        """Overridable method which can map headings of a dictionary to table headings.

        Args:
            heading (str): a key in a dictionary

        Returns:
            str: the mapped heading
        """
        return heading

    @staticmethod
    def include_heading(heading, **kwargs):
        """Overridable method which filters headings which should be present in
        the table given some parameters.

        For instance, this can be used to only include headings based on component type.

        Arguments:
            heading (str): the heading to filter

        Keyword Args:
            component_type (str): the component type for which the table is
                showing the status

        Returns:
            bool: True if the heading should be included, False otherwise
        """
        return True

    @classmethod
    def get_relevant_modules(cls, component_type=None, limit_modules=None):
        """Get a list of relevant modules for some component type.

        Args:
            component_type (None or str): if None, return all modules. If a str,
                return modules relevant to the given component type.
            limit_modules (None or list): if None, return all modules relevant to the
                given `component_type`. If a list, return a subset of the given
                modules relevant to the given `component_type`.

        Returns:
            list of relevant modules given the previous parameters.
        """
        modules = cls.modules if limit_modules is None else limit_modules

        if component_type is not None:
            return [module for module in modules
                    if not module.component_types or
                    component_type in module.component_types]
        return modules

    @classmethod
    def get_all_headings(cls, primary_key, limit_modules=None, initial_headings=None, component_type=None):
        """Get a list of headings applicable to the given modules and component types.

        Headings from modules are filtered based on their `include_headings`
        method.

        Args:
            primary_key (str): the primary key that all modules join on. This
                heading will always be first in the returned list.
            limit_modules (None or list): if None, return headings from all
                modules. If a list of StatusModule subclasses, return the subset
                of headings from only those modules.
            initial_headings (None or list): if None, sort headings arbitrarily,
                grouped by module. If a list, the provided headings will be
                placed at the beginning of the list following the primary key.
                Headings are not repeated.
            component_type (None or str): if None, return all headings from all
                modules. If a list, return the subset of headings from modules
                relevant to the given component type.

        Returns:
            [str]: the applicable headings
        """
        modules = cls.get_relevant_modules(limit_modules=limit_modules, component_type=component_type)
        if not modules:
            return []

        headings = [primary_key]
        if initial_headings is not None:
            for heading in initial_headings:
                if (any(heading in module.headings for module in modules)
                        and heading not in headings):
                    headings.append(heading)

        for module in modules:
            for heading in module.headings:
                if (heading not in headings
                        and module.include_heading(heading, component_type=component_type)):
                    headings.append(heading)
        return headings

    @classmethod
    def get_primary(cls):
        """Get the primary module.

        Returns:
            type: the StatusModule subclass designated as primary

        Raises:
            ValueError: if more than one module has its class attribute
                `primary` set to `True`.
        """
        primaries = [module for module in cls.modules if module.primary]
        if len(primaries) != 1:
            raise ValueError('Must be exactly one primary StatusModule')
        return primaries.pop()

    @classmethod
    def get_populated_rows(cls, *, primary_key, session, limit_modules=None, primary_key_type=str, **kwargs):
        """Return a list of rows joining data from all defined modules.

        Additional keyword arguments are passed through to StatusModule
        constructors.

        Keyword Args:
            primary_key (str): the primary key present in the output from all
                modules which the rows should be joined on.
            session (sat.session.SATSession): the session used to query CSM
                services.
            limit_modules (None or list): if None, return rows containing data
                from all defined modules. If a list, return rows containing data
                only from the provided modules.
            primary_key_type (str -> Any): a callable (or type) which takes a string
                and returns an object. The primary key of the populated rows
                will have this type.

        Returns:
            [dict]: data from the status modules as described above,
                which can be used to construct a table.
        """
        items_by_primary_key = defaultdict(dict)
        primary_module = cls.get_primary()

        modules = cls.get_relevant_modules(limit_modules=limit_modules)
        if primary_module not in modules:
            modules = [primary_module, *modules]

        for module in sorted(modules, key=cls._module_index):
            module_instance = module(session=session,
                                     primary_keys=items_by_primary_key.keys(),
                                     **kwargs)

            try:
                for row in module_instance.rows:
                    mapped_row = {}
                    for heading, value in row.items():
                        mapped_heading = module_instance.map_heading(heading)
                        if mapped_heading == primary_key:
                            value = primary_key_type(value)

                        mapped_row[mapped_heading] = value

                    if module.primary or mapped_row[primary_key] in items_by_primary_key:
                        items_by_primary_key[mapped_row[primary_key]].update(mapped_row)
            except StatusModuleException as err:
                LOGGER.warning('Could not retrieve status information from %s; %s',
                               module.source_name, err)

        return list(items_by_primary_key.values())


class HSMStatusModule(StatusModule):
    """Module for retrieving component state status information from HSM.

    This is the primary status module since it retrieves the list of xnames on the system.
    """

    headings = ['xname', 'Type', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Class', 'Role', 'SubRole', 'Net Type']
    source_name = 'HSM'
    primary = True

    def __init__(self, *, session, component_types, **_):
        super().__init__(session=session)
        self.component_types = [] if 'all' in component_types else component_types

    @staticmethod
    def map_heading(heading):
        return {
            'ID': 'xname',
            'NetType': 'Net Type'
        }.get(heading, heading)

    @staticmethod
    def include_heading(heading, *, component_type, **_):
        return component_type == 'Node' or heading not in ['NID', 'Role', 'SubRole']

    @property
    def rows(self):
        hsm_client = HSMClient(self.session)
        try:
            response = hsm_client.get('State', 'Components', params={'type': self.component_types})
        except APIError as err:
            raise StatusModuleException(f'Request to HSM API failed: {err}') from err

        try:
            response_json = response.json()
        except ValueError as err:
            raise StatusModuleException(f'Failed to parse JSON from component state response: {err}') from err

        try:
            components = response_json['Components']
        except KeyError as err:
            raise StatusModuleException(f'Key "{err}" not present in API response JSON.') from err

        # For SubRole, some types of nodes (specifically Compute nodes) are expected to
        # not have a SubRole, so 'None' looks a little more appropriate.
        for component in components:
            if component.get('Role') == 'Compute' and 'SubRole' not in component:
                component['SubRole'] = 'None'

        return components


class SLSStatusModule(StatusModule):
    """Module for retrieving hostname (alias) information from SLS."""
    headings = ['xname', 'Aliases']
    component_types = {'Node'}
    source_name = 'SLS'

    @property
    def rows(self):
        sls_client = SLSClient(self.session)

        try:
            sls_response = sls_client.get('hardware').json()
        except APIError as err:
            raise StatusModuleException(f'Could not query SLS for component aliases: {err}') from err
        except ValueError as err:
            raise StatusModuleException(f'Failed to parse JSON from SLS: {err}') from err

        xname_aliases = []
        for component in sls_response:
            if ({'Xname', 'ExtraProperties'}.issubset(set(component.keys()))
                    and 'Aliases' in component.get('ExtraProperties')):
                xname_aliases.append({
                    'xname': component.get('Xname'),
                    'Aliases': ', '.join(get_val_by_path(component, 'ExtraProperties.Aliases'))
                })
        return xname_aliases


class CFSStatusModule(StatusModule):
    """Module for retrieving node configuration information from CFS."""
    headings = ['xname', 'Desired Config', 'Configuration Status', 'Error Count']
    source_name = 'CFS'
    component_types = {'Node'}

    @staticmethod
    def map_heading(heading):
        return {
            'id': 'xname',
            'desiredConfig': 'Desired Config',
            'configurationStatus': 'Configuration Status',
            'errorCount': 'Error Count'
        }.get(heading, heading)

    @property
    def rows(self):
        cfs_client = CFSClient(self.session)
        try:
            cfs_response = cfs_client.get('components').json()
        except APIError as err:
            raise StatusModuleException(f'Failed to query CFS for component information: {err}') from err
        except ValueError as err:
            raise StatusModuleException(f'Failed to parse JSON from CFS component response: {err}') from err

        return cfs_response