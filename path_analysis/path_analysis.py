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

import gdstk
import logging
import os
from math import sqrt
import pandas as pd
import networkx as nx
from functools import partial


def get_length(poly: gdstk.Polygon) -> float:
    """
    Calculate the length of a polygon using its area and perimeter.

    Args:
        poly (gdstk.Polygon): The polygon for which to calculate the length.

    Returns:
        float: The calculated length of the polygon.

    Raises:
        ValueError: If the discriminant (value inside the square root) is negative,
                    indicating no real solution for the length with the given area and perimeter.

    Note:
        The area and perimeter are calculated using the gdstk library
        methods `area()` and `perimeter()`.
        The discriminant is rounded to 12 decimal places to avoid precision issues.
        If a negative value in the square root is detected, an error is logged,
        and a ValueError is raised.

    Example:
        >>> poly = gdstk.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        >>> length = get_length(poly)
        >>> print(f"The length is: {length}")
    """
    area = poly.area()
    perimeter = poly.perimeter()
    discriminant = round(perimeter * perimeter / 16 - area, 12)

    if discriminant < 0:
        logging.error(
            f"area = {area}, perimeter = {perimeter}, negative value {discriminant} in sqrt"
        )
        raise ValueError(
            "Invalid input: No real solution for the length with the given area and perimeter"
        )

    return perimeter / 4 + sqrt(discriminant)


def get_polygons(
    gdstk_lib: gdstk.Library,
    path_layer: tuple[int, int],
    cutting_layer: tuple[int, int],
    cell_name: str | None = None,
) -> tuple[list[gdstk.Polygon], list[list[gdstk.Polygon]], list[list[gdstk.Label]]]:
    """
    Retrieve polygons representing paths and cutting regions based on input parameters.

    Parameters:
    - gdstk_lib (gdstk.Library): The gdstk.Library containing the desired cell.
    - path_layer (tuple[int, int]): Layer number and dtype for paths polygons.
    - cutting_layer (tuple[int, int]): Layer number and dtype for cutting polygons.
    - cell_name (str, optional): Name of the cell. Defaults to None.

    Returns:
    tuple: A tuple containing three elements.
        - List of path polygons (gdstk.Polygon).
        - List of list of cutting polygons, where each list represents cutting polygons
          corresponding to a path polygon (list[list[gdstk.Polygon]])
        - List of list of cutting labels, where each list represents cutting labels
          corresponding to a path polygon (list[list[gdstk.Polygon]])

    The function performs the following steps:
    1. Calls _get_polygons to obtain path polygons, cutting polygons, and labels.
    2. Filters cutting polygons to include only valid polygons.
    3. Filters labels based on whether their origin is inside cutting polygons.
    ```
    """
    path_polygons, cutting_polygons, labels = _get_polygons(
        gdstk_lib, path_layer, cutting_layer, cell_name
    )
    cutting_polygons, labels = filter_polygons(path_polygons, cutting_polygons, labels)
    return path_polygons, cutting_polygons, labels


