#### Add license #####

"""Usage: path_length.py <config_file_path> [-h]

Arguments:
  <config_file_path>  Path to the config.yaml file.

Options:
  -h --help          Show this help message and exit.
"""


import gdstk
import logging
import os
from datetime import datetime
from time import time
from math import sqrt
from docopt import docopt
from yaml import safe_load
import pandas as pd
import networkx as nx
from functools import partial
from itertools import chain


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
        The area and perimeter are calculated using the gdstk library methods `area()` and `perimeter()`.
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
            f"area = {area}, perimeter = {perimeter}, negative value {discriminant} in sqrt detected"
        )
        raise ValueError(
            "Invalid input: No real solution for the length with the given area and perimeter"
        )

    return perimeter / 4 + sqrt(discriminant)


def get_polygons(
    gdstk_lib: gdstk.Library,
    path_layer: int,
    cutting_layer: int,
    cell_name: str | None = None,
    path_dtype: int = 0,
    cutting_dtype: int = 0,
) -> tuple[list[gdstk.Polygon], list[list[gdstk.Polygon]], list[list[gdstk.Label]]]:
    """
    Retrieve polygons representing paths and cutting regions based on input parameters.

    Parameters:
    - gdstk_lib (gdstk.Library): The gdstk.Library containing the desired cell.
    - path_layer (int): Layer number for paths.
    - cutting_layer (int): Layer number for cutting polygons.
    - cell_name (str, optional): Name of the cell. Defaults to None.
    - path_dtype (int, optional): Data type for paths. Defaults to 0.
    - cutting_dtype (int, optional): Data type for cutting regions. Defaults to 0.

    Returns:
    tuple: A tuple containing two elements.
        - List of path polygons (gdstk.Polygon).
        - List of dictionaries, where each dictionary represents cutting polygons
          corresponding to a path polygon. Keys are labels, and values are
          corresponding cutting polygons (dict[str, gdstk.Polygon]).

    The function performs the following steps:
    1. Calls _get_polygons to obtain path polygons, cutting polygons, and labels.
    2. Filters cutting polygons to include only those that intersect with path polygons.
    3. Filters labels based on whether their origin is inside cutting polygons.
    4. Creates a dictionary (polygon_labels_pairs) mapping labels to cutting polygons.
    5. Generates a list of dictionaries (cutting_polygons_per_path) representing cutting
       polygons for each path polygon.
    6. Returns the list of path polygons and cutting polygons per path.

    Example:
    ```
    path_polygons, cutting_polygons_per_path = get_polygons(
        gdstk_lib=my_library,
        path_layer=1,
        cutting_layer=2,
        cell_name="example",
        path_dtype=0,
        cutting_dtype=1
    )
    ```
    """
    path_polygons, cutting_polygons, labels = _get_polygons(
        gdstk_lib, path_layer, cutting_layer, cell_name, path_dtype, cutting_dtype
    )

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
    # logging.info(f"labels_as_list : {labels_text}")
    duplicate_labels = get_duplicates(labels_text)
    if duplicate_labels:
        logging.error(
            f"found duplicate labels {duplicate_labels}, please make sure to name your cutting polygons with a unique name"
        )
        exit(1)

    labels_points = [label.origin for label in labels]
    sorted_labels = []
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
            if check_if_polygon_cuts_path(polygon, [path_polygon]):
                if gdstk.inside([label.origin], polygon):
                    valid_cutting_polygons.append(polygon)
                    valid_cutting_labels.append(label)
        cutting_polygons_per_path.append(valid_cutting_polygons)
        cutting_labels_per_path.append(valid_cutting_labels)
    return path_polygons, cutting_polygons_per_path, cutting_labels_per_path


