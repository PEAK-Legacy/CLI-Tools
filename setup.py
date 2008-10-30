#!/usr/bin/env python
"""Distutils setup file"""

import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

# Metadata
PACKAGE_NAME = "CLI-Tools"
PACKAGE_VERSION = "0.5"
PACKAGES = ['peak', 'peak.cli']

def get_description():
    # Get our long description from the documentation
    f = file('README.txt')
    lines = []
    for line in f:
        if not line.strip():
            break     # skip to first blank line
    for line in f:
        if line.startswith('.. contents::'):
            break     # read to table of contents
        lines.append(line)
    f.close()
    return ''.join(lines)

setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description="Plugin-capable cmdline apps w/option parsing, for wx, Twisted, and more",
    long_description = open('README.txt').read(), # get_description(),
    install_requires=['AddOns', 'DecoratorTools', 'SymbolType'],
    # 'Plugins', 'Trellis', -- not actually used yet
    author="Phillip J. Eby",
    author_email="peak@eby-sarna.com",
    license="PSF or ZPL",
    url="http://pypi.python.org/pypi/CLI-Tools",
    test_suite = 'test_cli_tools',
    packages = PACKAGES,
    namespace_packages = ['peak'],
)
