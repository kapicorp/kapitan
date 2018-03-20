#!/usr/bin/env python3
#
# Copyright 2017 The Kapitan Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Kapitan setup.py for PIP install
"""

from setuptools import setup, find_packages
from kapitan.version import PROJECT_NAME, VERSION, DESCRIPTION, URL, AUTHOR, AUTHOR_EMAIL, LICENCE

setup(
    name=PROJECT_NAME,
    version=VERSION,

    description=DESCRIPTION,
    long_description=URL,
    url=URL,

    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENCE,

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],

    keywords='jsonnet kubernetes reclass jinja',
    py_modules=["kapitan"],
    packages=find_packages(),
    package_data={"": ["lib/*"]},
    include_package_data=True,
    install_requires=[
        'jsonnet==0.10.0',
        'PyYAML==3.12',
        'Jinja2>=2.10',
        # Latest commit from salt-formulas/reclass - python3 branch
        # TODO: Change commit hash to release tag, once python3 branch is merged in
        'git+git://github.com/salt-formulas/reclass@31770c6#egg=reclass',
        'jsonschema>=2.6.0',
        # Closest commit to official python-gnupg==0.4.1 + fix for https://bitbucket.org/vinay.sajip/python-gnupg/issues/84/on-osx-version-detection-fails-then-raises
        # TODO: Change to python-gnupg==0.4.2 once released
        'git+git://github.com/vsajip/python-gnupg@73b5d8d#egg=python-gnupg',
        'six>=1.11.0'
    ],

    entry_points={
        'console_scripts': [
            'kapitan=kapitan.cli:main',
        ],
    },
)
