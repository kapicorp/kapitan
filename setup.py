#!/usr/bin/env python3

# Copyright 2019 The Kapitan Authors
# SPDX-FileCopyrightText: 2020 The Kapitan Authors <kapitan-admins@googlegroups.com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Kapitan setup.py for PIP install
"""

from setuptools import find_packages, setup

from kapitan.version import AUTHOR, AUTHOR_EMAIL, DESCRIPTION, LICENCE, PROJECT_NAME, URL, VERSION


EXTRAS ={
    "awskms" : ["boto3>=1.14.3"],
    "gkms" : ["google-api-python-client==1.7.11"],
    "gpg" : ["python-gnupg==0.4.6"],
    "vaultkv" : ["hvac==0.10.4"],
    "helm" : ["cffi"],
    "test" : ["docker==4.2.1", "hvac==0.10.4"],
}
EXTRAS["all"] = [ item for items in EXTRAS.values() for item in items]

# From https://github.com/pypa/pip/issues/3610#issuecomment-356687173
def install_deps(EXTRAS):
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
    with open("requirements.txt", "r") as f:
        packages = f.readlines()
        new_pkgs = []
        links = []
        for resource in packages:
            if "git+https" in resource:
                pkg = resource.split("#")[-1]
                links.append(resource.strip() + "-9876543210")
                pkg = pkg.replace("egg=", "").rstrip()
                if pkg in EXTRAS["all"]:
                    continue
                new_pkgs.append(pkg)
            else:
                if resource.strip() in EXTRAS["all"]:
                    continue
                new_pkgs.append(resource.strip())
        return new_pkgs, links


pkgs, new_links = install_deps(EXTRAS)

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
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="jsonnet kubernetes reclass jinja",
    py_modules=["kapitan"],
    python_requires=">=3.6",
    packages=find_packages(),
    package_data={"kapitan" : ["*.so"]},
    include_package_data=True,
    dependency_links=new_links,
    extras_require=EXTRAS,
    install_requires=pkgs,
    entry_points={"console_scripts": ["kapitan=kapitan.cli:main",],},
)
