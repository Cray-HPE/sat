"""
This module handles enabling and disabling entries in /etc/hosts.

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
import logging

from sat.cli.bootsys.util import run_ansible_playbook

LOGGER = logging.getLogger(__name__)

ENABLE_PLAYBOOK = '/opt/cray/crayctl/ansible_framework/main/enable-dns-conflict-hosts.yml'
DISABLE_PLAYBOOK = '/opt/cray/crayctl/ansible_framework/main/disable-dns-conflict-hosts.yml'


def do_enable_hosts_entries():
    """
    Run an ansible playbook that enables all entries in the /etc/hosts file
    that would normally conflict with DNS entries.

    This needs to be done after all platform services are stopped in order to
    provide a resolution for the hostnames of the form 'ncn-{m,s,w}###-mgmt' so
    that we can reach the nodes to issue IPMI commands to view the console and
    power them off.

    Raises:
        SystemExit: if the ansible playbook fails.
    """
    run_ansible_playbook(ENABLE_PLAYBOOK)


def do_disable_hosts_entries():
    """
    Run an ansible playbook that disables all entries in the /etc/hosts file
    that conflict with DNS entries.

    This needs to be done before starting platform services in order to avoid
    conflicting with the DNS resolution.

    Raises:
        SystemExit: if ansible playbook fails.
    """
    run_ansible_playbook(DISABLE_PLAYBOOK)
