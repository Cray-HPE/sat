"""
Configurables used when shutting down the management cluster.

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

import os.path

LIVE = False

THISDIR = os.path.dirname(__file__)

if LIVE:
    PLAYBOOK = '/opt/cray/crayctl/ansible_framework/main/platform-shutdown.yml'
    WORKAROUND_PY = os.path.join(THISDIR, 'resources', 'kill_stalled_task.py')
    REMOTE_CMD = 'shutdown -h now'
else:
    HOME = '/root/sat-testing'
    PLAYBOOK = os.path.join(THISDIR, 'resources', 'testbook.yml')
    WORKAROUND_PY = os.path.join(THISDIR, 'resources', 'benign_scr.py')
    REMOTE_CMD = 'mkdir -p {}; touch {}'.format(HOME, os.path.join(HOME, 'helloworld_foo'))
