"""Functions for finding distances between points, areas or states.

    Typical usage example:

    from awpy.analytics.nav import area_distance

    geodesic_dist = area_distance(map_name="de_dust2", area_a=152, area_b=8970, dist_type="geodesic")
    f, ax = plot_map(map_name = "de_dust2", map_type = 'simpleradar', dark = True)

    for a in NAV["de_dust2"]:
        area = NAV["de_dust2"][a]
        color = "None"
        if a in geodesic_dist["areas"]:
            color = "red"
        width = (area["southEastX"] - area["northWestX"])
        height = (area["northWestY"] - area["southEastY"])
        southwest_x = area["northWestX"]
        southwest_y = area["southEastY"]
        rect = patches.Rectangle((southwest_x,southwest_y), width, height, linewidth=1, edgecolor="yellow", facecolor=color)
        ax.add_patch(rect)

    https://github.com/pnxenopoulos/awpy/blob/main/examples/03_Working_with_Navigation_Meshes.ipynb
"""
import sys
import itertools
from collections import defaultdict
from statistics import mean, median
import math
import json
from sympy.utilities.iterables import multiset_permutations
import networkx as nx
import numpy as np
from awpy.data import NAV, NAV_GRAPHS, AREA_DIST_MATRIX, PLACE_DIST_MATRIX, PATH
from scipy.spatial import distance
from shapely.geometry import Polygon
from numpy import array
from numpy.linalg import norm

def point_in_area(map_name, area_id, point):
    """Returns if the point is within a nav area for a map.

    Args:
        map_name (string): Map to search
        area_id (int): Area ID as an integer
        point (list): Point as a list [x,y,z]

    Returns:
        True if area contains the point, false if not
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if area_id not in NAV[map_name].keys():
        raise ValueError("Area ID not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    contains_x = (
        min(NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"])
        < point[0]
        < max(
            NAV[map_name][area_id]["northWestX"], NAV[map_name][area_id]["southEastX"]
        )
    )
    contains_y = (
        min(NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"])
        < point[1]
        < max(
            NAV[map_name][area_id]["northWestY"], NAV[map_name][area_id]["southEastY"]
        )
    )
    if contains_x and contains_y:
        return True
    else:
        return False


def find_closest_area(map_name, point):
    """Finds the closest area in the nav mesh. Searches through all the areas by comparing point to area centerpoint.

    Args:
        map_name (string): Map to search
        point (list): Point as a list [x,y,z]

    Returns:
        A dict containing info on the closest area
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if len(point) != 3:
        raise ValueError("Point must be a list [X,Y,Z]")
    closest_area = {"mapName": map_name, "areaId": None, "distance": 999999}
    for area in NAV[map_name].keys():
        avg_x = (
            NAV[map_name][area]["northWestX"] + NAV[map_name][area]["southEastX"]
        ) / 2
        avg_y = (
            NAV[map_name][area]["northWestY"] + NAV[map_name][area]["southEastY"]
        ) / 2
        avg_z = (
            NAV[map_name][area]["northWestZ"] + NAV[map_name][area]["southEastZ"]
        ) / 2
        dist = np.sqrt(
            (point[0] - avg_x) ** 2 + (point[1] - avg_y) ** 2 + (point[2] - avg_z) ** 2
        )
        if dist < closest_area["distance"]:
            closest_area["areaId"] = area
            closest_area["distance"] = dist
    return closest_area


