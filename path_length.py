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
from functools import partial
from docopt import docopt
from yaml import safe_load


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
) -> list[gdstk.Polygon]:
    """
    Split a polygon using boolean operations with a list of ports.

    Args:
        poly (gdstk.Polygon): The input polygon to be split.
        ports (list[gdstk.Polygon]): A list of polygons representing ports used for splitting polygon.

    Returns:
        list[gdstk.Polygon]: The resulting polygons after the split operation.

    """
    return gdstk.boolean(poly, list(ports.values()), "not")


def get_path_length(splitted_polygons: list[gdstk.Polygon]) -> float | None:
    """
    Calculate and return the length of a path based on the given list of polygons.

    Parameters:
    - splitted_polygons (list[gdstk.Polygon]): List of polygons representing the path after cutting.

    Returns:
    - float | None: The length of the path if valid, otherwise None.

    Note:
    - If len(splitted_polygons) == 3, this indicates that two ports cut the path polygon,
      and the desired path length is get_length(splitted_polygons[1]).
    - If len(splitted_polygons) > 3, this indicates an invalid cut.
      Also, if len(splitted_polygons) == 2, this indicates an invalid cut.
    - If len(splitted_polygons) == 1, this indicates that this path is out of the cutting layer scope.
    """
    if len(splitted_polygons) == 1:
        logging.info("This polygon path has no cuts")
    elif len(splitted_polygons) == 3:
        path_length = get_length(splitted_polygons[1])
        logging.info(f"Valid cut,  \n  path_length : {path_length}")
        return path_length
    else:
        logging.info("Invalid cut")


def path_length(
    gds_file: str,
    path_layer: int,
    cutting_layer: int,
    path_dtype: int = 0,
    cutting_dtype: int = 0,
) -> list[float]:
    gds_lib = gdstk.read_gds(gds_file)
    path_polygons = get_polygons(gds_lib, layer=path_layer, datatype=path_dtype)
    # get polygons in cutting layer
    polygon_labels_pairs = get_polygon_label_pair(
        gds_lib, cutting_layer, datatype=cutting_dtype
    )
    # split polygons using cutting layer polygons
    splitted_polygons = list(
        map(partial(split_polygon, ports=polygon_labels_pairs), path_polygons)
    )
    path_length = list(map(get_path_length, splitted_polygons))
    logging.info(f"path_length : \n {path_length}")
    return [length for length in path_length if length is not None]


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
    valid_path_lengths = path_length(**config_data)
    logging.info(f"valid_path_lengths: \n {valid_path_lengths}")
    exc_time = time() - time_start
    logging.info(f"tests Execution time: {exc_time} sec")
