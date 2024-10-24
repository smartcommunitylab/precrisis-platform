import json
import pickle
import sys

import geopandas as gpd
import geopy.distance
import networkx as nx
import osmnx as ox
from shapely import to_geojson
from shapely.geometry import MultiLineString, Point

# helper functions


def get_distance_time(origin, destination, net_type):
    G = ox.graph_from_point(origin, network_type="drive", dist=10000)

    # impute missing edge speeds and add travel times
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)

    # calculate route minimizing some weight
    orig = ox.nearest_nodes(G, origin[1], origin[0])
    dest = ox.nearest_nodes(G, destination[1], destination[0])

    try:
        route = nx.shortest_path(G, orig, dest, weight="travel_time")
    except Exception:
        return None

    # OPTION 1: see the travel time for the whole route
    travel_time = nx.shortest_path_length(G, orig, dest, weight="travel_time")
    return round(travel_time)

    # # OPTION 2: loop through the edges in your route
    # # and print the length and travel time of each edge
    # for u, v in zip(route[:-1], route[1:]):
    #     length = round(G.edges[(u, v, 0)]['length'])
    #     travel_time = round(G.edges[(u, v, 0)]['travel_time'])
    #     print(u, v, length, travel_time, sep='\t')

    # # OPTION 3: use get_route_edge_attributes
    # cols = ['osmid', 'length', 'travel_time']
    # attrs = ox.utils_graph.get_route_edge_attributes(G, route)
    # print(pd.DataFrame(attrs)[cols])


def get_distance_travel(origin, destination, net_type):
    G = ox.graph_from_point(origin, network_type="drive", dist=10000)

    # impute missing edge speeds and add travel times
    # G = ox.add_edge_speeds(G)
    # G = ox.add_edge_travel_times(G)

    # calculate route minimizing some weight
    orig = ox.nearest_nodes(G, origin[1], origin[0])
    dest = ox.nearest_nodes(G, destination[1], destination[0])

    try:
        route = nx.shortest_path(G, orig, dest, weight="length")
    except Exception:
        return None

    # OPTION 1: see the travel time for the whole route
    travel_dist = nx.shortest_path_length(G, orig, dest, weight="length")
    return round(travel_dist)

# ARGS
CITY = sys.argv[1]

LOCATIONS = {
    "Allianz_Stadion": (48.19802059, 16.26601893),
    "Donauinsel": (48.21069623, 16.43500653),
    "Ernst_Happel_Stadion": (48.20720609, 16.42098409),
    "Heldenplatz": (48.20662377, 16.36351103),
    "Rathausplatz": (48.21064294, 16.35875444),
    "Schottenring": (48.21365638, 16.37065462),
    "Waehring": (48.22914869, 16.33905238),
}

OUTPUT = sys.argv[2]

data = []