def area_distance(map_name, area_a, area_b, dist_type="graph"):
    """Returns the distance between two areas. Dist type can be graph or geodesic.

    Args:
        map_name (string): Map to search
        area_a (int): Area id
        area_b (int): Area id
        dist_type (string): String indicating the type of distance to use (graph, geodesic or euclidean)

    Returns:
        A dict containing info on the path between two areas.
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if (area_a not in NAV[map_name].keys()) or (area_b not in NAV[map_name].keys()):
        raise ValueError("Area ID not found.")
    if dist_type not in ["graph", "geodesic", "euclidean"]:
        raise ValueError("dist_type can only be graph, geodesic or euclidean")
    G = NAV_GRAPHS[map_name]
    distance_obj = {"distanceType": dist_type, "distance": None, "areas": []}
    if dist_type == "graph":
        try:
            discovered_path = nx.shortest_path(G, area_a, area_b)
            distance_obj["distance"] = len(discovered_path) - 1
            distance_obj["areas"] = discovered_path
        except nx.NetworkXNoPath:
            distance_obj["distance"] = float("inf")
            distance_obj["areas"] = []
        return distance_obj
    if dist_type == "geodesic":

        def dist_heuristic(a, b):
            return distance.euclidean(G.nodes()[a]["center"], G.nodes()[b]["center"])

        try:
            geodesic_path = nx.astar_path(
                G, area_a, area_b, heuristic=dist_heuristic, weight="weight"
            )
            geodesic_cost = sum(
                G[u][v]["weight"] for u, v in zip(geodesic_path[:-1], geodesic_path[1:])
            )
            distance_obj["distance"] = geodesic_cost
            distance_obj["areas"] = geodesic_path
        except nx.NetworkXNoPath:
            distance_obj["distance"] = float("inf")
            distance_obj["areas"] = []
        return distance_obj
    if dist_type == "euclidean":
        c = NAV[map_name][area_a]
        d = lambda a, b : (c[a] + c[b]) / 2
        e = (("southEastX", "northWestX"),\
             ("southEastY", "northWestY"),\
             ("southEastZ", "northWestZ"))
        f = lambda c : array(tuple(d(a, b) for a, b in e)) 
        area_a = f(c)     
        c = NAV[map_name][area_b]
        area_b = f(c)                    
        distance_obj["distance"] = norm(area_a - area_b)        
        return distance_obj


def point_distance(map_name, point_a, point_b, dist_type="graph"):
    """Returns the distance between two points.

    Args:
        map_name (string): Map to search
        point_a (list): Point as a list (x,y,z)
        point_b (list): Point as a list (x,y,z)
        dist_type (string): String indicating the type of distance to use. Can be graph, geodesic, euclidean, manhattan, canberra or cosine.

    Returns:
        A dict containing info on the distance between two points.
    """
    distance_obj = {"distanceType": dist_type, "distance": None, "areas": []}
    if dist_type == "graph":
        if map_name not in NAV:
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError(
                "When using graph or geodesic distance, point must be X/Y/Z"
            )
        area_a = find_closest_area(map_name, point_a)["areaId"]
        area_b = find_closest_area(map_name, point_b)["areaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "geodesic":
        if map_name not in NAV:
            raise ValueError("Map not found.")
        if len(point_a) != 3 or len(point_b) != 3:
            raise ValueError(
                "When using graph or geodesic distance, point must be X/Y/Z"
            )
        area_a = find_closest_area(map_name, point_a)["areaId"]
        area_b = find_closest_area(map_name, point_b)["areaId"]
        return area_distance(map_name, area_a, area_b, dist_type=dist_type)
    elif dist_type == "euclidean":
        distance_obj["distance"] = distance.euclidean(point_a, point_b)
        return distance_obj
    elif dist_type == "manhattan":
        distance_obj["distance"] = distance.cityblock(point_a, point_b)
        return distance_obj
    elif dist_type == "canberra":
        distance_obj["distance"] = distance.canberra(point_a, point_b)
        return distance_obj
    elif dist_type == "cosine":
        distance_obj["distance"] = distance.cosine(point_a, point_b)
        return distance_obj


def generate_position_token(map_name, frame):
    """Generates the position token for a game frame.

    Args:
        map_name (string): Map to search
        frame (dict): A game frame

    Returns:
        A dict containing the T token, CT token and combined token (T + CT concatenated)
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if (len(frame["ct"]["players"]) == 0) or (len(frame["t"]["players"]) == 0):
        raise ValueError("CT or T players has length of 0")
    # Create map area list
    map_area_names = []
    for area_id in NAV[map_name]:
        if NAV[map_name][area_id]["areaName"] not in map_area_names:
            map_area_names.append(NAV[map_name][area_id]["areaName"])
    map_area_names.sort()
    # Create token
    ct_token = np.zeros(len(map_area_names), dtype=np.int8)
    for player in frame["ct"]["players"]:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            ct_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    t_token = np.zeros(len(map_area_names), dtype=np.int8)
    for player in frame["t"]["players"]:
        if player["isAlive"]:
            closest_area = find_closest_area(
                map_name, [player["x"], player["y"], player["z"]]
            )
            t_token[
                map_area_names.index(NAV[map_name][closest_area["areaId"]]["areaName"])
            ] += 1
    # Create payload
    token = {}
    token["tToken"] = (
        str(t_token).replace("'", "").replace("[", "").replace("]", "").replace(" ", "")
    )
    token["ctToken"] = (
        str(ct_token)
        .replace("'", "")
        .replace("[", "")
        .replace("]", "")
        .replace(" ", "")
    )
    token["token"] = token["ctToken"] + token["tToken"]
    return token


