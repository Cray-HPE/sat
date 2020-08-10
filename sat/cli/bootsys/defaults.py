"""
Some constant default values used in the bootsys code.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import re

# The default directory where pod state is stored and read from
DEFAULT_PODSTATE_DIR = '/var/sat/podstates/'
# The default file where pod stats is stored and read from
DEFAULT_PODSTATE_FILE = DEFAULT_PODSTATE_DIR + 'pod-state.json'

# The regex matching standard CLE session templates, e.g. cle-1.3.0
CLE_BOS_TEMPLATE_REGEX = re.compile(r'^cle-\d+.\d+.\d+$')
# The name of the standard UAN session template
DEFAULT_UAN_BOS_TEMPLATE = 'uan'
# The number of seconds to wait before timing out on the BOS shutdowns
BOS_SHUTDOWN_TIMEOUT = 600
# The number of seconds to wait before timing out on the BOS boots
BOS_BOOT_TIMEOUT = 900
# The number of seconds to wait between checks on parallel BOS operations
PARALLEL_CHECK_INTERVAL = 10
