#!/usr/bin/python
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
    ],

    keywords='jsonnet kubernetes reclass jinja',
    py_modules=["kapitan"],
    packages=find_packages(),
    install_requires=[
        'jsonnet>=0.9.5',
        'PyYAML>=3.12',
        'Jinja2>=2.9.4',
        'reclass>=1.4.1',
        'jsonschema>=2.5.1'
    ],

    entry_points={
        'console_scripts': [
            'kapitan=kapitan.cli:main',
        ],
    },
)