def tree():
    """Builds tree data structure from nested defaultdicts

    Args:
        None

    Returns:
        An empty tree"""

    def the_tree():
        return defaultdict(the_tree)

    return the_tree()


def generate_area_distance_matrix(map_name, save=False):
    """Generates or grabs a tree like nested dictionary containing distance matrices (as dicts) for each map for all area
    Structures is [map_name][area1id][area2id][dist_type(euclidean,graph,geodesic)]

    Args:
        map_name (string): Map to generate the place matrix for
        save (boolean): Whether to save the matrix to file

    Returns:
        Tree structure containing distances for all area pairs on all maps
    """
    # Initialize the dict structure
    area_distance_matrix = tree()
    if map_name not in NAV:
        raise ValueError("Map not found.")
    areas = NAV[map_name]
    # And there over each area
    for area1 in areas:
        # Precompute the tile center
        area1 = int(area1)
        area1_x = (
            NAV[map_name][area1]["southEastX"] + NAV[map_name][area1]["northWestX"]
        ) / 2
        area1_y = (
            NAV[map_name][area1]["southEastY"] + NAV[map_name][area1]["northWestY"]
        ) / 2
        area1_z = (
            NAV[map_name][area1]["southEastZ"] + NAV[map_name][area1]["northWestZ"]
        ) / 2
        # Loop over every pair of areas
        for area2 in areas:
            area2 = int(area2)
            # # Compute center of second area
            area2_x = (
                NAV[map_name][area2]["southEastX"] + NAV[map_name][area2]["northWestX"]
            ) / 2
            area2_y = (
                NAV[map_name][area2]["southEastY"] + NAV[map_name][area2]["northWestY"]
            ) / 2
            area2_z = (
                NAV[map_name][area2]["southEastZ"] + NAV[map_name][area2]["northWestZ"]
            ) / 2
            # Calculate basic euclidean distance
            area_distance_matrix[area1][area2]["euclidean"] = math.sqrt(
                (area1_x - area2_x) ** 2
                + (area1_y - area2_y) ** 2
                + (area1_z - area2_z) ** 2
            )
            # Also get graph distance
            graph = area_distance(map_name, area1, area2, dist_type="graph")
            area_distance_matrix[area1][area2]["graph"] = graph["distance"]
            # And geodesic like distance
            geodesic = area_distance(map_name, area1, area2, dist_type="geodesic")
            area_distance_matrix[area1][area2]["geodesic"] = geodesic["distance"]
    if save:
        with open(
            PATH + f"nav/area_distance_matrix_{map_name}.json", "w", encoding="utf8"
        ) as json_file:
            json.dump(area_distance_matrix, json_file)
    return area_distance_matrix


