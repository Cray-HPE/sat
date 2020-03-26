# setuptools-based installation module for sat
# Copyright 2019 Cray Inc. All Rights Reserved

from os import path
from setuptools import setup, find_packages

from tools.changelog import get_latest_version_from_file

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    install_requires = []
    for line in f.readlines():
        commentless_line = line.split('#', 1)[0].strip()
        if commentless_line:
            install_requires.append(commentless_line)

version = get_latest_version_from_file('CHANGELOG.md')
if version is None:
    version = 'VERSION_MISSING'

setup(
    name='sat',
    version=version,
    description="System Admin Toolkit",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://stash.us.cray.com/projects/SAT/repos/sat',
    author='Cray, Inc.',
    license='Cray Proprietary',
    packages=find_packages(exclude=['tests', 'tests.*', 'tools', 'tools.*']),
    python_requires='>=3, <4',
    # Top-level dependencies are parsed from requirements.txt
    install_requires=install_requires,

    # This makes setuptools generate our executable script automatically for us.
    entry_points={
        'console_scripts': [
            'sat=sat.main:main'
        ]
    },
)