def _get_polygons(
    gdstk_lib: gdstk.Library,
    path_layer: tuple[int, int],
    cutting_layer: tuple[int, int],
    cell_name: str | None = None,
) -> tuple[gdstk.Polygon, gdstk.Polygon, list[gdstk.Label]]:
    """
    Retrieve polygons representing paths and cutting regions from a gdstk.Library.

    Parameters:
    - gdstk_lib (gdstk.Library): The gdstk.library containing the desired cell.
    - path_layer (tuple[int, int]): Layer number and dtype for paths polygons.
    - cutting_layer (tuple[int, int]): Layer number and dtype for cutting polygons.
    - cell_name (str, optional): Name of the cell. Defaults to None.

    Returns:
    tuple: A tuple containing three elements.
        - Polygons representing path (gdstk.Polygon).
        - Polygons representing cutting regions (gdstk.Polygon).
        - List of labels associated with cutting regions (list[gdstk.Label]).

    The function performs the following steps:
    1. Retrieves the top-level cells from the gdstk.Library.
    2. If no cells are available, logs an error and exits.
    3. If multiple top-level cells exist and no specific cell is specified, logs an error and exits.
    4. If a specific cell name is provided, searches for the cell with that name.
    5. Retrieves path polygons from the selected cell based on layer and datatype.
    6. Merges path polygons using gdstk.boolean with "or" operation.
    7. Retrieves cutting polygons and labels from the selected cell based on layer and datatype.
    8. Returns path polygons, cutting polygons, and labels.
    """
    cells = gdstk_lib.top_level()
    if len(cells) < 1:
        logging.error("no cells available")
        exit(1)

    if len(cells) > 1 and cell_name is None:
        logging.error("Please specify a cell name when multiple top-level cells exist.")
        exit(1)

    cell: gdstk.Cell | None = None

    if cell_name is None:
        cell = cells[0]
    else:
        for c in cells:
            if c.name == cell_name:
                cell = c
                break
    if cell is None:
        logging.error("Invalid cell name")
        exit(1)

    path_polygons = cell.get_polygons(
        depth=None, layer=path_layer[0], datatype=path_layer[1]
    )
    path_polygons = gdstk.boolean(path_polygons, path_polygons, "or")
    cutting_polygons = cell.get_polygons(
        depth=None, layer=cutting_layer[0], datatype=cutting_layer[1]
    )
    labels = cell.get_labels(
        depth=None, layer=cutting_layer[0], texttype=cutting_layer[1]
    )
    return path_polygons, cutting_polygons, labels


def filter_polygons(
    path_polygons: list[gdstk.Polygon],
    cutting_polygons: list[gdstk.Polygon],
    labels: list[gdstk.Label],
) -> tuple[list[list[gdstk.Polygon]], list[list[gdstk.Label]]]:
    """
    Filters cutting polygons and labels based on their relationship with path polygons.

    Parameters:
    - path_polygons (list[gdstk.Polygon]): List of path polygons.
    - cutting_polygons (list[gdstk.Polygon]): List of cutting polygons.
    - labels (list[gdstk.Label]): List of labels associated with cutting polygons.

    Returns:
    Tuple containing two filtered lists:
    1. List of filtered cutting polygons.
    2. List of filtered labels.

    This function filters cutting polygons based on whether they intersect with any of
    the path polygons. It also filters labels associated with the filtered cutting polygons.
    Duplicate labels are checked, and an error is raised if duplicates are found.

    Returns the rearranged data as a tuple of lists:
    - List of lists of cutting polygons per path polygon.
    - List of lists of labels per path polygon.
    """
    # filter cutting polygons
    cutting_polygons = [
        polygon
        for polygon in cutting_polygons
        if check_if_polygon_cuts_path(polygon, path_polygons)
    ]

    # filter labels
    labels = [
        label
        for label, condition1 in zip(
            labels,
            gdstk.inside([label.origin for label in labels], cutting_polygons),
        )
        if condition1
    ]

    labels_text = [(label.text) for label in labels]
    duplicate_labels = get_duplicates(labels_text)
    if duplicate_labels:
        logging.error(
            (
                f"found duplicate labels {duplicate_labels},"
                "please make sure to name your cutting polygons with a unique name"
            )
        )
        exit(1)

    return _rearrange_data(path_polygons, cutting_polygons, labels)