def generate_place_distance_matrix(map_name, save=False):
    """Generates or grabs a tree like nested dictionary containing distance matrices (as dicts) for each map for all regions
    Structures is [map_name][placeid][place2id][dist_type(euclidean,graph,geodesic)][reference_point(centroid,representative_point,median)]

    Args:
        map_name (string): Map to generate the place matrix for
        save (boolean): Whether to save the matrix to file

    Returns:
        Tree structure containing distances for all place pairs on all maps
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    areas = NAV[map_name]
    place_distance_matrix = tree()
    # Loop over all three considered distance types
    for dist_type in ["geodesic", "graph", "euclidean"]:
        # Get the mapping "areaName": [areas that have this area name]
        area_mapping = defaultdict(list)
        for area in areas:
            area_mapping[areas[area]["areaName"]].append(area)
        # Get the centroids and representative points for each named place on the map
        centroids, reps = generate_centroids(map_name)
        # Loop over all pairs of named places
        for place1, centroid1 in centroids.items():
            for place2, centroid2 in centroids.items():
                # If precomputed values do not exist calculate them
                if AREA_DIST_MATRIX is None or map_name not in AREA_DIST_MATRIX:
                    # Distances between the centroids for each named place
                    place_distance_matrix[place1][place2][dist_type][
                        "centroid"
                    ] = area_distance(
                        map_name, centroid1, centroid2, dist_type=dist_type
                    )[
                        "distance"
                    ]
                    # Distances between the representative points for each named place
                    place_distance_matrix[place1][place2][dist_type][
                        "representative_point"
                    ] = area_distance(
                        map_name, reps[place1], reps[place2], dist_type=dist_type
                    )[
                        "distance"
                    ]
                    # Median of all the distance pairs for areaA in place1 to areaB in place2
                    connections = []
                    for sub_area1 in area_mapping[place1]:
                        for sub_area2 in area_mapping[place2]:
                            connections.append(
                                area_distance(
                                    map_name,
                                    sub_area1,
                                    sub_area2,
                                    dist_type=dist_type,
                                )["distance"]
                            )
                    place_distance_matrix[place1][place2][dist_type][
                        "median_dist"
                    ] = median(connections)
                # If precomputed values exist just grab those
                else:
                    place_distance_matrix[place1][place2][dist_type][
                        "centroid"
                    ] = AREA_DIST_MATRIX[map_name][str(centroid1)][str(centroid2)][
                        dist_type
                    ]
                    place_distance_matrix[place1][place2][dist_type][
                        "representative_point"
                    ] = AREA_DIST_MATRIX[map_name][str(reps[place1])][
                        str(reps[place2])
                    ][
                        dist_type
                    ]
                    connections = []
                    for sub_area1 in area_mapping[place1]:
                        for sub_area2 in area_mapping[place2]:
                            connections.append(
                                AREA_DIST_MATRIX[map_name][str(sub_area1)][
                                    str(sub_area2)
                                ][dist_type]
                            )
                    place_distance_matrix[place1][place2][dist_type][
                        "median_dist"
                    ] = median(connections)
    if save:
        with open(
            PATH + f"nav/place_distance_matrix_{map_name}.json", "w", encoding="utf8"
        ) as json_file:
            json.dump(place_distance_matrix, json_file)
    return place_distance_matrix


def generate_centroids(map_name):
    """For each region in the given map calculates the centroid and a representative point and finds the closest tile for each

    Args:
        map_name (string): Name of the map for which to calculate the centroids

    Returns:
        Tuple of dictionaries containing the centroid and representative tiles for each region of the map
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    area_points = defaultdict(list)
    z_s = defaultdict(list)
    area_ids_cent = {}
    area_ids_rep = {}
    for a in NAV[map_name]:
        area = NAV[map_name][a]
        cur_x = []
        cur_y = []
        cur_x.append(area["southEastX"])
        cur_x.append(area["northWestX"])
        cur_y.append(area["southEastY"])
        cur_y.append(area["northWestY"])
        # Get the z coordinates for each tile of a named area
        z_s[area["areaName"]].append(area["northWestZ"])
        z_s[area["areaName"]].append(area["southEastZ"])
        # Get all the (x,y) points that make up each tile of a named area
        for x, y in itertools.product(cur_x, cur_y):
            area_points[area["areaName"]].append((x, y))
    # For each named area
    for area in area_points:
        # Get the (approximate) orthogonal convex hull
        hull = np.array(stepped_hull(area_points[area]))
        # Get the centroids and rep. point of the hull
        my_centroid = list(np.array(Polygon(hull).centroid.coords)[0]) + [
            mean(z_s[area])
        ]
        rep_point = list(np.array(Polygon(hull).representative_point().coords)[0]) + [
            mean(z_s[area])
        ]
        # Find the closest tile for these points
        area_ids_cent[area] = find_closest_area(map_name, my_centroid)["areaId"]
        area_ids_rep[area] = find_closest_area(map_name, rep_point)["areaId"]
    return area_ids_cent, area_ids_rep


