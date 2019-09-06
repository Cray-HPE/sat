# setuptools-based installation module for sat
# Copyright 2019 Cray Inc. All Rights Reserved

from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='sat',
    version='0.1.0',
    description="Shasta Admin Toolkit",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://stash.us.cray.com/projects/SAT/repos/sat',
    author='Cray, Inc.',
    packages=find_packages(exclude=['tests']),
    python_requires='>=3, <4',
    # Add top-level dependencies (e.g. requests) for this package
    install_requires=['docker'],

    # This makes setuptools generate our executable script automatically for us.
    entry_points={
        'console_scripts': [
            'sat=sat.main:main'
        ]
    },
)