for LOCATION_NAME in LOCATIONS:

    LOCATION = LOCATIONS[LOCATION_NAME]

    # the full list of pois tags can be found here
    # https://wiki.openstreetmap.org/wiki/Map_features
    # here we open use a dictionary with a list of "reasonable" POIs
    with open("pois_dict.pickle", "rb") as handle:
        pois_dict = pickle.load(handle)

        pois_dict["amenity"].append("parking")
        POIS_TAGS = pois_dict
        # remove tags that are not useful
        del POIS_TAGS["landuse"]

        # All points of interest

        # Create a new dictionary to store selected entries
        selected_entries = {}

        # Check if 'amenity' key exists
        if "amenity" in POIS_TAGS:
            # Create a new dictionary with only 'church' and 'synagogue' entries
            selected_entries["amenity"] = [
                tag
                for tag in POIS_TAGS["amenity"]
                if tag
                in [
                    "church",
                    "synagogue",
                    "school",
                    "university",
                    "terminal",
                    "bank",
                    "hospital",
                    "cinema",
                    "theatre",
                    "conference_centre",
                    "embassy",
                ]
            ]
        # Filter 'building' entries
        if "building" in POIS_TAGS:
            selected_entries["building"] = [
                tag
                for tag in POIS_TAGS["building"]
                if tag
                in [
                    "monastery",
                    "place_of_worship",
                    "police",
                    "fire_station",
                    "cathedral",
                    "chapel",
                    "church",
                    "mosque",
                    "religious",
                    "synagogue",
                    "shrine",
                    "temple",
                    "government",
                    "school",
                    "university",
                    "stadium",
                ]
            ]

        if "building" in POIS_TAGS:
            selected_entries["emergency"] = [
                tag for tag in POIS_TAGS["emergency"] if tag in ["church", "memorial"]
            ]

        if "building" in POIS_TAGS:
            selected_entries["leisure"] = [
                tag
                for tag in POIS_TAGS["leisure"]
                if tag in ["park", "sports_centre", "stadium"]
            ]

        if "building" in POIS_TAGS:
            selected_entries["office"] = [
                tag
                for tag in POIS_TAGS["office"]
                if tag
                in [
                    "educational_institution",
                    "diplomatic",
                    "government",
                    "ngo",
                    "religion",
                    "political party",
                ]
            ]

        if "building" in POIS_TAGS:
            selected_entries["tourism"] = [
                tag for tag in POIS_TAGS["tourism"] if tag in ["hotel", "museum"]
            ]

        # RADIUS = 3000
        # test radius
        radius_list = [500, 800, 1000]

        for RADIUS in radius_list:
            print(RADIUS)
            print(LOCATION_NAME)

            pois_gdf = ox.features_from_point(LOCATION, selected_entries, dist=RADIUS)

            # Street Network

            # mainly or exclusively for pedestrian
            PEDESTRAIN_DICT = {
                "highway": ["pedestrian", "footway", "bridleway", "steps"],
                "footway": ["sidewalk", "bridleway", "steps"],
            }

            # mainly or exclusively for bicycles
            BIKE_DICT = {
                "highway": ["cycleway"],
                "cycleway": [
                    "lane",
                    "opposite",
                    "opposite_lane",
                    "opposite_track",
                    "share_busway",
                    "opposite_share_busway",
                    "shared_lane",
                ],
            }

            VEHICLE_DICT = {
                "highway": [
                    "motorway",
                    "trunk",
                    "primary",
                    "secondary",
                    "tertiary",
                    "unclassified",
                    "residential",
                    "motorway_link",
                    "trunk_link",
                    "primary_link",
                    "secondary_link",
                    "tertiary_link",
                ],
            }

            vehicle_streets = ox.features_from_point(
                LOCATION, VEHICLE_DICT, dist=RADIUS
            )
            # bike_streets = ox.features_from_point(LOCATION, BIKE_DICT, dist=RADIUS)
            pedestrian_streets = ox.features_from_point(
                LOCATION, PEDESTRAIN_DICT, dist=RADIUS
            )
            buildings = ox.features_from_point(
                LOCATION, tags={"building": True}, dist=RADIUS
            )

            try:
                bike_streets = ox.features_from_point(LOCATION, BIKE_DICT, dist=RADIUS)
            except Exception as e:
                print(e)
                bike_streets = pedestrian_streets

            # insert into database
            data_to_be_processed = {
                "pois_gdf": pois_gdf,
                "vehicle_streets": vehicle_streets,
                "bike_streets": bike_streets,
                "pedestrian_streets": pedestrian_streets,
                "buildings": buildings,
            }
            for k, v in data_to_be_processed.items():
                for i in v["geometry"]:
                    base = {
                        "measurement": "points_of_interest",
                        "tags": {
                            "city": CITY,
                            "poi_type": k,
                            "location": LOCATION_NAME,
                            "radius": RADIUS,
                        },
                        "fields": {
                            "geojson": to_geojson(i),
                            "city": CITY,
                            "poi_type": k,
                            "location": LOCATION_NAME,
                            "radius": RADIUS,
                        },
                    }
                    data.append(base)

        # compute shortest paths

        HOSPITALS_DICT = {"amenity": "hospital"}

        # TODO
        # services being fixed to a larger radius for safety, need to find a better way to resolve

        RADIUS = 4000

        hospitals = ox.features_from_point(LOCATION, HOSPITALS_DICT, dist=RADIUS)

        # calculate distances

        hospitals.to_crs(epsg=4326, inplace=True)
        dist_hospitals = hospitals.copy()
        dist_hospitals["hospital_centroid"] = dist_hospitals.geometry.centroid
        dist_hospitals["my_loc"] = Point(LOCATION[1], LOCATION[0])
        dist_hospitals["distance_geodesic"] = dist_hospitals.apply(
            lambda row: geopy.distance.geodesic(
                (row["hospital_centroid"].y, row["hospital_centroid"].x),
                (row["my_loc"].y, row["my_loc"].x),
            ),
            axis=1,
        )
        dist_hospitals["distance_travel"] = dist_hospitals.apply(
            lambda row: get_distance_travel(
                (row["my_loc"].y, row["my_loc"].x),
                (row["hospital_centroid"].y, row["hospital_centroid"].x),
                "drive",
            ),
            axis=1,
        )
        dist_hospitals["distance_time_walk"] = (
            dist_hospitals["distance_travel"] / 1.38889
        )  # 5km/h = 1.38 m/s
        dist_hospitals["distance_time_vehicle"] = dist_hospitals.apply(
            lambda row: get_distance_time(
                (row["my_loc"].y, row["my_loc"].x),
                (row["hospital_centroid"].y, row["hospital_centroid"].x),
                "drive",
            ),
            axis=1,
        )

        dist_hospitals[
            [
                "geometry",
                "hospital_centroid",
                "my_loc",
                "distance_geodesic",
                "distance_travel",
                "distance_time_walk",
                "distance_time_vehicle",
            ]
        ].sort_values(by="distance_travel").head()

        # Convert the "police_centroid" column to a GeoDataFrame
        gdf_hospital = gpd.GeoDataFrame(dist_hospitals, geometry="hospital_centroid")

        # Extract the latitude and longitude from the "police_centroid" column
        gdf_hospital["latitude"] = gdf_hospital["hospital_centroid"].y
        gdf_hospital["longitude"] = gdf_hospital["hospital_centroid"].x

        # Sort the GeoDataFrame by increasing "distance_travel"
        sorted_hospital = gdf_hospital.sort_values(by="distance_travel")

        # Extract the latitude and longitude of the top two rows
        top_coordinates_hospital = (
            sorted_hospital[["latitude", "longitude"]].head(1).values.tolist()
        )

        # Example of the modified code:
        origin = LOCATION
        destination_hospital = top_coordinates_hospital

        # Convert the inner list to a tuple
        destination_hospital = tuple(destination_hospital[0])

        # EXAMPLE PLOT SHORTEST ROUTE (travel time)
        G = ox.graph_from_point(origin, network_type="drive", dist=10000)

        # calculate route minimizing some weight
        orig_hospital = ox.nearest_nodes(G, origin[1], origin[0])
        dest_hospital = ox.nearest_nodes(
            G, destination_hospital[1], destination_hospital[0]
        )

        route_hospital = nx.shortest_path(
            G, orig_hospital, dest_hospital, weight="length"
        )

        nodes, edges = ox.graph_to_gdfs(G)
        geoms = [
            edges.loc[(u, v, 0), "geometry"]
            for u, v in zip(route_hospital[:-1], route_hospital[1:])
        ]

        route_hosptal_geojson = to_geojson(MultiLineString(geoms))

        POLICE_DICT = {"amenity": "police"}

        police = ox.features_from_point(LOCATION, POLICE_DICT, dist=RADIUS)

        police.to_crs(epsg=4326, inplace=True)
        dist_police = police.copy()
        dist_police["police_centroid"] = dist_police.geometry.centroid
        dist_police["my_loc"] = Point(LOCATION[1], LOCATION[0])
        dist_police["distance_geodesic"] = dist_police.apply(
            lambda row: geopy.distance.geodesic(
                (row["police_centroid"].y, row["police_centroid"].x),
                (row["my_loc"].y, row["my_loc"].x),
            ),
            axis=1,
        )
        dist_police["distance_travel"] = dist_police.apply(
            lambda row: get_distance_travel(
                (row["my_loc"].y, row["my_loc"].x),
                (row["police_centroid"].y, row["police_centroid"].x),
                "drive",
            ),
            axis=1,
        )
        dist_police["distance_time_walk"] = (
            dist_police["distance_travel"] / 1.38889
        )  # 5km/h = 1.38 m/s
        dist_police["distance_time_vehicle"] = dist_police.apply(
            lambda row: get_distance_time(
                (row["my_loc"].y, row["my_loc"].x),
                (row["police_centroid"].y, row["police_centroid"].x),
                "drive",
            ),
            axis=1,
        )

        dist_police[
            [
                "geometry",
                "police_centroid",
                "my_loc",
                "distance_geodesic",
                "distance_travel",
                "distance_time_walk",
                "distance_time_vehicle",
            ]
        ].sort_values(by="distance_travel")

        # Convert the "police_centroid" column to a GeoDataFrame
        gdf_police = gpd.GeoDataFrame(dist_police, geometry="police_centroid")

        # Extract the latitude and longitude from the "police_centroid" column
        gdf_police["latitude"] = gdf_police["police_centroid"].y
        gdf_police["longitude"] = gdf_police["police_centroid"].x

        # Sort the GeoDataFrame by increasing "distance_travel"
        sorted_police = gdf_police.sort_values(by="distance_travel")

        # Extract the latitude and longitude of the top two rows
        top_coordinates_police = (
            sorted_police[["latitude", "longitude"]].head(1).values.tolist()
        )

        # Example of the modified code:
        origin = LOCATION
        destination_police = top_coordinates_police

        # Convert the inner list to a tuple
        destination_police = tuple(destination_police[0])

        # EXAMPLE PLOT SHORTEST ROUTE (travel time)
        G = ox.graph_from_point(origin, network_type="drive", dist=10000)

        # calculate route minimizing some weight
        orig_police = ox.nearest_nodes(G, origin[1], origin[0])
        dest_police = ox.nearest_nodes(G, destination_police[1], destination_police[0])

        route_police = nx.shortest_path(G, orig_police, dest_police, weight="length")

        nodes, edges = ox.graph_to_gdfs(G)
        geoms = [
            edges.loc[(u, v, 0), "geometry"]
            for u, v in zip(route_police[:-1], route_police[1:])
        ]

        route_police_geojson = to_geojson(MultiLineString(geoms))

        FIRE_DICT = {"amenity": "fire_station", "building": "fire_station"}

        fire_station = ox.features_from_point(LOCATION, FIRE_DICT, dist=RADIUS)
        fire_station.to_crs(epsg=4326, inplace=True)
        dist_fire_station = fire_station.copy()
        dist_fire_station["fire_station_centroid"] = dist_fire_station.geometry.centroid
        dist_fire_station["my_loc"] = Point(LOCATION[1], LOCATION[0])
        dist_fire_station["distance"] = dist_fire_station.apply(
            lambda row: geopy.distance.geodesic(
                (row["fire_station_centroid"].y, row["fire_station_centroid"].x),
                (row["my_loc"].y, row["my_loc"].x),
            ),
            axis=1,
        )
        dist_fire_station[
            ["geometry", "fire_station_centroid", "my_loc", "distance"]
        ].sort_values(by="distance").head()

        dist_fire_station["distance_geodesic"] = dist_fire_station.apply(
            lambda row: geopy.distance.geodesic(
                (row["fire_station_centroid"].y, row["fire_station_centroid"].x),
                (row["my_loc"].y, row["my_loc"].x),
            ),
            axis=1,
        )
        dist_fire_station["distance_travel"] = dist_fire_station.apply(
            lambda row: get_distance_travel(
                (row["my_loc"].y, row["my_loc"].x),
                (row["fire_station_centroid"].y, row["fire_station_centroid"].x),
                "drive",
            ),
            axis=1,
        )
        dist_fire_station["distance_time_walk"] = (
            dist_fire_station["distance_travel"] / 1.38889
        )  # 5km/h = 1.38 m/s
        dist_fire_station["distance_time_vehicle"] = dist_fire_station.apply(
            lambda row: get_distance_time(
                (row["my_loc"].y, row["my_loc"].x),
                (row["fire_station_centroid"].y, row["fire_station_centroid"].x),
                "drive",
            ),
            axis=1,
        )

        dist_fire_station[
            [
                "geometry",
                "fire_station_centroid",
                "my_loc",
                "distance_geodesic",
                "distance_travel",
                "distance_time_walk",
                "distance_time_vehicle",
            ]
        ].sort_values(by="distance_travel").head()

        # Convert the "police_centroid" column to a GeoDataFrame
        gdf_fire = gpd.GeoDataFrame(dist_fire_station, geometry="fire_station_centroid")

        # Extract the latitude and longitude from the "police_centroid" column
        gdf_fire["latitude"] = gdf_fire["fire_station_centroid"].y
        gdf_fire["longitude"] = gdf_fire["fire_station_centroid"].x

        # Sort the GeoDataFrame by increasing "distance_travel"
        sorted_fire = gdf_fire.sort_values(by="distance_travel")

        # Extract the latitude and longitude of the top two rows
        top_coordinates_fire = (
            sorted_fire[["latitude", "longitude"]].head(1).values.tolist()
        )

        # Example of the modified code:
        origin = LOCATION
        destination_fire = top_coordinates_fire

        # Convert the inner list to a tuple
        destination_fire = tuple(destination_fire[0])

        # EXAMPLE PLOT SHORTEST ROUTE (travel time)
        G = ox.graph_from_point(origin, network_type="drive", dist=10000)

        # calculate route minimizing some weight
        orig_fire = ox.nearest_nodes(G, origin[1], origin[0])
        dest_fire = ox.nearest_nodes(G, destination_fire[1], destination_fire[0])

        route = nx.shortest_path(G, orig_fire, dest_fire, weight="length")

        nodes, edges = ox.graph_to_gdfs(G)
        geoms = [
            edges.loc[(u, v, 0), "geometry"] for u, v in zip(route[:-1], route[1:])
        ]

        route_firestation_geojson = to_geojson(MultiLineString(geoms))

        # insert into database

        data_to_be_processed = {
            "hospitals": hospitals,
            "police": police,
            "fire_station": fire_station,
        }
        for k, v in data_to_be_processed.items():
            for i in v["geometry"]:
                base = {
                    "measurement": "points_of_interest",
                    "tags": {
                        "city": CITY,
                        "poi_type": k,
                        "location": LOCATION_NAME,
                        "radius": RADIUS,
                    },
                    "fields": {
                        "geojson": to_geojson(i),
                        "city": CITY,
                        "poi_type": k,
                        "location": LOCATION_NAME,
                        "radius": RADIUS,
                    },
                }
                data.append(base)

        data_to_be_processed = {
            "hospitals_route": route_hosptal_geojson,
            "police_route": route_police_geojson,
            "fire_station_route": route_firestation_geojson,
        }
        for k, v in data_to_be_processed.items():
            base = {
                "measurement": "points_of_interest",
                "tags": {
                    "city": CITY,
                    "poi_type": k,
                    "location": LOCATION_NAME,
                    "radius": RADIUS,
                },
                "fields": {
                    "geojson": v,
                    "city": CITY,
                    "poi_type": k,
                    "location": LOCATION_NAME,
                    "radius": RADIUS,
                },
            }
            data.append(base)


with open(OUTPUT, "w") as f:
    json.dump(data, f)
