"""
Tests for VCS utility classes and functions.

Copyright (C) 2021 Hewlett Packard Enterprise Development LP. All Rights Reserved.

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

from textwrap import dedent
import subprocess
import unittest
from unittest.mock import patch, PropertyMock

from sat.apiclient.vcs import VCSError, VCSRepo


class TestVCSRepo(unittest.TestCase):
    """Tests for the VCSRepo class."""
    def setUp(self):
        self.mock_subprocess_run = patch('sat.apiclient.vcs.subprocess.run').start()

    def tearDown(self):
        patch.stopall()

    def test_default_username(self):
        """Test that the VCSRepo constructor sets the default username when None supplied"""
        repo = VCSRepo('foo/bar.git')
        self.assertEqual(repo.username, VCSRepo._default_username)

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

    def test_getting_clone_url(self):
        """Test retrieving the clone URL for the repo"""
        with patch('sat.apiclient.vcs.VCSRepo.vcs_host',
                   new_callable=PropertyMock) as mock_vcs_host:
            host = 'vcs.local'
            path = 'foo/bar.git'
            mock_vcs_host.return_value = host
            repo = VCSRepo(path)
            self.assertEqual(f'https://{host}/{path}', repo.clone_url)
