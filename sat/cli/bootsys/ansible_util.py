"""
Support for the Ansible-controlled portion of shutdown of the management cluster.

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
import shlex
import subprocess

host_regex = re.compile(r'\s+\"([\w-]+)\",?$')


def get_groups(groups):
    spec = '+'.join(['groups["{}"]'.format(g) for g in groups])
    cmd = 'ansible localhost -m debug -a \'var={}\''.format(spec)
    pc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, encoding='utf-8')

    group = set()

    for line in pc.stdout.splitlines():
        m = host_regex.match(line)
        if m:
            group.add(m.group(1))

    return group