def _rearrange_data(
    path_polygons: list[gdstk.Polygon],
    cutting_polygons: list[gdstk.Polygon],
    labels: list[gdstk.Label],
) -> tuple[list[list[gdstk.Polygon]], list[list[gdstk.Label]]]:
    """
    Rearranges data by associating cutting polygons and labels with path polygons.

    Parameters:
    - path_polygons (list[gdstk.Polygon]): List of path polygons.
    - cutting_polygons (list[gdstk.Polygon]): List of cutting polygons.
    - labels (list[gdstk.Label]): List of labels associated with cutting polygons.

    Returns:
    Tuple containing two lists:
    1. List of lists of cutting polygons per path polygon.
    2. List of lists of labels per path polygon.
    """
    labels_points = [label.origin for label in labels]
    sorted_labels: list[gdstk.Label] = []
    for polygon in cutting_polygons:
        for label, condition in zip(labels, gdstk.inside(labels_points, polygon)):
            if condition:
                sorted_labels.append(label)
                break
    cutting_polygons_per_path: list[list[gdstk.Polygon]] = []
    cutting_labels_per_path: list[list[gdstk.Label]] = []
    for path_polygon in path_polygons:
        valid_cutting_polygons = []
        valid_cutting_labels = []
        for polygon, label in zip(cutting_polygons, sorted_labels):
            if check_if_polygon_cuts_path(polygon, path_polygon):
                if polygon.contain(label.origin):
                    valid_cutting_polygons.append(polygon)
                    valid_cutting_labels.append(label)
        cutting_polygons_per_path.append(valid_cutting_polygons)
        cutting_labels_per_path.append(valid_cutting_labels)
    return cutting_polygons_per_path, cutting_labels_per_path


def get_duplicates(lst: list) -> list:
    """
    Finds and returns duplicate elements in a list.

    Parameters:
    - lst (list): The input list to check for duplicates.

    Returns:
    list: A list containing the duplicate elements found in the input list.

    Example:
    duplicates = get_duplicates([1, 2, 2, 3, 4, 4, 5])
    # Result: [2, 4]
    """
    seen = set()
    duplicates = []
    for item in lst:
        if item in seen:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def check_if_polygon_cuts_path(
    polygon: gdstk.Polygon, path_polygons: list[gdstk.Polygon]
) -> bool:
    """
    Check if a polygon cuts through a set of path polygons.

    Parameters:
    - polygon (gdstk.Polygon): The polygon to be checked for cutting through paths.
    - path_polygons (list[gdstk.Polygon]): List of path polygons to check against.

    Returns:
    bool: True if the given polygon cuts through any polygon of the set of path polygons,
        False otherwise.

    The function performs the following steps:
    1. Calculates the boolean operation 'not' between the given polygon and
        the set of path polygons.
    2. Checks if the length of the resulting polygons is greater than 1,
    indicating cutting through paths.
    3. Handles cases where the boolean operations 'and' yields empty list.(not on path).
    4. Handles cases where the cutting polygon is on the path end.
        (if any vertix is inside the path it will be considered invalid cut).
    """
    splitted_polygons = gdstk.boolean(path_polygons, polygon, "not")
    if len(splitted_polygons) > 1:
        return True
    if len(splitted_polygons) == 1 and gdstk.boolean(path_polygons, polygon, "and"):
        return not gdstk.any_inside(polygon.points, path_polygons)
    return False


def split_polygon(
    poly: gdstk.Polygon, cutting_polygons: list[gdstk.Polygon]
) -> list[gdstk.Polygon]:
    """
    Split a polygon using a set of cutting polygons.

    Parameters:
    - poly (gdstk.Polygon): The polygon to be split.
    - cutting_polygons (list[gdstk.Polygon]): List of cutting polygons for the split operation.

    Returns:
    list[gdstk.Polygon]: List of polygons resulting from the split operation.

    The function performs the following steps:
    1. Calculates the boolean operation 'not' between the given polygon and the cutting polygons.
    2. Returns a list of polygons resulting from the split operation.

    Example:
    ```
    split_result = split_polygon(
        poly=my_polygon,
        cutting_polygons=[cutting1, cutting2, cutting3]
    )
    ```
    """
    return gdstk.boolean(poly, cutting_polygons, "not")


