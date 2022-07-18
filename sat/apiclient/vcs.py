#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Client for interacting with the Version Control Service (VCS).
"""

# TODO (CRAYSAT-1214): This code was essentially copied verbatim from
# cfs_config_util/vcs.py, and so we should look at factoring this out when
# splitting out other API access code. This version of the code has a slight
# improvement over the version used in cfs-config-util as it can accept a full
# URL in addition to just the path to the config repo.

import os
import subprocess
from tempfile import NamedTemporaryFile
from urllib.parse import ParseResult, urlparse, urlunparse

from sat.cached_property import cached_property


class VCSError(Exception):
    """An error occurring during VCS access."""


class VCSRepo:
    """Main client object for accessing VCS."""
    _default_username = os.environ.get('VCS_USERNAME', 'crayvcs')

    def __init__(self, repo_url, username=None):
        """Constructor for VCSRepo.

        Args:
            repo_url (str): The URL to the repo on the git server.
            username (str or None): if a str, then use this username to
                authenticate to the git server. If None, use the default
                username.
        """
        parsed_url = urlparse(repo_url)
        self.repo_path = parsed_url.path

        if username is None:
            self.username = self._default_username
        else:
            self.username = username

    @property
    def remote_refs(self):
        """Get the remote refs for a remote repo.

        Returns:
            dict: mapping of remote refs to their corresponding commit hashes

        Raises:
            VCSError: if there is an error when git accesses VCS to enumerate
                remote refs
        """

        user_netloc = f'{self.username}@{self.vcs_host}'
        url_components = ParseResult(scheme='https', netloc=user_netloc, path=self.repo_path,
                                     params='', query='', fragment='')
        vcs_full_url = urlunparse(url_components)

        # Get the password directly from k8s to avoid leaking it via the /proc
        # filesystem.
        # TODO (CRAYSAT-1214): cfs-config-util uses the Python kubernetes
        # library (via a small `vcs-creds-helper` script) since kubectl isn't
        # available in the cfs-config-util image. As part of CRAYSAT-1214, we
        # probably want to figure out a consistent way to retrieve credentials
        # regardless of whether kubectl is installed. An argument could be made
        # that both approaches used are clunky in their own way, and perhaps
        # there's a cleaner common solution for both.
        with NamedTemporaryFile(delete=False) as cred_helper_script:
            cred_helper_script.write('#!/bin/bash\n'
                                     'kubectl get secret -n services vcs-user-credentials '
                                     '--template={{.data.vcs_password}} | base64 -d'.encode())

        os.chmod(cred_helper_script.name, 0o700)  # Make executable by user

        env = dict(os.environ)
        env.update(GIT_ASKPASS=cred_helper_script.name)
        try:
            proc = subprocess.run(['git', 'ls-remote', vcs_full_url],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env=env, check=True)
        except subprocess.CalledProcessError as err:
            raise VCSError(f"Error accessing VCS: {err}") from err
        finally:
            os.remove(cred_helper_script.name)

        # Each line in the output from `git ls-remote` has the form
        # "<commit_hash>\t<ref_name>", and we want the returned dictionary to map
        # the other way, i.e. from ref names to commit hashes. Thus when we split
        # each line on '\t', we should reverse the order of the resulting pair
        # before inserting it into the dictionary (hence the `reversed` in the
        # following comprehension.)
        return dict(
            tuple(reversed(line.split('\t')))
            for line in proc.stdout.decode('utf-8').split('\n')
            if line
        )

    def get_commit_hash_for_branch(self, branch):
        """Get the commit hash corresponding to the HEAD of some branch.

        Args:
            branch (str): the name of the branch

        Returns:
            str or None: a commit hash corresponding to the given branch,
                or None if the given branch is not found.
        """
        target_ref = f'refs/heads/{branch}'
        return self.remote_refs.get(target_ref)

    @cached_property
    def vcs_host(self):
        """str: Hostname of the VCS server."""
        return 'api-gw-service-nmn.local'  # TODO: Update per CRAYSAT-898.

    @cached_property
    def clone_url(self):
        """str: a full, git-clone-able URL to the repository"""
        return urlunparse(('https', self.vcs_host, self.repo_path, '', '', ''))
