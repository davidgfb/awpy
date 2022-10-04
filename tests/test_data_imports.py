import os
import pytest
import networkx

from awpy.data import MAP_DATA, NAV, NAV_CSV, NAV_GRAPHS, PLACE_DIST_MATRIX


class TestDataImports:
    """Class to test the data imports"""

    def test_nav_csv(self):
        """Tests the nav dataframe"""
        assert NAV_CSV[NAV_CSV["mapName"] == "de_cbble"].shape[0] == 1180

    def test_nav(self):
        assert type(NAV) == dict
        assert type(NAV["de_dust2"][152])
        assert NAV["de_dust2"][152]["areaName"] == "BombsiteA"

    def test_nav_graphs(self):
        assert type(NAV_GRAPHS) == dict
        assert type(NAV_GRAPHS["de_dust2"]) == networkx.DiGraph

    def test_map_data(self):
        """Tests the nav data"""
        assert MAP_DATA["de_overpass"]["scale"] == 5.2

    def test_place_dist_matrix(self):
        """Tests the nav data"""
        assert PLACE_DIST_MATRIX["de_nuke"]["TSpawn"]["Silo"]["geodesic"] == {
            "centroid": float("inf"),
            "representative_point": float("inf"),
            "median_dist": float("inf"),
        }
        assert PLACE_DIST_MATRIX["de_nuke"]["TSpawn"]["Silo"]["graph"] == {
            "centroid": float("inf"),
            "representative_point": float("inf"),
            "median_dist": float("inf"),
        }
        assert PLACE_DIST_MATRIX["de_nuke"]["TSpawn"]["Silo"]["euclidean"] == {
            "centroid": 2272.1231010307897,
            "representative_point": 2135.6869302332207,
            "median_dist": 2196.9121452155255,
        }

        assert PLACE_DIST_MATRIX["de_nuke"]["Silo"]["TSpawn"]["geodesic"] == {
            "centroid": 4252.041279324491,
            "representative_point": 4235.10392500164,
            "median_dist": 4325.087557744252,
        }
        assert PLACE_DIST_MATRIX["de_nuke"]["Silo"]["TSpawn"]["graph"] == {
            "centroid": 27,
            "representative_point": 28,
            "median_dist": 28.0,
        }
        assert PLACE_DIST_MATRIX["de_nuke"]["Silo"]["TSpawn"]["euclidean"] == {
            "centroid": 2272.1231010307897,
            "representative_point": 2135.6869302332207,
            "median_dist": 2196.9121452155255,
        }