def construct_graph_data_frame(
    path_polygons: list[gdstk.Polygon],
    cutting_polygons: list[list[gdstk.Polygon]],
    labels: list[list[gdstk.Label]],
) -> pd.DataFrame:
    """
    Construct a DataFrame representing graph data from path_polygons and cutting polygons.

    Parameters:
    - path_polygons (list[gdstk.Polygon]): List of path polygons.
    - cutting_polygons (list[list[gdstk.Polygon]]): List of lists,
      where each list represents cutting polygons corresponding to a path polygon.
    - labels (list[list[gdstk.Label]]): List of lists of labels associated with cutting polygons.

    Returns:
    pd.DataFrame: DataFrame with columns 'port1', 'port2', and 'length' representing
    the graph data.

    The function performs the following steps:
    1. Iterates over path_polygons, cutting_polygons to process each path and its cutting polygons.
    2. splits path_polygon with cutting_polygons.
    3. For each sub_polygon, extracts port1, port2, and length.
    4. Appends records (port1, port2, length) to a list.
    5. Constructs a DataFrame from the list of records.
    6. Returns the constructed DataFrame.

    The resulting DataFrame might look like:
    ```
        port1               port2        length
    0   label1_tail_0       node_1         10.0
    1   node_1              node_2         15.0
    2   node_2          polygon_0_tail_1   12.0
    3   polygon_1_tail_0    node_4         8.0
    4   node_4          polygon_1_tail_1   20.0
    ```
    """
    records = []
    path_labels = move_labels_on_path(path_polygons, cutting_polygons, labels)
    for i, (poly, cutting_polys) in enumerate(zip(path_polygons, cutting_polygons)):
        tail_counter = 0
        if cutting_polys:
            splitted_polygons = split_polygon(poly, cutting_polys)
            for sub_poly in splitted_polygons:
                node_names = get_node_names(sub_poly, path_labels)
                if len(node_names) == 1:
                    continue
                    port1 = node_names[0]
                    port2 = f"polygon_{i}_tail_{tail_counter}"
                    tail_counter += 1
                elif len(node_names) == 2:
                    port1, port2 = node_names
                else:
                    continue
                length = get_length(sub_poly)
                records.append([port1, port2, length])
    df = pd.DataFrame(records, columns=["port1", "port2", "length"])
    return df


def get_node_names(poly, labels: list[gdstk.Label]) -> list[str]:
    """
    Get unique node names associated with a polygon based on label positions.

    Parameters:
    - poly (gdstk.Polygon): The polygon for which node names are determined.
    - labels (list[gdstk.Label]): List of labels associated with the polygon.

    Returns:
    list[str]: List of unique node names associated with the polygon.

    The function performs the following steps:
    1. Extracts points and corresponding names from the given list of labels.
    2. checks whether points are inside the polygon.
    3. Appends names to the list 'node_names' if the corresponding point are inside the polygon.
    4. Returns a list containing unique node names.

    Example:
    ```
    polygon = gdstk.Polygon(...)
    labels = [label1, label2, label3]
    node_names = get_node_names(polygon, labels)
    # Result: ['port1', 'port2']
    ```
    """
    points = [label.origin for label in labels]
    names = [label.text for label in labels]
    node_names: list[str] = []
    for name, condition in zip(names, gdstk.inside(points, poly)):
        if condition:
            node_names.append(name)
    return list(set(node_names))


def _get_path_labels(
    path: gdstk.Polygon, cutting_poly: gdstk.Polygon, text: str
) -> list[gdstk.Label]:
    """
    Create labels with a specified text at the vertices of the intersection
    between a path polygon and a cutting polygon.

    Parameters:
    - path (gdstk.Polygon): The path polygon.
    - cutting_poly (gdstk.Polygon): The cutting polygon.
    - text (str): The text to be assigned to the labels.

    Returns:
    list[gdstk.Label]: List of labels with the specified text at the vertices
    of the intersection between the path and cutting polygons.
    """

    intersection = gdstk.boolean(cutting_poly, path, "and")
    if intersection:
        points = intersection[0].points
    else:
        logging.error(f"failed to find intersection between {cutting_poly}, and {path}")
        exit(1)
    return [gdstk.Label(text, origin=point) for point in points]


