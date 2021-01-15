"""
Stages of the bootsys command.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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

import importlib
from collections import OrderedDict


def load_stage(bootsys_module, function):
    """Dynamically load stage function by name.

    load_stage is used in place of a conventional import so that `sat
    bootsys` can list the stage names without having to import the code
    for all the stages' functions.  This is especially useful for
    automatic command-line completion when listing the possible names
    of stages.

    Args:
        bootsys_module(str): The submodule under sat.cli.bootsys from which to
            load the stage function.
        function(str): The name of the function that runs the stage.

    Returns:
        The callable function.
    """
    module_path = f'sat.cli.bootsys.{bootsys_module}'
    return getattr(importlib.import_module(module_path), function)


# Each top-level key is the name of the action parsed from the command line
# Under each of those keys is an OrderedDict mapping from the name of the stage from
# the '--stage' option to a tuple of sat.cli.bootsys submodule and name of the function
# that takes the parsed args and then performs the actions for that stage.
#
# If a stage fails, the function can just choose to raise SystemExit(1) or
# sys.exit(1).
STAGES_BY_ACTION = {
    'shutdown': OrderedDict([
        ('capture-state', ('state_recorder', 'do_state_capture')),
        ('session-checks', ('service_activity', 'do_service_activity_check')),
        ('bos-operations', ('bos', 'do_bos_shutdowns')),
        ('cabinet-power', ('cabinet_power', 'do_cabinets_power_off')),
        ('bgp-check', ('bgp', 'do_bgp_check')),
        ('platform-services', ('platform', 'do_platform_stop')),
        ('ncn-power', ('mgmt_power', 'do_power_off_ncns'))
    ]),
    'boot': OrderedDict([
        ('ncn-power', ('mgmt_power', 'do_power_on_ncns')),
        ('platform-services', ('platform', 'do_platform_start')),
        ('k8s-check', ('k8s', 'do_k8s_check')),
        ('ceph-check', ('ceph', 'do_ceph_check')),
        ('bgp-check', ('bgp', 'do_bgp_check')),
        ('cabinet-power', ('cabinet_power', 'do_cabinets_power_on')),
        ('bos-operations', ('bos', 'do_bos_boots'))
    ])
}
