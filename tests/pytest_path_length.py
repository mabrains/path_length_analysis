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

import pandas as pd
from path_analysis import path_length
import numpy as np


# Pytest function to test the correctness of the output DataFrame for simple route example
def test_simple_path():
    # Expected output data based on the processing logic
    expected_output = pd.DataFrame(
        {"port1": ["start"], "port2": ["end"], "length (um)": [19.831]}
    )

    # Call the function to get the actual output
    actual_output = path_length(
        gds_file="tests/route_path.gds",
        path_layer={"layer_no": 41, "layer_dtype": 0},
        cutting_layer={"layer_no": 66, "layer_dtype": 0},
    )

    # Sort ports to make sure that both data have same order [port1 & port2 are interchangeable]
    expected_output[["port1", "port2"]] = np.sort(
        expected_output[["port1", "port2"]], axis=1
    )
    actual_output[["port1", "port2"]] = np.sort(
        actual_output[["port1", "port2"]], axis=1
    )
    expected_output.reset_index(drop=True, inplace=True)
    actual_output.reset_index(drop=True, inplace=True)

    # Use pandas testing functions to check the correctness
    pd.testing.assert_frame_equal(actual_output, expected_output)


# Pytest function to test the correctness of the output DataFrame for intermediate route example
def test_intermediate_path():
    # Expected output data based on the processing logic
    expected_output = pd.DataFrame(
        {"port1": ["start"], "port2": ["end"], "length (um)": [162.511598]}
    )

    # Call the function to get the actual output
    actual_output = path_length(
        gds_file="tests/route_bend_path.gds",
        path_layer={"layer_no": 1, "layer_dtype": 0},
        cutting_layer={"layer_no": 66, "layer_dtype": 0},
    )
    print(actual_output)
    # Sort ports to make sure that both data have same order [port1 & port2 are interchangeable]
    expected_output[["port1", "port2"]] = np.sort(
        expected_output[["port1", "port2"]], axis=1
    )
    actual_output[["port1", "port2"]] = np.sort(
        actual_output[["port1", "port2"]], axis=1
    )
    expected_output.reset_index(drop=True, inplace=True)
    actual_output.reset_index(drop=True, inplace=True)

    # Use pandas testing functions to check the correctness
    pd.testing.assert_frame_equal(actual_output, expected_output)


# Pytest function to test the correctness of the output DataFrame for complex route example
def test_complex_path():
    # Expected output data based on the processing logic
    expected_output = pd.DataFrame(
        {
            "port1": ["splitter_p1_start", "splitter_p3_start"],
            "port2": ["splitter_p1_end", "splitter_p3_end"],
            "length (um)": [526.139253, 501.134027],
        }
    )
    # Call the function to get the actual output
    actual_output = path_length(
        gds_file="tests/lidar_no_rad.gds",
        path_layer={"layer_no": 1, "layer_dtype": 0},
        cutting_layer={"layer_no": 1, "layer_dtype": 10},
        nodes=[
            "splitter_p1_start",
            "splitter_p1_end",
            "splitter_p3_start",
            "splitter_p3_end",
        ],
    )
    # Sort ports to make sure that both data have same order [port1 & port2 are interchangeable]
    expected_output[["port1", "port2"]] = np.sort(
        expected_output[["port1", "port2"]], axis=1
    )
    actual_output[["port1", "port2"]] = np.sort(
        actual_output[["port1", "port2"]], axis=1
    )
    expected_output.reset_index(drop=True, inplace=True)
    actual_output.reset_index(drop=True, inplace=True)

    # Use pandas testing functions to check the correctness
    pd.testing.assert_frame_equal(actual_output, expected_output)