def move_labels_on_path(
    path_polygons: list[gdstk.Polygon],
    cutting_polygons: list[list[gdstk.Polygon]],
    labels: list[list[gdstk.Label]],
) -> list[gdstk.Label]:
    """
    Create labels with a specified text at the vertices of the intersection
    between a path polygon and a cutting polygon.

    Parameters:
    - path_polygons (list[gdstk.Polygon]): List of path polygons.
    - cutting_polygons (list[list[gdstk.Polygon]]): List of lists containing cutting polygons
        corresponding to each path.
    - labels (list[list[gdstk.Label]]): List of lists containing labels
        associated with cutting polygons.

    Returns:
    list[gdstk.Label]: List of path_labels.

    The function performs the following steps:
    1. Iterates over each path polygon, its cutting polygons, and associated labels.
    2. For each cutting polygon and label, computes the labels along the path
        based on the vertices of the intersection.
    3. Appends the calculated labels to the 'moved_labels' list.
    4. Returns the list of moved labels.
    """
    moved_labels = []
    for path_poly, cutting_polys, labels in zip(
        path_polygons, cutting_polygons, labels
    ):
        get_path_labels = partial(_get_path_labels, path=path_poly)
        for poly, label in zip(cutting_polys, labels):
            moved_labels += get_path_labels(cutting_poly=poly, text=label.text)
    return moved_labels


def get_nx_graph(graph_data_frame: pd.DataFrame) -> nx.Graph:
    """
    Create a NetworkX graph from a DataFrame containing edge information.
    Args:
        graph_data_frame (pd.DataFrame): A DataFrame with columns 'port1', 'port2', and 'length'
                                          representing edges and their corresponding lengths.
    Returns:
        nx.Graph: A NetworkX graph constructed from the provided DataFrame.
    Note:
        This function uses the `nx.from_pandas_edgelist` method to create a graph.
        The 'port1' and 'port2' columns of the DataFrame represent nodes,
        and the 'length' column is used as the edge attribute.
    Example:
        >>> data = {
        ...     'port1': ['a', 'b'],
        ...     'port2': ['b', 'c'],
        ...     'length': [1.0, 2.0]
        ... }
        >>> graph_df = pd.DataFrame(data)
        >>> graph = get_nx_graph(graph_df)
        >>> print(list(graph.edges(data=True)))
        [('a', 'b', {'length': 1.0}),
         ('b', 'c', {'length': 2.0})]
    """
    return nx.from_pandas_edgelist(graph_data_frame, "port1", "port2", "length")


def get_paths_report(graph: nx.Graph) -> pd.DataFrame:
    """
    Generate a report of shortest path lengths between all pairs of nodes in a graph.

    Parameters:
    - graph (nx.Graph): The input graph with weighted edges.

    Returns:
    pd.DataFrame: DataFrame containing information about shortest path lengths
    between all pairs of nodes. Columns include 'port1', 'port2', and 'length'.

    The function performs the following steps:
    1. Iterates over all pairs of nodes in the graph.
    2. Uses NetworkX's shortest_path_length to find the shortest path length between each pair,
       considering edge weights defined by the 'length' attribute.
    3. Handles cases where no path exists between nodes using a try-except block.
    4. Appends records (port1, port2, length) to a list.
    5. Constructs a DataFrame from the list of records.
    6. Adds a 'sorted_nodes' column for later duplicate checking.
    7. Drops duplicate rows based on the 'sorted_nodes' column.
    8. Returns the resulting DataFrame.
    """
    nodes = graph.nodes
    records = []
    for start_node in nodes:
        for end_node in nodes:
            if start_node != end_node:
                try:
                    path_length = nx.shortest_path_length(
                        graph, start_node, end_node, weight="length"
                    )
                except nx.NetworkXNoPath:
                    path_length = -1
                records.append([start_node, end_node, path_length])
    if not records:
        logging.error(f"no_nodes detected : {records}")
        exit(1)

    report = pd.DataFrame(records)
    report.columns = ["port1", "port2", "length (um)"]
    # Sort values in each row and create a new sorted column
    report["sorted_nodes"] = report.apply(
        lambda row: "".join(sorted([row["port1"], row["port2"]])), axis=1
    )

    # Drop duplicates based on the sorted column
    report = report.drop_duplicates("sorted_nodes").drop("sorted_nodes", axis=1)
    return report


