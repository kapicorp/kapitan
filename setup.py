#!/usr/bin/env python3.6
#
# Copyright 2018 The Kapitan Authors
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


# From https://github.com/pypa/pip/issues/3610#issuecomment-356687173
def install_deps():
    """Reads requirements.txt and preprocess it
    to be feed into setuptools.

    This is the only possible way (we found)
    how requirements.txt can be reused in setup.py
    using dependencies from private github repositories.

    Links must be appendend by `-{StringWithAtLeastOneNumber}`
    or something like that, so e.g. `-9231` works as well as
    `1.1.0`. This is ignored by the setuptools, but has to be there.

    Returns:
         list of packages and dependency links.
    """
    with open('requirements.txt', 'r') as f:
        packages = f.readlines()
        new_pkgs = []
        links = []
        for resource in packages:
            if 'git+https' in resource:
                pkg = resource.split('#')[-1]
                links.append(resource.strip() + '-9876543210')
                new_pkgs.append(pkg.replace('egg=', '').rstrip())
            else:
                new_pkgs.append(resource.strip())
        return new_pkgs, links


pkgs, new_links = install_deps()

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

        'Programming Language :: Python :: 3.6'
    ],

    keywords='jsonnet kubernetes reclass jinja',
    py_modules=["kapitan"],
    packages=find_packages(),
    include_package_data=True,
    dependency_links=new_links,
    install_requires=pkgs,
    entry_points={
        'console_scripts': [
            'kapitan=kapitan.cli:main',
        ],
    },
)
