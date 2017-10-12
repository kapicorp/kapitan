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

setup(
    name='kapitan',
    version='0.9.14',

    description='Kapitan is a tool to manage kubernetes configuration using jsonnet templates',
    long_description='https://github.com/deepmind/kapitan',

    author='Ricardo Amaro',
    author_email='ramaro@google.com',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='jsonnet kubernetes reclass jinja',
    py_modules=["kapitan"],
    packages=find_packages(),
    install_requires=[
        'jsonnet>=0.9.4',
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
