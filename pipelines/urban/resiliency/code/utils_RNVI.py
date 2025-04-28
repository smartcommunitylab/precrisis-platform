import geopandas as gpd
import random
import pandas as pd
import networkx as nx
import numpy as np



def associate_closest_responders(gdf_nodes, gdf_targets, N_RESPONDERS = 3, RESPONDER_TYPE = 'police'):

    fr_stations = gdf_nodes[gdf_nodes[RESPONDER_TYPE] == True]
    closest_fr_dict = {}

    for idx, node in gdf_targets.iterrows():

        current_osmid = node['osmid']
        current_geometry = node['geometry']

        fr_stations['distance'] = fr_stations['geometry'].distance(current_geometry)
        closest_fr = fr_stations.sort_values('distance').head(N_RESPONDERS)['osmid'].tolist()
        
        closest_fr_dict[current_osmid] = closest_fr
    
    return closest_fr_dict



def get_node_counts_by_district(gdf_nodes):

    node_counts = gdf_nodes.groupby('STATAUSTRI').size()
    node_counts_dict = node_counts.to_dict()
    
    return node_counts_dict



def calculate_cumulative_length_by_district(gdf_edges):

    cumulative_length_by_district = gdf_edges.groupby('STATAUSTRI')['length'].sum()
    length_dict = cumulative_length_by_district.to_dict()
    
    return length_dict



def select_random_nodes_by_district(gdf_nodes, node_counts_by_district, percentage=20):

    fraction = percentage / 100.0
    grouped = gdf_nodes.groupby('STATAUSTRI')
    
    sampled_nodes_list = []

    # Iterate over each district group
    for district_code, group in grouped:
        # Get the total number of nodes in this district from the node_counts_by_district dictionary
        total_nodes = node_counts_by_district.get(district_code, len(group))
        
        # Calculate the sample size as a fraction of the total nodes in the district
        sample_size = max(1, int(np.floor(total_nodes * fraction)))  # Ensure at least 1 node is sampled
        
        # Apply the random sampling for this district
        sampled_nodes = group.sample(n=sample_size, random_state=1) if len(group) >= sample_size else group
        
        # Append the sampled nodes to the list
        sampled_nodes_list.append(sampled_nodes)
    
    # Concatenate the list of sampled nodes into a single GeoDataFrame
    sampled_nodes = gpd.GeoDataFrame(pd.concat(sampled_nodes_list, ignore_index=True))

    return sampled_nodes



def remove_edges(G, selected_edges_gdf):
    # Remove edges from the graph G
    G2 = G.copy()
    for index, row in selected_edges_gdf.iterrows():
        u, v = row['u'], row['v']  # Assuming the third element (0) is irrelevant here
        if G2.has_edge(u, v, 0):
            G2.remove_edge(u, v, 0)
    
    # Recompute the average shortest path length
    return G2
    

    

def select_edges_random(gdf_edges, X, stataustri_code):
 
    gdf_filtered = gdf_edges[gdf_edges['STATAUSTRI'] == stataustri_code].copy()
    gdf_filtered = gdf_filtered.sample(frac=1).reset_index(drop=True) #random_state=42
    
    # Initialize variables to store the cumulative length and selected edges
    cumulative_length = 0
    selected_edges = []
    
    # Iterate over the shuffled GeoDataFrame
    for idx, row in gdf_filtered.iterrows():
        edge_length = row['length']
        
        # Add edge if it doesn't exceed the cumulative length of X
        if cumulative_length + edge_length <= X:
            selected_edges.append(row)
            cumulative_length += edge_length
        else:
            break

    selected_gdf = gpd.GeoDataFrame(selected_edges)
    
    return selected_gdf



def select_edges_random_connected(gdf_edges, X, stataustri_code):

    gdf_filtered = gdf_edges[gdf_edges['STATAUSTRI'] == stataustri_code].copy()
    
    # Shuffle the edges for random selection (optional)
    gdf_filtered = gdf_filtered.sample(frac=1).reset_index(drop=True)  # random_state=42 if needed
    
    # Initialize variables to store the cumulative length and selected edges
    cumulative_length = 0
    selected_edges = []

    # Randomly select an initial edge to start the chain
    first_edge = gdf_filtered.sample(n=1).iloc[0]
    selected_edges.append(first_edge)
    cumulative_length += first_edge['length']
    
    # Initialize the valid node set with the u and v of the first edge
    valid_nodes = {first_edge['u'], first_edge['v']}
    
    # Remove the selected first edge from the pool of edges to avoid reselection
    gdf_filtered = gdf_filtered.drop(first_edge.name)

    # Keep selecting edges until we reach the cumulative length limit X
    while cumulative_length < X:
        # Filter the edges that are connected (i.e., share u or v with the valid nodes)
        connected_edges = gdf_filtered[(gdf_filtered['u'].isin(valid_nodes)) | 
                                       (gdf_filtered['v'].isin(valid_nodes))]

        if connected_edges.empty:
            # No more connected edges to select, break the loop
            break

        # Randomly select one of the connected edges
        next_edge = connected_edges.sample(n=1).iloc[0]

        # Add the edge length to the cumulative length, but break if it exceeds X
        if cumulative_length + next_edge['length'] > X:
            break

        # Append the selected edge to the list of selected edges
        selected_edges.append(next_edge)
        cumulative_length += next_edge['length']

        # Update the valid nodes set with the u and v of the selected edge
        valid_nodes.update([next_edge['u'], next_edge['v']])

        # Remove the selected edge from the pool of edges to avoid reselection
        gdf_filtered = gdf_filtered.drop(next_edge.name)

    # Convert the selected edges to a GeoDataFrame
    selected_gdf = gpd.GeoDataFrame(selected_edges)
    
    return selected_gdf