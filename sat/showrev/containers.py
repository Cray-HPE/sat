"""
Functions for obtaining version information about docker containers/images.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import docker


def get_dockers(substr=''):
    """Return names and version info from installed images.

    Args:
        substr: Only return information about docker images whose name or id
            contains the substr.
    Returns:
        A list of lists; each containing 3+ entries. The first entry contains
        the docker image id. The second contains the image's base-name. The
        third on to the end contain the image's versions.
    """

    client = docker.from_env()

    ret = []
    for image in client.images.list():
        tags = image.tags
        if len(tags) > 0:

            # Docker id is returned like 'sha256:fffffff'
            full_id = image.id.split(':')[-1]
            short_id = image.short_id.split(':')[-1]
            fields = tags[0].split(':')
            name = fields[-2].split('/')[-1]

            if not substr or substr in name or substr in full_id:
                versions = []
                for tag in tags:
                    version = tag.split(':')[-1]
                    if version not in versions and version != 'latest':
                        versions.append(version)

                if not versions:
                    versions.append('latest')

                ret.append([name, short_id, ', '.join(versions)])

    ret.sort()
    return ret
