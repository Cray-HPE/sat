"""
Mock data for ProductCatalog and InstalledProductVersion unit tests

(C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP.

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

from yaml import safe_dump


# Two versions of a product named SAT where:
# - The two versions have have no docker images in common with one another.
# - Both have configurations, but neither have images or recipes
SAT_VERSIONS = {
    '2.0.0': {
        'component_versions': {
            'docker': [
                {'name': 'cray/cray-sat', 'version': '1.0.0'},
                {'name': 'cray/sat-cfs-install', 'version': '1.4.0'}
            ],
            'repositories': [
                {'name': 'sat-sle-15sp2', 'type': 'group', 'members': ['sat-2.0.0-sle-15sp2']},
                {'name': 'sat-2.0.0-sle-15sp2', 'type': 'hosted'}
            ]
        },
        "configuration": {
           "clone_url": "https://vcs.machine.dev.cray.com/vcs/cray/sat-config-management.git",
           "commit": "5b7e74714c7f789e474ac9dbc2cae5c04d0e8e33",
           "import_branch": "cray/sat/2.0.0",
           "import_date": "2021-07-07T22:13:32.462655Z",
           "ssh_url": "git@vcs.machine.dev.cray.com:cray/sat-config-management.git"
        }
    },
    '2.0.1': {
        'component_versions': {
            'docker': [
                {'name': 'cray/cray-sat', 'version': '1.0.1'},
                {'name': 'cray/sat-other-image', 'version': '1.4.0'}
            ],
            'repositories': [
                {'name': 'sat-sle-15sp2', 'type': 'group', 'members': ['sat-2.0.1-sle-15sp2']},
                {'name': 'sat-2.0.1-sle-15sp2', 'type': 'hosted'}
            ]
        },
        "configuration": {
            "clone_url": "https://vcs.machine.dev.cray.com/vcs/cray/sat-config-management.git",
            "commit": "e1fa10b6865fb47ced6c1a6cfab2bc28fe149a74",
            "import_branch": "cray/sat/2.0.1",
            "import_date": "2021-10-26T15:23:06.078295Z",
            "ssh_url": "git@vcs.machine.dev.cray.com:cray/sat-config-management.git"
        }
    },
}

# Two versions of a product named COS where:
# - The two versions have one docker image name and version in common
# - The first version has no repositories, configuration, images, or recipes
# - The second version has repositories, configuration, images, and recipes
COS_VERSIONS = {
    '2.0.0': {
        'component_versions': {
            'docker': [
                {'name': 'cray/cray-cos', 'version': '1.0.0'},
                {'name': 'cray/cos-cfs-install', 'version': '1.4.0'}
            ]
        }
    },
    '2.0.1': {
        'component_versions': {
            'docker': [
                {'name': 'cray/cray-cos', 'version': '1.0.1'},
                {'name': 'cray/cos-cfs-install', 'version': '1.4.0'}
            ],
            'repositories': [
                {'name': 'cos-sle-15sp2', 'type': 'group', 'members': ['cos-2.0.1-sle-15sp2']},
                {'name': 'cos-2.0.1-sle-15sp2', 'type': 'hosted'}
            ]
        },
        "configuration": {
            "clone_url": "https://vcs.machine.dev.cray.com/vcs/cray/cos-config-management.git",
            "commit": "f0b17e13fcf7dd3b896196776e4547fdb98f1da7",
            "import_branch": "cray/cos/2.0.1",
            "import_date": "2021-11-24T12:04:25.210495Z",
            "ssh_url": "git@vcs.machine.dev.cray.com:cray/cos-config-management.git"
        },
        "images": {
            "cray-shasta-compute-sles15sp2.x86_64-1.5.66": {
                "id": "e2d58d7e-42b7-434d-b689-31ca3d053c51"
            }
        },
        "recipes": {
            "cray-shasta-compute-sles15sp2.x86_64-1.5.66": {
                "id": "54bc9447-73ba-4b06-a647-e5225451596d"
            }
        }
    },
}

# One version of "Other Product" that also uses cray/cray-sat:1.0.1
OTHER_PRODUCT_VERSION = {
    '2.0.0': {
        'component_versions': {
            'docker': [
                {'name': 'cray/cray-sat', 'version': '1.0.1'},
            ],
            'repositories': [
                {'name': 'sat-sle-15sp2', 'type': 'group', 'members': ['sat-2.0.0-sle-15sp2']},
                {'name': 'sat-2.0.0-sle-15sp2', 'type': 'hosted'}
            ]
        }
    }
}


# A mock version of the data returned when querying the Product Catalog ConfigMap
MOCK_PRODUCT_CATALOG_DATA = {
    'sat': safe_dump(SAT_VERSIONS),
    'cos': safe_dump(COS_VERSIONS),
    'other_product': safe_dump(OTHER_PRODUCT_VERSION)
}