def filter_path_report(report: pd.DataFrame, nodes: list[str]) -> pd.DataFrame:
    """
    Filter a DataFrame based on specified nodes in the 'port1' and 'port2' columns.

    Parameters:
    - report (pd.DataFrame): The input DataFrame containing a network report.
    - nodes (list[str]): A list of nodes to filter the DataFrame by.

    Returns:
    - pd.DataFrame: A filtered DataFrame containing rows where either 'port1' or 'port2' matches
        any node in the specified list.
    """
    return report[report["port1"].isin(nodes) & report["port2"].isin(nodes)]


def key_exist_dict(key: str, d: dict):
    """
    Checking if a specific key is exist in a dict

    Args:
        key (str): Dict key to be checked
        d (dict): Dict to check in
    Returns:
        val (str or list): contains value of the selected key
    """

    if key in d:
        return d[key]
    else:
        logging.error(f"There is no {key} parameter in the config file, please recheck")
        exit(1)


def path_length(
    gds_file: str,
    path_layer: dict[str, int],
    cutting_layer: dict[str, int],
    cell_name: str | None = None,
    nodes: list[str] = [],
) -> pd.DataFrame:
    """
    Calculate the shortest path lengths between cutting polygons on paths in a gds file.

    Parameters:
    - gds_file (str): The path to the gds file.
    - path_layer (tuple[int, int]): Layer number and dtype for paths.
    - cutting_layer (tuple[int, int]): Layer number and dtype for cutting regions.
    - cell_name (str, optional): Name of the cell. Defaults to None.
    - nodes (list[str], optional): list of node names to consider for path length report.

    Returns:
    pd.DataFrame: DataFrame containing information about shortest path lengths
    between cutting polygons. Columns include 'port1', 'port2', and 'length'.

    The function performs the following steps:
    1. Reads the gds file using gdstk.read_gds to obtain a gdstk.Library.
    2. Calls the get_polygons function to retrieve path and cutting polygons.
    3. Constructs a DataFrame with graph information using construct_graph_data_frame.
    4. Converts the DataFrame to a NetworkX graph using get_nx_graph.
    5. Generates a report of shortest path lengths between labels using get_paths_report.
    6. Returns the DataFrame containing path lengths.

    Example:
    ```
    gds_file_path = "path/to/your/file.gds"
    lengths_df = path_length(
        gds_file=gds_file_path,
        path_layer=(1,0),
        cutting_layer=(2,0),
        cell_name="example",
        nodes=['start','mid','stop']
    )
    ```
    """
    # Make sure that both path and cutting layer passed in proper format and make them as a list
    path_ly = [
        key_exist_dict("layer_no", path_layer),
        key_exist_dict("layer_dtype", path_layer),
    ]
    cut_ly = [
        key_exist_dict("layer_no", cutting_layer),
        key_exist_dict("layer_dtype", cutting_layer),
    ]
    # Reading input layout file
    if not os.path.isfile(gds_file):
        logging.error(f"{gds_file} file can't be found")
        exit(1)
    gdstk_lib = gdstk.read_gds(gds_file)
    # get path_polygons and cutting polygons
    path_polygons, cutting_polygons, labels = get_polygons(
        gdstk_lib=gdstk_lib,
        path_layer=path_ly,
        cutting_layer=cut_ly,
        cell_name=cell_name,
    )
    # get networkx graph
    df = construct_graph_data_frame(path_polygons, cutting_polygons, labels)
    graph = get_nx_graph(df)
    # generate report for all paths
    report = get_paths_report(graph)
    report_clean_df = report[report["length (um)"] > 0]
    # Filter out required ports only
    if nodes:
        return filter_path_report(report_clean_df, nodes)

    return report_clean_df