def stepped_hull(points):
    """Takes a set of points and produces an approximation of their orthogonal convex hull

    Args:
        points (list): A list of points given as tuples (x, y)

    Returns:
        A list of points making up the hull or four lists of points making up the four quadrants of the hull"""
    # May be equivalent to the orthogonal convex hull

    points = sorted(set(points))

    if len(points) <= 1:
        return points

    # Get extreme y points
    min_y = min(points, key=lambda p: p[1])
    max_y = max(points, key=lambda p: p[1])

    # Create upper section
    upper_left = build_stepped_upper(
        sorted(points, key=lambda tup: (tup[0], tup[1])), max_y
    )
    upper_right = build_stepped_upper(
        sorted(points, key=lambda tup: (-tup[0], tup[1])), max_y
    )

    # Create lower section
    lower_left = build_stepped_lower(
        sorted(points, key=lambda tup: (tup[0], -tup[1])), min_y
    )
    lower_right = build_stepped_lower(
        sorted(points, key=lambda tup: (-tup[0], -tup[1])), min_y
    )

    # Correct the ordering
    lower_right.reverse()
    upper_left.reverse()

    # Remove duplicate points
    hull = list(dict.fromkeys(lower_left + lower_right + upper_right + upper_left))
    hull.append(hull[0])
    return hull


def build_stepped_upper(points, max_y):
    """Builds builds towards the upper part of the hull based on starting point and maximum y value.

    Args:
        points (list): A list of points to build the upper left hull section from
        max_y (float): The point with the highest y

    Returns:
        A list of points making up the upper part of the hull"""
    # Steps towards the highest y point

    section = [points[0]]

    if max_y != points[0]:
        for point in points:
            if point[1] >= section[-1][1]:
                section.append(point)
            if max_y == point:
                break
    return section


def build_stepped_lower(points, min_y):
    """Builds builds towards the lower part of the hull based on starting point and maximum y value.

    Args:
        points (list): A list of points to build the upper left hull section from
        min_y (float): The point with the lowest y

    Returns:
        A list of points making up the lower part of the hull"""
    # Steps towards the lowest y point

    section = [points[0]]

    if min_y != points[1]:
        for point in points:
            if point[1] <= section[-1][1]:
                section.append(point)

            if min_y == point:
                break
    return section


