#### Add license #####
import gdstk
import logging
import os
from datetime import datetime
from time import time
from math import sqrt
from functools import partial
import pandas as pd
import networkx as nx


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
    gdstk_lib: gdstk.Library, layer: int, datatype: int = 0
) -> list[gdstk.Polygon]:
    """
    Extract polygons from the top-level cells of a gdstk library with specific layer and datatype.

    Args:
        gdstk_lib (gdstk.Library): The GDS library containing the cells.
        layer (int): The layer of the polygons to extract.
        datatype (int, optional): The datatype of the polygons (default is 0).

    Returns:
        list[gdstk.Polygon]: A list of gdstk.Polygon objects extracted from the specified layer and datatype.

    Note:
        The function iterates through the top-level cells of the gdstk_lib library,
        flattens each cell to obtain all polygons within it, and filters polygons
        based on the specified layer and datatype.

    Example:
        >>> gds_library = gdstk.read_gds(gds_file_path)
        >>> layer_number = 10
        >>> datatype_number = 0
        >>> polygons = get_polygons(gds_library, layer=layer_number, datatype=datatype_number)
    """
    path_polygons: list[gdstk.Polygon] = []
    for cell in gdstk_lib.top_level():
        path_polygons += cell.get_polygons(layer=layer, datatype=datatype)

    merged_polygons = gdstk.boolean(path_polygons, path_polygons, "or")
    logging.info(
        f"number of top_cells = {len(gdstk_lib.top_level())}, number of polygons = {len(path_polygons)}, number of polygons after merge = {len(merged_polygons)} "
    )
    return merged_polygons


def get_polygon_label_pair(
    gdstk_lib: gdstk.Library, layer: int, datatype: int = 0
) -> dict[str, gdstk.Polygon]:
    """
    Extracts polygons and corresponding labels from the top-level cells in a GDSTk library.

    Args:
    - gdstk_lib (gdstk.Library): The GDSTk library containing the cells.
    - layer (int): The layer of interest for polygon extraction.
    - datatype (int, optional): The datatype of interest for polygon extraction. Defaults to 0.

    Returns:
    dict[str, gdstk.Polygon]: A dictionary mapping labels to their corresponding polygons.

    Note:
    - The function assumes that each cell in the library has unique labels.
    """

    polygon_labels_pairs: dict[str, gdstk.Polygon] = {}
    polygons: list[gdstk.Polygon] = []
    labels: list[gdstk.Label] = []
    for cell in gdstk_lib.top_level():
        polygons += cell.get_polygons(layer=layer, datatype=datatype)
        labels += cell.get_labels(layer=layer, texttype=datatype)
    for poly, label in zip(polygons, labels):
        polygon_labels_pairs[label.text] = poly
    return polygon_labels_pairs


def split_polygon(
    poly: gdstk.Polygon, ports: dict[gdstk.Label, gdstk.Polygon]
) -> gdstk.Polygon:
    """
    Split a polygon using boolean operations with a list of ports.

    Args:
        poly (gdstk.Polygon): The input polygon to be split.
        ports (list[gdstk.Polygon]): A list of polygons representing ports used for splitting polygon.

    Returns:
        gdstk.Polygon: The resulting polygon after the split operation.

    """
    return gdstk.boolean(poly, list(ports.values()), "not")


