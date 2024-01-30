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

"""
Run Path Length Measurements.

Usage:
  path_length.py  --config=<config_file_path> [--run_dir=<run_dir_path>]

Options:
    --help -h                    Print this help message.
    --config=<param>             Yaml file contains the path length parameters.
    --run_dir=<run_dir_path>     directory to save all the results [default: pwd]
"""

import logging
import os
from datetime import datetime
import time
from docopt import docopt
import yaml
import pandas as pd
from typing import Any
from path_analysis.path_analysis import path_length


def read_yaml(yaml_file: str) -> dict[str, Any]:
    """
    Reading yaml file and saving the data to dictionary

    Args:
        yaml_file (str): yaml file path

    Returns:
        yaml_dic (dict): contains all the yaml file data
    """

    # load yaml config data
    with open(yaml_file, "r") as stream:
        try:
            yaml_dic = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logging.error(exc)
    return yaml_dic


if __name__ == "__main__":
    # arguments
    arguments = docopt(__doc__, version="RUN Path Length: 1.0")

    # logs format
    now_str = datetime.utcnow().strftime("length_run_%Y_%m_%d_%H_%M_%S")

    # checking config file existance
    config_in = arguments["--config"]
    if not os.path.exists(config_in):
        logging.error(f"The configuration file {config_in} doesn't exist, please check")
        exit(1)

    if (
        arguments["--run_dir"] == "pwd"
        or arguments["--run_dir"] == ""
        or arguments["--run_dir"] is None
    ):
        run_dir = os.path.join(os.path.abspath(os.getcwd()), now_str)
    else:
        run_dir = os.path.abspath(arguments["--run_dir"])

    # checking run_dir existance & creation
    if not os.path.isdir(run_dir):
        os.makedirs(run_dir, exist_ok=True)
    else:
        # shutil.rmtree(run_dir)
        os.makedirs(run_dir, exist_ok=True)

    # logs setup
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(os.path.join(run_dir, "{}.log".format(now_str))),
            logging.StreamHandler(),
        ],
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%d-%b-%Y %H:%M:%S",
    )

    # set pandas options
    pd.set_option("display.max_rows", None)

    # reading config file
    config_data = read_yaml(config_in)

    # Calling the main function
    time_start = time.time()
    path_length_df = path_length(**config_data)
    exc_time = time.time() - time_start

    # Save clean report with desired lengths
    path_length_df.to_csv(os.path.join(run_dir, "final_report_length.csv"), index=False)
    logging.info(f"path_length_report: \n {path_length_df}")

    # Reporting execution time
    logging.info(f"Path length execution time: {exc_time} sec")
