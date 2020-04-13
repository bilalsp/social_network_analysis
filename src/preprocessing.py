import pickle
import re
import numpy as np
import pandas as pd
import networkx as nx
import os.path


class NetworkPreprocessing:
    
    def __init__(self):
        pass
    
    def convert(self, to = 'gml'):
        """Convert the dictionary data to the gml graph file"""
        with open("data/friends_network.pickle", 'rb') as f:
            friends_network = pickle.load(f)
            
            if not os.path.isfile('data/attributes.csv'):
                attributes = _Generator(path='data/').generate_attributes()
            else:
                attributes = pd.read_csv("data/attributes.csv", usecols=['Unnamed: 0','Name','Birthday','Gender','Hometown','Follower'], index_col='Unnamed: 0')

            attributes.fillna("Unknown", inplace=True)
            null_attr = {'Name':'Unknown', 'Birthday':'Unknown', 'Gender':'Unknown', 'Hometown':'Unknown', 'Follower':'Unknown'}
            nodes = list(map(lambda friend_id: (friend_id,dict(attributes.loc[friend_id])) if friend_id in attributes.index else (friend_id,null_attr), friends_network.keys()))
            edges = [(friend, friend_of_friend) 
                      for friend, friends_of_friend in friends_network.items() for friend_of_friend in friends_of_friend]
            G = nx.Graph()
            G.add_nodes_from(nodes)
            G.add_edges_from(edges)
            write = {'gml': lambda: nx.write_gml(G, 'data/friends_network.gml'), 
                     'graphml': lambda: nx.write_graphml(G, 'data/friends_network.graphml')}
            read = {'gml': lambda: nx.read_gml('data/friends_network.gml'), 
                     'graphml': lambda: nx.read_graphml(G, 'data/friends_network.graphml')}

            write[to]()
            return read[to]()

    def convert_v0(self, to = 'gml'):
        """Convert the dictionary data to the gml graph file"""
        with open("data/friends_network.pickle", 'rb') as f:
            friends_network = pickle.load(f)
            with open('data/more_info.pickle', 'rb') as f2:
                attributes =  pickle.load(f2)
                null_attributes = {'name': 'None', 'work': 'None', 'education': 'None', 'hometown': 'None'}
                nodes = list(map(lambda friend_id: (friend_id,attributes[friend_id]) if friend_id in attributes else (friend_id,null_attributes),friends_network.keys()))
                edges = [(friend, friend_of_friend) 
                      for friend, friends_of_friend in friends_network.items() for friend_of_friend in friends_of_friend]
                G = nx.Graph()
                G.add_nodes_from(nodes)
                G.add_edges_from(edges)
                write = {'gml': lambda: nx.write_gml(G, 'data/friends_network.gml'), 
                         'graphml': lambda: nx.write_graphml(G, 'data/friends_network.graphml')}
                read = {'gml': lambda: nx.read_gml('data/friends_network.gml'), 
                         'graphml': lambda: nx.read_graphml(G, 'data/friends_network.graphml')}

                write[to]()
                return read[to]()
                
                
    def narrownetwork(self):
        pass
    
    
class _Generator:
    """
    To generate the dataframe of attributes from the dictionary
    """
    def __init__(self, path = 'data/'):
        self.path = path
        
    def get_name(self, data: str) -> str:
        return {'Name': data[4:] if data[0] == '(' else data}
        
    def get_basic_info(self, data:dict) -> dict:
        data = data+"\n"
        basic_info = {'Birthday':np.NaN, 'Gender':np.NaN, 'Languages':np.NaN, 'Interested in':np.NaN, 'Religious views':np.NaN, 'Political views':np.NaN}
        for info_type in basic_info.keys():
            found = re.search(info_type+"\n(.*)\n", data)
            if found:
                basic_info[info_type] = found[1]
        try:
            basic_info['Languages'] = basic_info['Languages'].replace(' · ','^')
        except:
            pass
        return basic_info
    
    def get_living_cities(self, data:dict) -> dict:
        living_cities = {'Hometown':np.NaN, 'Current_City':np.NaN, "Other_Places_Lived":np.NaN}
        hometown = re.search("(.*)\nHome Town", data)
        cur_city = re.search("(.*)\nCurrent city", data)
        others = re.findall("(.*)\nMoved (.*)", data)
        if hometown:
            living_cities['Hometown'] = hometown[1]
        if cur_city:
            living_cities['Current_City'] = cur_city[1]
        if others:
            living_cities['Other_Places_Lived'] = others
        return living_cities
    
    def get_following(self, data:str) -> str:
        if data == '':
            return np.NaN
        return data
    
    def get_followers(self, data:str) -> str:
        if data == '':
            return np.NaN
        return data
    
    def generate_attributes(self):
        file_path = self.path+'more_info.pickle'
        with open(file_path, 'rb') as f:
            more_info = pickle.load(f)
            attributes = {}
            for friend_id in more_info.keys():
                try: 
                    friend_attrs = {**self.get_name(more_info[friend_id]['name']),
                               **self.get_basic_info(more_info[friend_id]['basic_info']),
                               **self.get_living_cities(more_info[friend_id]['hometown']),
                               'Follower': self.get_followers(more_info[friend_id]['followers']),
                              'Following': self.get_following(more_info[friend_id]['following'])}
                    attributes[friend_id] = friend_attrs
                except:
                    pass
            df = pd.DataFrame(attributes).transpose()
            df.to_csv(self.path+'attributes.csv', index=True)
            return df
        