def get_duplicates(lst):
    seen = set()
    duplicates = []
    for item in lst:
        if item in seen:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def _get_polygons(
    gdstk_lib: gdstk.Library,
    path_layer: int,
    cutting_layer: int,
    cell_name: str | None = None,
    path_dtype: int = 0,
    cutting_dtype: int = 0,
) -> tuple[gdstk.Polygon, gdstk.Polygon, list[gdstk.Label]]:
    """
    Retrieve polygons representing paths and cutting regions from a gdstk.Library.

    Parameters:
    - gdstk_lib (gdstk.Library): The gdstk.library containing the desired cell.
    - path_layer (int): Layer number for paths.
    - cutting_layer (int): Layer number for cutting regions.
    - cell_name (str, optional): Name of the cell. Defaults to None.
    - path_dtype (int, optional): Data type for paths. Defaults to 0.
    - cutting_dtype (int, optional): Data type for cutting regions. Defaults to 0.

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

    Example:
    ```
    path_polygons, cutting_polygons, labels = _get_polygons(
        gdstk_lib=my_library,
        path_layer=1,
        cutting_layer=2,
        cell_name="example",
        path_dtype=0,
        cutting_dtype=1
    )
    ```
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

    path_polygons = cell.get_polygons(depth=None, layer=path_layer, datatype=path_dtype)
    path_polygons = gdstk.boolean(path_polygons, path_polygons, "or")
    cutting_polygons = cell.get_polygons(
        depth=None, layer=cutting_layer, datatype=cutting_dtype
    )
    labels = cell.get_labels(depth=None, layer=cutting_layer, texttype=cutting_dtype)
    return path_polygons, cutting_polygons, labels


def check_if_polygon_cuts_path(
    polygon: gdstk.Polygon, path_polygons: list[gdstk.Polygon]
) -> bool:
    """
    Check if a polygon cuts through a set of path polygons.

    Parameters:
    - polygon (gdstk.Polygon): The polygon to be checked for cutting through paths.
    - path_polygons (list[gdstk.Polygon]): List of path polygons to check against.

    Returns:
    bool: True if the given polygon cuts through any polygon of the set of path polygons, False otherwise.

    The function performs the following steps:
    1. Calculates the boolean operation 'not' between the given polygon and the set of path polygons.
    2. Returns True if the length of the result is 2, indicating that the polygon cuts through the paths.
       Otherwise, returns False.

    Example:
    ```
    is_cutting = check_if_polygon_cuts_path(
        polygon=my_polygon,
        path_polygons=[path1, path2, path3]
    )
    ```
    """
    return len(gdstk.boolean(polygon, path_polygons, "not")) == 2


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
    - cutting_polygons (list[dict[str, gdstk.Polygon]]): List of dictionaries,
      where each dictionary represents cutting polygons corresponding to a path polygon.
      Keys are labels, and values are corresponding cutting polygons.

    Returns:
    pd.DataFrame: DataFrame with columns 'node1', 'node2', and 'length' representing
    the graph data.

    The function performs the following steps:
    1. Iterates over path_polygons, cutting_polygons.items() to process each path and its cutting polygons.
    2. For each pair of adjacent cutting polygons, extracts node1, node2, and the length of the connecting segment.
    3. Appends records (node1, node2, length) to a list.
    4. Constructs a DataFrame from the list of records.
    5. Logs the resulting DataFrame for debugging purposes.
    6. Returns the constructed DataFrame.

    Example:
    ```
    graph_df = construct_graph_data_frame(
        path_polygons=[path1, path2, path3],
        cutting_polygons={
            "label1": cutting_poly1,
            "label2": cutting_poly2,
            "label3": cutting_poly3
        }
    )
    ```
    """
    records = []
    path_labels = move_labels_on_path(path_polygons, cutting_polygons, labels)
    logging.info(f"moved labels : {[label.text for label in path_labels]}")
    logging.info(f"{len(path_polygons),len(cutting_polygons),len(labels)}")
    for i, (poly, cutting_polys) in enumerate(zip(path_polygons, cutting_polygons)):
        logging.info(f"{i,len(cutting_polys),len(labels[i])}")
        tail_counter = 0
        if cutting_polys:
            splitted_polygons = split_polygon(poly, cutting_polys)
            logging.info(f"polygon counter{i}")
            logging.info(
                f"len splitted polygons :{len(split_polygon(poly, cutting_polys))} "
            )
            logging.info(f"len cutting polygons :{len(cutting_polys)} ")

            for sub_poly in splitted_polygons:
                logging.info("touch")
                node_names = get_node_names(sub_poly, path_labels)
                logging.info(f"node names {node_names}")
                if len(node_names) == 1:
                    node1 = node_names[0]
                    node2 = f"polygon_{i}_tail_{tail_counter}"
                    tail_counter += 1
                elif len(node_names) == 2:
                    node1, node2 = node_names
                else:
                    logging.error(f"node_names {node_names}")
                    continue
                length = get_length(sub_poly)
                logging.info(f"{[node1, node2, length]}")
                records.append([node1, node2, length])
    df = pd.DataFrame(records, columns=["node1", "node2", "length"])
    return df


def get_node_names(poly, labels: list[gdstk.Label]):
    points = [label.origin for label in labels]
    names = [label.text for label in labels]
    node_names: list[str] = []
    for name, condition in zip(names, gdstk.inside(points, poly)):
        if condition:
            node_names.append(name)
    logging.info(f"condition : {gdstk.inside(points, poly)}")
    logging.info(f"names: {names}")
    logging.info(f"points : {points}")

    return list(set(node_names))


def _min_max_labels(path: gdstk.Polygon, cutting_poly: gdstk.Polygon, text: str):
    points = gdstk.boolean(path, cutting_poly, "and")[0].points
    x_values, y_values = zip(*points)
    #logging.info(f"x: {x_values},\n  y:{y_values}")
    xmin = min(x_values)
    ymin = min(y_values)
    xmax = max(x_values)
    ymax = max(y_values)
    logging.info(f"xmin:{xmin},xmax:{xmax},ymin{ymin},ymax{ymax}")
    return [
        gdstk.Label(text, origin=point) for point in points
    ]


def move_labels_on_path(
    path_polygons: list[gdstk.Polygon],
    cutting_polygons: list[list[gdstk.Polygon]],
    labels: list[list[gdstk.Label]],
):
    moved_labels = []
    for path_poly, cutting_polys, labels in zip(
        path_polygons, cutting_polygons, labels
    ):
        get_min_max_labels = partial(_min_max_labels, path_poly)
        for poly, label in zip(cutting_polys, labels):
            moved_labels += get_min_max_labels(poly, label.text)
    return moved_labels