def position_state_distance(
    map_name,
    position_array_1,
    position_array_2,
    distance_type="geodesic",
):
    """Calculates a distance between two game states based on player positions

    Args:
        map_name (string): Map to search
        position_array_1 (numpy array): Numpy array with shape (2|1, 5, 3) with the first index indicating the team, the second the player and the third the coordinate
        position_array_2 (numpy array): Numpy array with shape (2|1, 5, 3) with the first index indicating the team, the second the player and the third the coordinate
        distance_type (string): String indicating how the distance between two player positions should be calculated. Options are "geodesic", "graph" and "euclidean"

    Returns:
        A float representing the distance between these two game states
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if distance_type not in ["graph", "geodesic", "euclidean"]:
        raise ValueError("distance_type can only be graph, geodesic or euclidean")
    pos_distance = 0
    if (
        position_array_1.shape[0] != position_array_2.shape[0]
        or position_array_1.shape[2] != position_array_2.shape[2]
    ):
        raise ValueError(
            "Game state shapes do not match! Both states have to have the same number of teams(1 or 2) and same number of coordinates (3)."
        )
    if distance_type not in ["geodesic", "graph"] and position_array_1.shape[2] != 3:
        raise ValueError(
            "Game state shapes do not match! Both states have to have the same number of teams(1 or 2) and same number of coordinates (3)."
        )
    # Make sure array1 is the one with more players alive
    if position_array_1.shape[1] < position_array_2.shape[1]:
        position_array_1, position_array_2 = position_array_2, position_array_1
    # Pre compute the area names for each player's position
    if distance_type in ["geodesic", "graph"] and position_array_1.shape[-1] == 3:
        areas = {1: defaultdict(dict), 2: defaultdict(dict)}
        for team in range(position_array_1.shape[0]):
            for player in range(position_array_1.shape[1]):
                areas[1][team][player] = find_closest_area(
                    map_name, position_array_1[team][player]
                )["areaId"]
        for team in range(position_array_2.shape[0]):
            for player in range(position_array_2.shape[1]):
                areas[2][team][player] = find_closest_area(
                    map_name, position_array_2[team][player]
                )["areaId"]
    # Get the minimum mapping distance for each side separately
    for team in range(position_array_1.shape[0]):
        side_distance = float("inf")
        # Generate all possible mappings between players from array1 and array2. (Map player1 from array1 to player1 from array2 and player2's to each other or match player1's with player2's and so on)
        for mapping in itertools.permutations(
            range(position_array_1.shape[1]), position_array_2.shape[1]
        ):
            # Distance team distance for the current mapping
            cur_dist = 0
            # Calculate the distance between each pair of players in the current mapping
            for player2, player1 in enumerate(mapping):
                # Just take euclidian distance between the two players. Fast but ignores walls
                if distance_type == "euclidean":
                    this_dist = math.sqrt(
                        (
                            position_array_1[team][player1][0]
                            - position_array_2[team][player2][0]
                        )
                        ** 2
                        + (
                            position_array_1[team][player1][1]
                            - position_array_2[team][player2][1]
                        )
                        ** 2
                        + (
                            position_array_1[team][player1][2]
                            - position_array_2[team][player2][2]
                        )
                        ** 2
                    )
                # Use a more accurate graph based distance that takes into account the actual map
                elif distance_type in ["geodesic", "graph"]:
                    # The underlying graph is directed (There is a short path to drop down a ledge but a long one is needed to get back up)
                    # So calculate both possible values and take the minimum one so that the distance between two states/trajectories is commutative
                    area1 = (
                        areas[1][team][player1]
                        if position_array_1.shape[-1] == 3
                        else int(position_array_1[team][player1][0])
                    )
                    area2 = (
                        areas[2][team][player2]
                        if position_array_2.shape[-1] == 3
                        else int(position_array_2[team][player2][0])
                    )
                    if AREA_DIST_MATRIX is None or map_name not in AREA_DIST_MATRIX:
                        this_dist = min(
                            area_distance(
                                map_name,
                                area1,
                                area2,
                                dist_type=distance_type,
                            )["distance"],
                            area_distance(
                                map_name,
                                area2,
                                area1,
                                dist_type=distance_type,
                            )["distance"],
                        )
                    else:
                        this_dist = min(
                            AREA_DIST_MATRIX[map_name][str(area1)][str(area2)][
                                distance_type
                            ],
                            AREA_DIST_MATRIX[map_name][str(area2)][str(area1)][
                                distance_type
                            ],
                        )
                    if this_dist == float("inf"):
                        this_dist = sys.maxsize / 6
                # Build up the overall distance for the current mapping of the current side
                cur_dist += this_dist / len(mapping)
            # Only keep the smallest distance from all the mappings
            side_distance = min(side_distance, cur_dist)
        # Build the total distance as the sum of the individual side's distances
        pos_distance += side_distance / position_array_1.shape[0]
    return pos_distance


def token_state_distance(
    map_name,
    token_array_1,
    token_array_2,
    distance_type="geodesic",
    reference_point="centroid",
):
    """Calculates a distance between two game states based on player positions

    Args:
        map_name (string): Map to search
        token_array_1 (numpy array): 1-D numpy array of a position token
        token_array_2 (numpy array): 1-D numpy array of a position token
        distance_type (string): String indicating how the distance between two player positions should be calculated. Options are "geodesic", "graph", "euclidean" and "edit_distance"
        reference_point (string): String indicating which reference point to use to determine area distance. Options are "centroid" and "representative_point"

    Returns:
        A float representing the distance between these two game states
    """
    if map_name not in NAV:
        raise ValueError("Map not found.")
    if distance_type not in ["graph", "geodesic", "euclidean", "edit_distance"]:
        raise ValueError(
            "distance_type can only be graph, geodesic, euclidean or edit_distance"
        )
    if reference_point not in ["centroid", "representative_point"]:
        raise ValueError("reference_point can only be centroid or representative_point")
    if len(token_array_1) != len(token_array_2):
        raise ValueError("Token arrays have to have the same length!")
    # Get the list of named areas. Needed to translate back from token position to area name
    map_area_names = []
    for area_id in NAV[map_name]:
        if NAV[map_name][area_id]["areaName"] not in map_area_names:
            map_area_names.append(NAV[map_name][area_id]["areaName"])
    map_area_names.sort()

    if (
        len(token_array_1) != len(map_area_names)
        and len(token_array_1) != len(map_area_names) * 2
    ):
        raise ValueError(
            "Token arrays do not have the correct length. There has to be one entry per named area per team considered!"
        )

    token_dist = 0

    if distance_type == "edit_distance":
        # How many edits of one value by 1 (up or down) are needed to go from one array to the other
        # Eg: [3,0,0] to [0,1,0] needs 4 edits. Three to get the first index from 3 to 0 and then one to get the second from 0 to 1
        token_dist = sum(map(abs, np.subtract(token_array_1, token_array_2)))
        token_dist /= len(token_array_1) // len(map_area_names)

    # More complicated distances based on actual area locations
    elif distance_type in ["geodesic", "graph", "euclidean"]:
        # If we do not have the precomputed matrix we need to first build the centroids to get them ourselves later
        if PLACE_DIST_MATRIX is None or map_name not in PLACE_DIST_MATRIX:
            ref_points = {}
            (
                ref_points["centroid"],
                ref_points["representative_point"],
            ) = generate_centroids(map_name)
        # Loop over each team
        for i in range(len(token_array_1) // len(map_area_names)):
            side_distance = float("inf")
            # Get the sub arrays for this team from the total array
            array1, array2 = (
                token_array_1[
                    0
                    + i * len(map_area_names) : len(map_area_names)
                    + i * len(map_area_names),
                ],
                token_array_2[
                    0
                    + i * len(map_area_names) : len(map_area_names)
                    + i * len(map_area_names),
                ],
            )
            # Make sure array1 is the larger one
            if sum(array1) < sum(array2):
                array1, array2 = array2, array1
            size = sum(array2)
            # Get the indices where array1 and array2 have larger values than the other.
            # Use each index as often as it is larger
            diff_array = np.subtract(array1, array2)
            pos_indices = []
            neg_indices = []
            for i, difference in enumerate(diff_array):
                if difference > 0:
                    pos_indices.extend([i] * int(difference))
                elif difference < 0:
                    neg_indices.extend([i] * int((abs(difference))))
            # Get all possible mappings between the differences
            # Eg: diff array is [1,1,-1,-1] then pos_indices is [0,1] and neg_indices is [2,3]
            # The possible mappings are then [(0,2),(1,3)] and [(0,3),(1,2)]
            for mapping in (
                list(zip(x, neg_indices))
                for x in multiset_permutations(pos_indices, len(neg_indices))
            ):
                this_dist = 0
                # Iterate of the mapping. Eg: [(0,2),(1,3)] and get their total distance
                # For the example this would be dist(0,2)+dist(1,3)
                for area1, area2 in mapping:
                    if PLACE_DIST_MATRIX is None or map_name not in PLACE_DIST_MATRIX:
                        this_dist += min(
                            area_distance(
                                map_name,
                                ref_points[reference_point][map_area_names[area1]],
                                ref_points[reference_point][map_area_names[area2]],
                                dist_type=distance_type,
                            )["distance"],
                            area_distance(
                                map_name,
                                ref_points[reference_point][map_area_names[area2]],
                                ref_points[reference_point][map_area_names[area1]],
                                dist_type=distance_type,
                            )["distance"],
                        )
                    else:
                        this_dist += min(
                            PLACE_DIST_MATRIX[map_name][map_area_names[area1]][
                                map_area_names[area2]
                            ][distance_type][reference_point],
                            PLACE_DIST_MATRIX[map_name][map_area_names[area2]][
                                map_area_names[area1]
                            ][distance_type][reference_point],
                        )
                this_dist /= size
                side_distance = min(side_distance, this_dist)
            token_dist += side_distance / (len(token_array_1) // len(map_area_names))
    return token_dist


def frame_distance(
    map_name,
    frame1,
    frame2,
    distance_type="geodesic",
):
    """Calculates a distance between two frames based on player positions

    Args:
        map_name (string): Map to search
        frame1 (dict): A game frame
        frame2 (dict): A game frame
        distance_type: String indicating how the distance between two player positions should be calculated. Options are "geodesic", "graph" and "euclidean"

    Returns:
        A float representing the distance between these two game states
    """
    pos_array1 = np.zeros(
        (
            2
            if len(frame1["ct"]["players"]) > 0 and len(frame1["t"]["players"]) > 0
            else 1,
            max(len(frame1["ct"]["players"]), len(frame1["t"]["players"])),
            3,
        )
    )
    pos_array2 = np.zeros(
        (
            2
            if len(frame2["ct"]["players"]) > 0 and len(frame2["t"]["players"]) > 0
            else 1,
            max(len(frame2["ct"]["players"]), len(frame2["t"]["players"])),
            3,
        )
    )
    team_to_index = {"t": 0, "ct": 1}
    for team in frame1:
        index = (
            team_to_index[team]
            if (len(frame1["ct"]["players"]) > 0 and len(frame1["t"]["players"]) > 0)
            else 0
        )
        for player_index, player in enumerate(frame1[team]["players"]):
            pos_array1[index][player_index][0] = player["x"]
            pos_array1[index][player_index][1] = player["y"]
            pos_array1[index][player_index][2] = player["z"]
    for team in frame2:
        index = (
            team_to_index[team]
            if (len(frame2["ct"]["players"]) > 0 and len(frame2["t"]["players"]) > 0)
            else 0
        )
        for player_index, player in enumerate(frame2[team]["players"]):
            pos_array2[index][player_index][0] = player["x"]
            pos_array2[index][player_index][1] = player["y"]
            pos_array2[index][player_index][2] = player["z"]
    return position_state_distance(map_name, pos_array1, pos_array2, distance_type)


def token_distance(
    map_name,
    token1,
    token2,
    distance_type="geodesic",
    reference_point="centroid",
):
    """Calculates a distance between two game states based on position tokens

    Args:
        map_name (string): Map to search
        token1 (string): A team position token
        token2 (string): A team position token
        distance_type: String indicating how the distance between two player positions should be calculated. Options are "geodesic", "graph", "euclidean" and "edit_distance"
        reference_point: String indicating which reference point to use to determine area distance. Options are "centroid" and "representative_point"

    Returns:
        A float representing the distance between these two game states
    """
    return token_state_distance(
        map_name,
        np.array(list(token1), dtype=int),
        np.array(list(token2), dtype=int),
        distance_type,
        reference_point,
    )
