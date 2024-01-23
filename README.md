Path Length Calculations
================================

[![License](https://img.shields.io/badge/license-GPLv3-blue)](/LICENSE) 
[<p align="center"><img src="images/mabrains.png" width="700">](http://mabrains.com/)

# Table of contents
- [Introduction](#introduction)
- [Current-Status](#current-status)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [About Mabrains](#about-mabrains)
- [Contact-Us](#contact-us)
- [License](#license)


## Introduction

In the realm of electronic design and integrated circuit (IC) development, understanding the intricacies of signal paths is paramount. To streamline this process, we introduce our powerful tool – the Path Length Report Generator tailored for GDS files.

The Path Length Report Generator is a specialized utility designed for analyzing and reporting on signal path lengths within GDS files.

In a world where precision and efficiency are paramount, our Path Length Report Generator empowers designers and engineers to elevate their electronic designs to new heights. Dive into the intricacies of your GDS files and pave the way for enhanced performance in your designs.

## Current-Status

> :warning: We are currently treating the current content as an **experimental preview!**

The tool will be tagged with a production version when ready to do.

## Folder Structure
```
📁 Path_Length
 ┣ 📁images                     Contains images used in readme.
 ┣ 📜requirements.txt           List of python packages required for path length tool.
 ┣ 📜path_length.py                    python script to calculate path length for a gds file.
 ┣ 📜config.yaml                    configuration for path length script.
 ┣ 📜.flake8                    Includes flake8 configuration setup.
 ┣ 📜.gitignore                 Excludes certain local files from being pushed to Git.
 ┗ 📜README.md                  This file that describes the contents.
```

## Prerequisites

At a minimum:

- python 3.9+
- python3-venv


To install a virtual environment for ubuntu 22.04:

```bash
python3 -m pip install --user virtualenv
# OR
sudo apt-get install -y python3-venv
```


## Installation

To install the path length environment, run the following commands in your command-line prompt:

```bash
git clone https://github.com/mabrains/Path_Length.git
cd Path_Length/

python3 -m venv ./path_length_env
source ./path_length_env/bin/activate

pip install -r requirements.txt
```

## Usage
The configuration.yaml file should include the following.

*   gds file path
*   top cell name if more than cell available
*   path layer as tuple of two integers for layer number and dtype.
*   cutting layer as tuple of two integers for layer number and dtype.
*   nodes of interest to filter path report by as a list of strings corresponding to text placed on cutting polygons. if not included all nodes are considered.

configuration file example
```yaml
gds_file: path_to_file.gds
cell_name: top_cell
path_layer: 
- 1
- 0
cutting_layer:
- 2
- 0
nodes: 
- starting_node
- intermediate_node
- end_node
```
The `path_length.py` script takes your configuration file to run path length analysis on gds file. 

```bash
    python3 path_length.py (--help| -h)
    python3 path_length.py (--config=<config_file_path>) [--run_dir=<run_dir_path>]
```

Example:

```bash
    python3 path_length.py --config=gds_examples/test.gds --run_dir=path_length_results
```

### Options

- `--help -h`                           Print this help message.

- `--config=<config_file_path>`                  Yaml file contains the configuration needed for path length analysis parameters.
- `--run_dir=<run_dir_path>`                  Run directory to save all the results [default: pwd].

## About Mabrains

Mabrains was founded to achieve the main purpose to change the world of Chip Design using AI. Empowering the world with a new methodologies and techniques that would disrupt the status quo in the EDA industry.

We have contributed in developing many PDKs for Open Source Tools.


## Contact-Us

Requests for more information about Path Length tool and other open source technologies can be [submitted via this web form](https://mabrains.com/#contactus).


## License

The Path Length tool is released under the [GNU GENERAL PUBLIC LICENSE Version 3](/LICENSE)

The copyright details (which should also be found at the top of every file) are;

```
# SPDX-FileCopyrightText: 2024 Mabrains Company
# Licensed under the GNU GENERAL PUBLIC License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.

#                    GNU GENERAL PUBLIC LICENSE
#                       Version 3, 29 June 2007

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# SPDX-License-Identifier: GPL-3.0
```