def get_nx_graph(graph_data_frame: pd.DataFrame) -> nx.Graph:
    """
    Create a NetworkX graph from a DataFrame containing edge information.
    Args:
        graph_data_frame (pd.DataFrame): A DataFrame with columns 'node1', 'node2', and 'length'
                                          representing edges and their corresponding lengths.
    Returns:
        nx.Graph: A NetworkX graph constructed from the provided DataFrame.
    Note:
        This function uses the `nx.from_pandas_edgelist` method to create a graph.
        The 'node1' and 'node2' columns of the DataFrame represent nodes,
        and the 'length' column is used as the edge attribute.
    Example:
        >>> data = {
        ...     'node1': ['a', 'b'],
        ...     'node2': ['b', 'c'],
        ...     'length': [1.0, 2.0]
        ... }
        >>> graph_df = pd.DataFrame(data)
        >>> graph = get_nx_graph(graph_df)
        >>> print(list(graph.edges(data=True)))
        [('a', 'b', {'length': 1.0}),
         ('b', 'c', {'length': 2.0})]
    """
    return nx.from_pandas_edgelist(graph_data_frame, "node1", "node2", "length")


def get_paths_report(graph: nx.Graph) -> pd.DataFrame:
    """
    Generate a report of shortest path lengths between all pairs of nodes in a graph.

    Parameters:
    - graph (nx.Graph): The input graph with weighted edges.

    Returns:
    pd.DataFrame: DataFrame containing information about shortest path lengths
    between all pairs of nodes. Columns include 'node1', 'node2', and 'length'.

    The function performs the following steps:
    1. Iterates over all pairs of nodes in the graph.
    2. Uses NetworkX's shortest_path_length to find the shortest path length between each pair,
       considering edge weights defined by the 'length' attribute.
    3. Handles cases where no path exists between nodes using a try-except block.
    4. Appends records (node1, node2, length) to a list.
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
    report = pd.DataFrame(records)
    report.columns = ["node1", "node2", "length"]
    # Sort values in each row and create a new sorted column
    report["sorted_nodes"] = report.apply(
        lambda row: "".join(sorted([row["node1"], row["node2"]])), axis=1
    )

    # Drop duplicates based on the sorted column
    report = report.drop_duplicates("sorted_nodes").drop("sorted_nodes", axis=1)
    return report


def path_length(
    gds_file: str,
    path_layer: int,
    cutting_layer: int,
    cell_name: str | None = None,
    path_dtype: int = 0,
    cutting_dtype: int = 0,
) -> pd.DataFrame:
    """
    Calculate the shortest path lengths between cutting polygons on paths in a gds file.

    Parameters:
    - gds_file (str): The path to the gds file.
    - path_layer (int): Layer number for paths.
    - cutting_layer (int): Layer number for cutting regions.
    - cell_name (str, optional): Name of the cell. Defaults to None.
    - path_dtype (int, optional): Data type for paths. Defaults to 0.
    - cutting_dtype (int, optional): Data type for cutting regions. Defaults to 0.

    Returns:
    pd.DataFrame: DataFrame containing information about shortest path lengths
    between cutting polygons. Columns include 'node1', 'node2', and 'length'.

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
        path_layer=1,
        cutting_layer=2,
        cell_name="example",
        path_dtype=0,
        cutting_dtype=1
    )
    ```
    """
    # read gds_lib
    # TODO : check gds_file_path exists
    gdstk_lib = gdstk.read_gds(gds_file)
    # get path_polygons and cutting polygons
    path_polygons, cutting_polygons, labels = get_polygons(
        gdstk_lib=gdstk_lib,
        path_layer=path_layer,
        cutting_layer=cutting_layer,
        cell_name=cell_name,
        path_dtype=path_dtype,
        cutting_dtype=cutting_dtype,
    )
    # get networkx graph
    df = construct_graph_data_frame(path_polygons, cutting_polygons, labels)
    graph = get_nx_graph(df)
    # generate report for all paths
    report = get_paths_report(graph)
    return report


if __name__ == "__main__":
    args = docopt(__doc__)
    config_file_path = args["<config_file_path>"]
    if not os.path.isfile(config_file_path):
        logging.error(f"{config_file_path} file can't be found")
        exit(1)

    try:
        with open(config_file_path) as f:
            config_data = safe_load(f)
    except Exception as e:
        logging.error(
            f"failed to read config file  {config_file_path}, \n Error messege: {e} "
        )
        exit(1)

    if not os.path.exists("logs/"):
        os.mkdir("logs/")

    now_str = datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(
                f"logs/{config_data['gds_file'].split('/')[-1].split('.')[0]}_{now_str}.log"
            ),
            logging.StreamHandler(),
        ],
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%d-%b-%Y %H:%M:%S",
    )
    logging.getLogger()

    time_start = time()
    path_length_report = path_length(**config_data)
    logging.info(f"path_length_report: \n {path_length_report}")
    exc_time = time() - time_start
    logging.info(f"Execution time: {exc_time} sec")
