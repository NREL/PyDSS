#**Authors:**
# Akshay Kumar Jain; Akshay.Jain@nrel.gov


import logging
import os
import matplotlib.pyplot as plt
import csv
import pandas as pd
import math
import opendssdirect as dss
import networkx as nx
import time
import json
# from place_new_regs import place_new_regs
import numpy as np
import scipy.spatial.distance as ssd
from sklearn.cluster import AgglomerativeClustering
import matplotlib.image as mpimg
plt.rcParams.update({'font.size': 14})


# Post process thermal upgrades dss files to create network plots and also to create easier post processing files
# TODO: make function to post process orig and new objects (instead of text parsing file)
class postprocess_thermal_upgrades():
    def __init__(self, Settings, dss, logger):
        self.Settings = Settings
        self.logger = logger
        self.sol = dss.Solution
        self.new_lines = self.Settings["new_lines"]
        self.orig_lines = self.Settings["orig_lines"]
        self.new_xfmrs = self.Settings["new_xfmrs"]
        self.orig_xfmrs = self.Settings["orig_xfmrs"]
        self.orig_lc_parameters = self.Settings["orig_lc_parameters"]
        # TODO - next two lines to be used when we move to object comparison instead of text parsing
        # self.orig_line_parameters = self.Settings["orig_line_parameters"]
        # self.orig_DT_parameters = self.Settings["orig_DT_parameters"]
        dss.Vsources.First()
        self.source = dss.CktElement.BusNames()[0].split(".")[0]
        if self.Settings["Create_plots"]:
            self.create_op_plots()
        self.get_orig_line_DT_params()
        self.process_thermal_upgrades()
        try:
            self.get_all_parallel()  # save csv of parallel lines and transformers
        except:
            self.logger.info("Parallel line and transformer computation failed")

    def get_orig_line_DT_params(self):
        self.orig_line_parameters = {}
        self.orig_DT_parameters = {}
        # NEED TO CHECK WHY THIS IS COMMENTED OUT
        # self.orig_lc_parameters = {}
        # f = open(os.path.join(self.Settings["Outputs"], "Original_linecodes_parameters.json"), "r")
        # data = json.load(f)
        # for lc, params in data.items():
        #     self.orig_lc_parameters[lc.lower()] = params
        f = open(os.path.join(self.Settings["Outputs"], "Original_line_parameters.json"), "r")
        data = json.load(f)
        for line, params in data.items():
            try:
                for ln_par, ln_par_val in params.items():
                    if ln_par.lower()=="linecode":
                        ln_ampacity = self.orig_lc_parameters[ln_par_val]["Ampacity"]
                params["Ampacity"] = ln_ampacity
            except:
                self.logger.info("No linecode for line: {} ".format(line))
                pass
            self.orig_line_parameters["line."+line.lower()] = params
        f = open(os.path.join(self.Settings["Outputs"], "Original_xfmr_parameters.json"), "r")
        data = json.load(f)
        for xfmr, params in data.items():
            self.orig_DT_parameters["transformer."+xfmr.lower()] = params

    def process_thermal_upgrades(self):
        self.pen_level_upgrades = {}
        with open(os.path.join(self.Settings["Outputs"], "thermal_upgrades.dss")) as datafile:
            for line in datafile:
                new_line = line.split()
                for parameters in new_line:
                    if parameters.lower().startswith("line."):
                        ln_name = parameters.split("_upgrade")[0]
                        if ln_name not in self.pen_level_upgrades:
                            if line.lower().startswith("new"):
                                self.pen_level_upgrades[ln_name] = {"new":[1,self.orig_line_parameters[ln_name.lower()]],"upgrade":[0,[]]}
                            elif line.lower().startswith("edit"):
                                lc_name = self.get_line_upgrade_params(new_line)
                                lc_ampacity = self.orig_lc_parameters[lc_name]["Ampacity"]
                                ln_params = {"Linecode": lc_name, "Ampacity": lc_ampacity}
                                self.pen_level_upgrades[ln_name] = {"new":[0,self.orig_line_parameters[ln_name.lower()]],"upgrade":[1,[ln_params]]}
                        elif ln_name in self.pen_level_upgrades:
                            if line.lower().startswith("new"):
                                self.pen_level_upgrades[ln_name]["new"][0]+=1
                            elif line.lower().startswith("edit"):
                                lc_name = self.get_line_upgrade_params(new_line)
                                lc_ampacity = self.orig_lc_parameters[lc_name]["Ampacity"]
                                ln_params = {"Linecode":lc_name,"Ampacity":lc_ampacity}
                                self.pen_level_upgrades[ln_name]["upgrade"][0]+=1
                                self.pen_level_upgrades[ln_name]["upgrade"][1].append(ln_params)
                    if parameters.lower().startswith("transformer."):
                        dt_name = parameters.split("_upgrade")[0]
                        if dt_name not in self.pen_level_upgrades:
                            if line.lower().startswith("new"):
                                self.pen_level_upgrades[dt_name] = {"new":[1,self.orig_DT_parameters[dt_name.lower()]],"upgrade":[0,[]]}
                            elif line.lower().startswith("edit"):
                                dt_params = self.get_xfmr_upgrade_params(new_line)
                                self.pen_level_upgrades[dt_name] = {"new":[0,self.orig_DT_parameters[dt_name.lower()]],"upgrade":[1,[dt_params]]}
                        elif dt_name in self.pen_level_upgrades:
                            if line.lower().startswith("new"):
                                self.pen_level_upgrades[dt_name]["new"][0]+=1
                            elif line.lower().startswith("edit"):
                                dt_params = self.get_xfmr_upgrade_params(new_line)
                                self.pen_level_upgrades[dt_name]["upgrade"][0]+=1
                                self.pen_level_upgrades[dt_name]["upgrade"][1].append(dt_params)
        self.pen_level_upgrades["feederhead_name"] = self.Settings["feederhead_name"]
        self.pen_level_upgrades["feederhead_basekV"] = self.Settings["feederhead_basekV"]
        self.write_to_json(self.pen_level_upgrades, "Processed_thermal_upgrades")
        if self.Settings["Create_plots"]:
            self.create_edge_node_dicts()
            self.plot_feeder()

    def write_to_json(self, dict, file_name):
        with open(os.path.join(self.Settings["Outputs"],"{}.json".format(file_name)), "w") as fp:
            json.dump(dict, fp, indent=4)

    def get_line_upgrade_params(self, new_line):
        lc_name = ''
        line_name = [string for string in new_line if 'Line.' in string][0]
        line_name = line_name.split(".")[1]
        for parameters in new_line:
            if parameters.lower().startswith("linecode"):
                lc_name = parameters.split("=")[1]
            elif parameters.lower().startswith("geometry"):
                lc_name = parameters.split("=")[1]
            else:
                lc_name = line_name  # i.e. if the line parameters are defined in line definition itself
        return lc_name

    def get_xfmr_upgrade_params(self, new_line):
        dt_params = {}
        for params in new_line:
            if params.lower().startswith("%noloadloss"):
                dt_params["%noloadloss"] = params.split("=")[1]
            if params.lower().startswith("kva"):
                if "kva" not in dt_params:
                    dt_params["kva"] = [params.split("=")[1]]
                elif "kva" in dt_params:
                    dt_params["kva"].append(params.split("=")[1])
            if params.lower().startswith("%r"):
                if "%r" not in dt_params:
                    dt_params["%r"] = [params.split("=")[1]]
                elif "%r" in dt_params:
                    dt_params["%r"].append(params.split("=")[1])
        return dt_params

    def create_edge_node_dicts(self):
        self.edge_to_plt_dict = []
        self.edge_pos_plt_dict = {}
        self.edge_size_list = []
        self.DT_sec_lst = []
        self.DT_size_list = []
        self.DT_sec_coords = {}
        for key,vals in self.pen_level_upgrades.items():
            if key.lower().startswith("line"):
                dss.Circuit.SetActiveElement("{}".format(key))
                from_bus = dss.CktElement.BusNames()[0].split(".")[0]
                to_bus = dss.CktElement.BusNames()[1].split(".")[0]
                self.edge_to_plt_dict.append((from_bus, to_bus))
                self.edge_pos_plt_dict[from_bus] = self.pos_dict[from_bus]
                self.edge_pos_plt_dict[to_bus] = self.pos_dict[to_bus]
                self.edge_size_list.append((vals["new"][0]+vals["upgrade"][0])*5)
            if key.lower().startswith("transformer"):
                dss.Circuit.SetActiveElement("{}".format(key))
                bus_sec = dss.CktElement.BusNames()[1].split(".")[0]
                self.DT_sec_lst.append(bus_sec)
                self.DT_size_list.append((vals["new"][0]+vals["upgrade"][0])*25)
                self.DT_sec_coords[bus_sec] = self.pos_dict[bus_sec]

    def create_op_plots(self):
        self.all_bus_names = dss.Circuit.AllBusNames()
        self.G = nx.DiGraph()
        self.generate_nodes()
        self.generate_edges()
        self.pos_dict = nx.get_node_attributes(self.G, 'pos')
        self.correct_node_coords()
        self.logger.info("Length: %s", len(self.pos_dict))

    def correct_node_coords(self):
        # If node doesn't have node attributes, attach parent or child node's attributes
        new_temp_graph = self.G
        temp_graph = new_temp_graph.to_undirected()
        for n, d in self.G.in_degree().items():
            if d == 0:
                self.source = n
        for key, vals in self.pos_dict.items():
            if vals[0] == 0.0 and vals[1] == 0.0:
                new_x = 0
                new_y = 0
                pred_buses = nx.shortest_path(temp_graph, source=key, target=self.source)
                if len(pred_buses) > 0:
                    for pred_bus in pred_buses:
                        if pred_bus == key:
                            continue
                        if self.pos_dict[pred_bus][0] != 0.0 and self.pos_dict[pred_bus][1] != 0.0:
                            new_x = self.pos_dict[pred_bus][0]
                            new_y = self.pos_dict[pred_bus][1]
                            self.G.node[key]["pos"] = [new_x, new_y]
                            break
                if new_x == 0 and new_y == 0:
                    # Since either predecessor nodes were not available or they did not have
                    # non-zero coordinates, try successor nodes
                    # Get a leaf node
                    for x in self.G.nodes():
                        if self.G.out_degree(x) == 0 and self.G.in_degree(x) == 1:
                            leaf_node = x
                            break
                    succ_buses = nx.shortest_path(temp_graph, source=key, target=leaf_node)
                    if len(succ_buses) > 0:
                        for pred_bus in succ_buses:
                            if pred_bus == key:
                                continue
                            if self.pos_dict[pred_bus][0] != 0.0 and self.pos_dict[pred_bus][1] != 0.0:
                                new_x = self.pos_dict[pred_bus][0]
                                new_y = self.pos_dict[pred_bus][1]
                                self.G.node[key]["pos"] = [new_x, new_y]
                                break
        # Update pos dict with new coordinates
        self.pos_dict = nx.get_node_attributes(self.G, 'pos')

    def generate_nodes(self):
        self.nodes_list = []
        for b in self.all_bus_names:
            dss.Circuit.SetActiveBus(b)
            name = b.lower()
            position = []
            position.append(dss.Bus.X())
            position.append(dss.Bus.Y())
            self.G.add_node(name, pos=position)
            self.nodes_list.append(b)

    def generate_edges(self):
        '''
        All lines, switches, reclosers etc are modeled as lines, so calling lines takes care of all of them.
        However we also need to loop over transformers as they form the edge between primary and secondary nodes
        :return:
        '''
        dss.Lines.First()
        while True:
            from_bus = dss.Lines.Bus1().split('.')[0].lower()
            to_bus = dss.Lines.Bus2().split('.')[0].lower()
            phases = dss.Lines.Phases()
            length = dss.Lines.Length()
            name = dss.Lines.Name()
            self.G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
            if not dss.Lines.Next() > 0:
                break

        dss.Transformers.First()
        while True:
            bus_names = dss.CktElement.BusNames()
            from_bus = bus_names[0].split('.')[0].lower()
            to_bus = bus_names[1].split('.')[0].lower()
            phases = dss.CktElement.NumPhases()
            length = 0.0
            name = dss.Transformers.Name()
            self.G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
            if not dss.Transformers.Next() > 0:
                break

    def plot_feeder(self):
        plt.figure(figsize=(40, 40), dpi=10)
        if len(self.edge_size_list)>0:
            de = nx.draw_networkx_edges(self.G, pos=self.edge_pos_plt_dict, edgelist=self.edge_to_plt_dict, edge_color="r",
                                        alpha=1.0, width=self.edge_size_list)
        ec = nx.draw_networkx_edges(self.G, pos=self.pos_dict, alpha=1.0, width=1)
        if len(self.DT_sec_lst)>0:
            dt = nx.draw_networkx_nodes(self.G, pos=self.DT_sec_coords, nodelist=self.DT_sec_lst, node_size=self.DT_size_list,
                                        node_color='r', alpha=1)
        ldn = nx.draw_networkx_nodes(self.G, pos=self.pos_dict, nodelist=self.nodes_list, node_size=1,
                                     node_color='k', alpha=1)

        # nx.draw_networkx_labels(self.G, pos=self.pos_dict, node_size=1, font_size=15)
        plt.title("Thermal violations")
        plt.axis("off")
        plt.savefig(os.path.join(self.Settings["Outputs"],"Thermal_upgrades.pdf"))

    def parallel_upgrades(self, equipment_type):
        '''upgrade_df is a dataframe version of the processed_thermal_upgrades.json
        file produced by Akshay's upgrade codeself.
        equipment_type is a string equal to either "Transformer" or "Line" '''
        parallel_equip_df = pd.DataFrame()
        parallel_equip_ids = []
        parallel_equip_counts = []

        for k in self.pen_level_upgrades.keys():
            equip_str = equipment_type + '.'
            if equip_str in k:
                # count of new lines added to address overload. Often 1, but could be > 1 with severe overloads
                parallel_count = self.pen_level_upgrades[k]['new'][0]

                if parallel_count > 1:
                    parallel_equip_ids.append(k)
                    parallel_equip_counts.append(parallel_count)

        parallel_equip_df['element_id'] = parallel_equip_ids
        parallel_equip_df['count_of_equipment_in_parallel'] = parallel_equip_counts

        return parallel_equip_df

    def get_all_parallel(self):
        ''' processed_upgrade_file is the name of the json file written out from
        Akshay's thermal upgrades code'''

        xfmr_parallel_df = self.parallel_upgrades('Transformer')
        line_parallel_df = self.parallel_upgrades('Line')

        xfmr_parallel_df.to_csv(os.path.join(self.Settings["Outputs"], 'summary_of_parallel_transformer_upgrades.csv'))
        line_parallel_df.to_csv(os.path.join(self.Settings["Outputs"], 'summary_of_parallel_line_upgrades.csv'))
        return


# Test Disco feeder
if __name__ == "__main__":
    Settings = {
        "Feeder"                    : "../Test_Feeder_J1",
        "master file"               : "Master.dss",
        "Outputs"                   : "../Outputs",
        "Create_plots"              : True
    }
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    data = postprocess_thermal_upgrades(Settings, dss, logger)
