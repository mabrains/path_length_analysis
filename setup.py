# =========================================================================================
# Copyright (c) 2024, Mabrains LLC
# Licensed under the GNU Lesser General Public License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.

#                    GNU Lesser General Public License
#                       Version 3, 29 June 2007

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: LGPL-3.0

# =========================================================================================

from setuptools import setup, find_packages

requirements = open("requirements.txt").read().strip().split("\n")

setup(
    name="path_analysis",
    packages=find_packages(),
    version="0.4.0",
    description="Measurement Of Path Length For Photonic and Electrical systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Mabrains LLC",
    author_email="contact@mabrains.com",
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">3.9",
)