def construct_graph_data_frame(
    polygons: list[list[gdstk.Polygon]],
) -> pd.DataFrame:
    """
    Construct a DataFrame representing a graph from a list of polygons splitted in a list.

    Args:
        polygons (list[list[gdstk.Polygon]]): A list of lists, where each inner list contains gdstk.Polygon objects.

    Returns:
        pd.DataFrame: A DataFrame representing the graph with columns "node1", "node2", and "length".

    Note:
        This function iterates through the nested list of polygons, calculates the length
        between consecutive nodes in each polygon using the `get_length` function,
        and constructs a DataFrame with columns "node1", "node2", and "length".

    Example:
        >>> poly0 = [gdstk.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]), gdstk.Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]
        >>> poly1 = [gdstk.Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]), gdstk.Polygon([(1, 0), (2, 0), (2, 1), (1, 1)])]
        >>> polygons = [poly0, poly1]
        >>> graph_df = construct_graph_data_frame(polygons)
        >>> print(graph_df)
              node1           node2       length
        0  poly_0_node_0  poly_0_node_1     1.0
        1  poly_0_node_1  poly_0_node_2     1.0
        3  poly_1_node_0  poly_1_node_1     1.0
        4  poly_1_node_1  poly_1_node_2     1.0
    """
    records = []
    for i, poly in enumerate(polygons):
        for node, sub_poly in enumerate(poly):
            node1 = f"poly_{i}_node_{node}"
            node2 = f"poly_{i}_node_{node+1}"
            length = get_length(sub_poly)
            records.append([node1, node2, length])
    df = pd.DataFrame(records, columns=["node1", "node2", "length"])
    return df


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
        ...     'node1': ['poly_0_node_0', 'poly_0_node_1'],
        ...     'node2': ['poly_0_node_1', 'poly_0_node_2'],
        ...     'length': [1.0, 2.0]
        ... }
        >>> graph_df = pd.DataFrame(data)
        >>> graph = get_nx_graph(graph_df)
        >>> print(list(graph.edges(data=True)))
        [('poly_0_node_0', 'poly_0_node_1', {'length': 1.0}),
         ('poly_0_node_1', 'poly_0_node_2', {'length': 2.0})]
    """
    return nx.from_pandas_edgelist(graph_data_frame, "node1", "node2", "length")


def _get_path_length_from_edges(
    path_edges: list[tuple[str, str, dict[str, float]]]
) -> float:
    """
    Calculate the total length of a path based on path edges.

    Args:
        path_edges (list[tuple[str, str, dict[str, float]]]):
            A list of tuples representing edges in the path.
            Each tuple contains source node, target node, and a dictionary with the 'length' attribute.

    Returns:
        float: The total length of the specified path.

    Example:
        >>> edges = [('A', 'B', {'length': 1.0}), ('B', 'C', {'length': 2.0}), ('C', 'D', {'length': 3.0})]
        >>> result = _get_path_length_from_graph_data(edges)
        >>> print(result)
        6.0
    """
    path_length = 0
    for edge in path_edges:
        path_length += edge[2]["length"]
    return path_length


def get_path_length(graph: nx.Graph, start_node: str, end_node: str) -> float:
    """
    Calculate the total length of the shortest path between two nodes in a NetworkX graph.

    Args:
        graph (nx.Graph): The input graph.
        start_node (str): The starting node.
        end_node (str): The ending node.

    Returns:
        float: The total length of the shortest path between the specified nodes.

    Raises:
        nx.NetworkXNoPath: If there is no path between the specified nodes.

    Example:
        >>> G = nx.Graph()
        >>> G.add_edge('A', 'B', length=1.0)
        >>> G.add_edge('B', 'C', length=2.0)
        >>> G.add_edge('C', 'D', length=3.0)
        >>> result = get_path_length(G, 'A', 'D')
        >>> print(result)
        6.0
    """
    return nx.shortest_path_length(graph, start_node, end_node, "length")


def main() -> None:
    # example_path = "gds_examples/inverter.gds"
    example_path = "gds_examples/test.gds"
    path_layer = 174
    cutting_layer = 1000
    gds_lib = gdstk.read_gds(example_path)
    # get polygons in path_layer
    path_polygons = get_polygons(gds_lib, layer=path_layer)
    # get polygons in cutting layer
    # ports_polygons = get_polygons(gds_lib, layer=cutting_layer)
    polygon_labels_pairs = get_polygon_label_pair(gds_lib, cutting_layer)
    # split polygons using cutting layer polygons
    splitted_polygons = list(
        map(partial(split_polygon, ports=polygon_labels_pairs), path_polygons)
    )
    # logging.info(splitted_polygons)
    # prepare nx graph data_frame
    graph_data_frame = construct_graph_data_frame(splitted_polygons)
    logging.info(f"graph_data_frame : \n {graph_data_frame}")
    # get nx graph from dataframe
    path_length_graph = get_nx_graph(graph_data_frame)
    logging.info(f"graph edges : {path_length_graph.edges}")
    # solve graph for shorted path using start and end nodes
    start_node, end_node = "poly_0_node_1", "poly_0_node_2"
    path_length = get_path_length(path_length_graph, start_node, end_node)
    logging.info(f"path_length : {path_length}")


if __name__ == "__main__":
    if not os.path.exists("logs/"):
        os.mkdir("logs/")

    now_str = datetime.utcnow().strftime("op_tests_%Y_%m_%d_%H_%M_%S")
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(f"logs/{now_str}.log"),
            logging.StreamHandler(),
        ],
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%d-%b-%Y %H:%M:%S",
    )
    logging.getLogger()

    time_start = time()
    main()
    exc_time = time() - time_start
    logging.info(f"tests Execution time: {exc_time} sec")
