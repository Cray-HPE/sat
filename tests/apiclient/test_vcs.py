#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
Tests for VCS utility classes and functions.
"""
import base64
import logging
from textwrap import dedent
import subprocess
import unittest
from unittest.mock import Mock, patch, PropertyMock

from sat.apiclient.vcs import VCSError, VCSRepo


class TestVCSRepo(unittest.TestCase):
    """Tests for the VCSRepo class."""
    def setUp(self):
        self.repo_name = 'sat-config-management'
        self.repo_path = f'/vcs/cray/{self.repo_name}.git'
        self.vcs_host = 'api-gw-service-nmn.local'
        self.clone_url = f'https://{self.vcs_host}{self.repo_path}'
        self.vcs_repo = VCSRepo(self.clone_url)

        self.vcs_username = 'crayvcs'

        self.mock_subprocess_run = patch('sat.apiclient.vcs.subprocess.run').start()
        self.mock_load_kube_config = patch('sat.apiclient.vcs.load_kube_config').start()
        self.mock_k8s_api_cls = patch('sat.apiclient.vcs.CoreV1Api').start()
        self.mock_k8s_api = self.mock_k8s_api_cls.return_value
        mock_vcs_secret_data = {'vcs_username': base64.b64encode(self.vcs_username.encode('utf-8'))}
        self.mock_k8s_api.read_namespaced_secret.return_value = Mock(data=mock_vcs_secret_data)

    def tearDown(self):
        patch.stopall()

    def test_init_with_user_clone_url(self):
        """Test creating a VCSRepo with a clone URL containing a username."""
        user_clone_url = f'https://admin@{self.vcs_host}{self.repo_path}'
        with self.assertLogs(level=logging.WARNING) as logs_cm:
            vcs_repo = VCSRepo(user_clone_url)

        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Ignoring username admin specified in clone URL {user_clone_url}',
                         logs_cm.records[0].msg)

        self.assertEqual(self.clone_url, vcs_repo.clone_url)
        self.assertEqual(f'https://{self.vcs_username}@{self.vcs_host}{self.repo_path}',
                         vcs_repo.user_clone_url)

    def test_repo_path(self):
        """Test repo_path property of VCSRepo."""
        self.assertEqual(self.repo_path, self.vcs_repo.repo_path)

    def test_repo_name(self):
        """Test repo_name property of VCSRepo."""
        self.assertEqual(self.repo_name, self.vcs_repo.repo_name)

    def test_vcs_username(self):
        """Test vcs_username property of VCSRepo."""
        self.assertEqual(self.vcs_username, self.vcs_repo.vcs_username)

    def test_user_clone_url(self):
        """Test user_clone_url property of VCSRepo."""
        self.assertEqual(f'https://{self.vcs_username}@{self.vcs_host}{self.repo_path}',
                         self.vcs_repo.user_clone_url)

    def test_getting_remote_refs(self):
        """Test getting remote refs from VCS"""
        self.mock_subprocess_run.return_value.stdout = dedent("""\
        e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e	HEAD
        7448d8798a4380162d4b56f9b452e2f6f9e24e7a	foo
        a3db5c13ff90a36963278c6a39e4ee3c22e2a436	bar
        """).encode('utf-8')

        repo = VCSRepo('foo/bar.git')
        self.assertEqual(repo.remote_refs, {
            'HEAD': 'e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e',
            'foo': '7448d8798a4380162d4b56f9b452e2f6f9e24e7a',
            'bar': 'a3db5c13ff90a36963278c6a39e4ee3c22e2a436',
        })

    def test_remote_refs_raises_vcs_error(self):
        """Test that getting remote refs throws an error when git issues occur"""
        self.mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, b'git ls-remote')
        repo = VCSRepo('foo/bar.git')
        with self.assertRaises(VCSError):
            _ = repo.remote_refs

    def test_getting_commit_hashes_for_versions(self):
        """Test getting a commit hash for the current version"""
        with patch('sat.apiclient.vcs.VCSRepo.remote_refs',
                   new_callable=PropertyMock) as mock_remote_refs:
            commit_hash = '6e42d6e57855cfe022c5481efa7c971114ee1688'
            mock_remote_refs.return_value = {
                'refs/heads/some-branch': commit_hash,
                'refs/heads/some-other-branch': '13a290994ff4102d5380e140bc1c0bd6fb112900',
            }
            retrieved_hash = VCSRepo('foo/bar.git').get_commit_hash_for_branch('some-branch')
            self.assertEqual(retrieved_hash, commit_hash)
