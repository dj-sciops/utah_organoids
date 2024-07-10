# %%
# Load Modulues
import os
if os.path.basename(os.getcwd()) == "illustration":
    os.chdir("..")
if os.path.basename(os.getcwd()) == "notebooks":
    os.chdir("..")
import datajoint as dj
from datetime import datetime
import spikeinterface as si
from spikeinterface import widgets, exporters, postprocessing, qualitymetrics, sorters
from workflow.pipeline import *
from workflow.utils.paths import (
    get_ephys_root_data_dir,
    get_raw_root_data_dir,
    get_processed_root_data_dir,
)

import numpy as np
from matplotlib import pyplot as plt


# %%
# Parameter Dictionaries
Batches = ["Batch 1" , "Batch 2" , "Batch 3"]
Drugs = ["4-AP" , "No Drug" , "Bicuculline" , "Tetrodotoxin"]
Organoids = {
    "Batch 1":["O09" , "O10" , "O11" , "O12"],
    "Batch 2":["O13" , "O14" , "O15" , "O16"],
    "Batch 3":["O17" , "O18" , "O19" , "O20"]
    }


# %%
# Random functions

def get_dir_info(clustering_output_dir):
    # take clustering output dir and extract batch , drug_name , organoid , start_time , end_time

    # find organoid , start time , end time
    query = ephys.ClusteringTask() & f"clustering_output_dir = '{clustering_output_dir}'"

    if len(query) == 1:

        key = query.fetch1("KEY")

        organoid = key["organoid_id"]
        experiment = key["experiment_start_time"]

        # find batch
        if organoid in Organoids["Batch 1"]:
            batch = "Batch 1"
        elif organoid in Organoids["Batch 2"]:
            batch = "Batch 2"
        elif organoid in Organoids["Batch 3"]:
            batch = "Batch 3"
        
        # find drug name
        drug = (culture.Experiment() & f"organoid_id = '{organoid}' AND experiment_start_time = '{experiment}'").fetch1("drug_name")

        info = {
            "batch":batch,
            "drug":drug,
            "organoid":organoid,
            "start_time":key["start_time"],
            "end_time":key["end_time"]
            }
        
    else:

        info = {clustering_output_dir:"error"}
    
    return info

def get_nest_dict(data , nest_dict , param , convert=False): # Make a nested dictionary (adds a "nest level")
    
    key_order = { # order that each param falls in the key ()
    "batch":0,
    "drug":1,
    "organoid":2,
    "start_time":3,
    "end_time":4
    }

    if not nest_dict: # Create new dictionary based on param

        # Get and Split Key Data
        keys = np.array(list(data))

        # Split data and get unique values for relative parameter
        split_keys = np.array([key.split('/') for key in keys])

        # Extract keys for specific param
        # If theres 2 parameters in one nest section (marked by "/")
        if "/" in param:

            param_list = param.split("/") # split param up
            param_key_list = split_keys[:,[key_order[p] for p in param_list]] # find the keys for each param
            param_keys = np.array(["/".join(pkey) for pkey in param_key_list]) # combine them into a single param key (ex: 4-AP/O10)

        else:
            
            # Simple extract
            param_keys = split_keys[:,key_order[param]]


        # Find unique values of the parameter
        new_keys , key_idx = np.unique(param_keys , return_index=True)
        new_keys = new_keys[np.argsort(key_idx)] # sorts in the order they were found

        for nkey in new_keys:
            
            # Find the data that corresponds to each unique parameter
            data_keys = keys[param_keys == nkey]

            # If convert is on
            if convert:

                grouped_data =[]
                for dkey in data_keys:
                    grouped_data.extend(data[dkey]) # group all data based on the keys in the previous statement
                    
                nest_dict[nkey] = grouped_data # add it to the dictionary

            else:

                nest_dict[nkey] = data_keys # if convert is False simply add the key to the dictionary

    else: # Nest dictionary based on param

        # Find the key and values of the current dict nest level
        old_values = list(nest_dict.values())
        old_keys = list(nest_dict)

        if isinstance(old_values[0] , dict): # if values are a dict (we need to go back another layer)

            for okey in old_keys:

                # go back another "nest" layer to a new dictionary
                new_dict = nest_dict[okey]

                # try and run the function again at that layer (If that level is a dict too it will keep repeating)
                nest_dict[okey] = get_nest_dict(data=data , nest_dict=new_dict , param=param , convert=convert)

            return nest_dict # Even though the return is here it will run the lines under in different iterations of the function (at lower layers)

        for okey in old_keys:
            
            # Get data to be grouped (for each group)
            keys = nest_dict[okey]

            # split and get unique values
            split_keys = np.array([key.split('/') for key in keys])

            if "/" in param:

                param_list = param.split("/") # split param up
                param_key_list = split_keys[:,[key_order[p] for p in param_list]] # find the keys for each param
                param_keys = np.array(["/".join(pkey) for pkey in param_key_list]) # combine them into a single param key (ex: 4-AP/O10)

            else:

                param_keys = split_keys[:,key_order[param]]

            # Find unique values of the parameter
            new_keys = np.unique(param_keys)

            # Make a new dictionary to group data
            nest_dict[okey] = {}
            for nkey in new_keys:
                
                data_keys = keys[param_keys == nkey]
           
                if convert:

                    grouped_data =[]
                    for dkey in data_keys:
                        grouped_data.extend(data[dkey]) # group all data based on the keys in the previous statement
                        
                    nest_dict[okey][nkey] = grouped_data

                else:

                    nest_dict[okey][nkey] = data_keys

    return nest_dict

def get_barX(data , bargap=.2 , groupgap=.2): # NEED TO CHANGE SO IT CAN WORK WITH ANY DICTIONARY
        # Get X values used in a bar plot
        # data = nested dictionary of data for x values
        #   first set of keys is for groups, next set of keys is for bars within the group
        # bargap = gap between bars (center to center)
        # groupgap = distance between groups 

        x_group = None
        dict1 = data

        xvalues = []
        for dict2 in dict1.values():
            
            if x_group is None:
                x_group = list(np.arange(len(dict2))*bargap)

            else:
                group_offset = x_group[-1] + groupgap + bargap
                x_group = list(np.arange(len(dict2))*bargap + group_offset)

            xvalues.append(x_group)

        return xvalues

def reorder_dict(dict1 , order):
    # Reorder dict keys acording to order

    new_dict = {}
    if set(dict1.keys()).issubset(set(order)): # Check if all dictionary keys are in order (all order doesn't need to be in keys)

        for newkey in order:

            try:
                new_dict[newkey] = dict1[newkey] # Try and enter value info into newdict with correct order
            except:
                continue # if newkey not in dict1 then go to next newkey

        return new_dict
    
    # If keys not a subset of order
    for key1 , value1 in dict1.items(): # iterate through dictionaries (in case they're nested)

        if isinstance(value1 , dict): # if dict1 is nested
            dict2 = value1

            new_dict[key1] = reorder_dict(dict1=dict2 , order=order) # attempt to reorder nested layer

        else:
            raise Exception("items in order not found in dictionary")
        
    return new_dict

def unnest_list(nested_list):
    # nested list = list, needs to be universally nested (each element is nested the same number of times) (can change this is needed)

    mylist = nested_list

    while isinstance(mylist[0] , list): # unnest list
        mylist = sum(mylist , [])

    flattened_list = mylist

    return flattened_list
# %%

class session:

    def spike_sorting_session(organoid_id , experiment_start_time , start_time , end_time , used_electrodes , paramset):    

        # create spike_sorting sessions
        session_info = dict(
            organoid_id=organoid_id,
            experiment_start_time=experiment_start_time,
            insertion_number=0,
            start_time=start_time,
            end_time=end_time,
            session_type="spike_sorting",
        )

        session_probe_info = dict(
            organoid_id=organoid_id,
            experiment_start_time=experiment_start_time,
            insertion_number=0,
            start_time=start_time,
            end_time=end_time,
            probe="Q983",  # probe serial number
            port_id="A",  # Port ID ("A", "B", etc.)
            used_electrodes=used_electrodes,  # empty if all electrodes were used
        )

        # Insert the session
        SPIKE_SORTING_DURATION = 120  # minutes

        # Start and end time of the session. It should be within the experiment time range
        start_time = datetime.strptime(session_info["start_time"], "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(session_info["end_time"], "%Y-%m-%d %H:%M:%S")
        duration = (end_time - start_time).total_seconds() / 60

        assert (
            session_info["session_type"] == "spike_sorting"
            and duration <= SPIKE_SORTING_DURATION
        ), f"Session type must be 'spike_sorting' and duration must be less than {SPIKE_SORTING_DURATION} minutes"
        
        ephys.EphysSession.insert1(session_info, ignore_extra_fields=True, skip_duplicates=True)

        ephys.EphysSessionProbe.insert1(
            session_probe_info, ignore_extra_fields=True, skip_duplicates=True
        )

        del session_probe_info["used_electrodes"]

        key = (ephys.EphysSession & session_info).fetch1("KEY")

        # determine sorter
        sorter_name = "spykingcircus2"
        si.sorters.get_default_sorter_params(sorter_name)

        # get cluster
        clustering_task = key | {"paramset_idx" : paramset}
        ephys.ClusteringTask.insert1(clustering_task , skip_duplicates=True)
        
        return clustering_task
# %%
# Get Data functions
class data:

    def get_tasks(global_key):
        # get clustering tasks which will contain data to be used (time segments and organoids)
        
        # global key = list of dictionaries of wanted Clustering Tasks - [{AND conditions} OR {AND conditions} OR ...]
        #   --> ex: [{"organoid_id":"O09"} , {"organoid_id":"O10" , "start_time":datetime(2023, 5, 18, 12, 25)}]
        #           = all tasks with organoid O09 or tasks with organoid O10 and start time 5/18/2023 , 12:25
        # key options: organoid_id , experiment_start_time , insertion_number , start_time , end_time , paramset_idx , clustering_output_dir

        # Get string key based on global key
        str_key = "" # initialize final string key

        for idx_OR , key in enumerate(global_key): # loop through global key (OR statements)
            
            str_OR = "" # intialize string for keys

            for idx_AND , (param , value) in enumerate(key.items()): # loop through individual keys (AND statements)

                str_AND = f"{param} = '{value}'" # create AND conditions

                if idx_AND == len(key)-1: # if the param,value pair isn't the last one (account for 0)
                    str_OR += str_AND # add onto OR condition without AND statement
                else:
                    str_OR += str_AND + " AND " # add onto OR condition with AND statement
                    
            if idx_OR == len(global_key)-1: # same logic as AND statements
                str_key += str_OR
            else:
                str_key += str_OR + " OR "

        # Extract wanted tasks
        tasks = ephys.ClusteringTask() & str_key
        
        return tasks

    def get_data(Tasks , global_query , Values):
        # get data values based on clustering task

        # Tasks = query of clustering tasks generated by get_tasks
        # global_query = query where to access the data
        # Values = wanted data values (ex: amplitude, firing rate, electrode, waveform)

        data = {}

        for task in Tasks: # loop through wanted values

            # get task info
            clustering_output_dir = task["clustering_output_dir"]
            task_info = get_dir_info(clustering_output_dir=clustering_output_dir)
            task_title = "/".join(map(str, task_info.values()))

            if task_title == "error":
                print(f"directory error for {clustering_output_dir}")

            else:
                # get task data query
                task_query = global_query & f"organoid_id='{task_info['organoid']}' AND start_time='{task_info['start_time']}' AND end_time='{task_info['end_time']}'"

                if len(task_query) == 0:

                    data[task_title] = "no data"
                    print(f"No data for {task_title}")

                else:
                    
                    data[task_title] = {}
                    for value in Values: # loop through tasks
                        
                        # extract value data
                        value_data = task_query.fetch(value)
                        
                        # put into dictionary
                        data[task_title][value] = value_data

        return data
    
    def group_data(data , batch=False , drug=False , organoid=False , start_time=False , end_time=False , dict_order=["batch" , "drug" , "organoid" , "start_time" , "end_time"]):
        # group data based on listed parameters (batch , drug , organoid , start_time , end_time)
        # when parameter set to true, the function will group based on that factor
        # assumes the key is batch/drug/organoid/start_time/end_time
        
        # data = input data dictionary --> keys = key (in format listed above) , values = whatever 
        # parameters = logicals
        # dict order = order in which the data will be grouped, each parameter will be a different "nest layer"
        #   ex: ["batch" , "drug" , "organoid"] will sort by batch then drug then organoid with a tripple nested dictionary
        #   if organoid is set to false the function will output a double nested dictionary sorted by batch and drug
        
        #   can use a / to group by 2 factors in one nest level
        #   ex: ["batch" , "drug/organoid"] will output a double nested dictionary grouped by batch then by organoid and drug

        logical_dict = {
            "batch":batch,
            "drug":drug,
            "organoid":organoid,
            "start_time":start_time,
            "end_time":end_time
        }

        # Create order of nest determined by dict_order and logical_dict
        order = []
        for param in dict_order:
            if "/" in param and all(logical_dict[p] for p in param.split("/")) or logical_dict[param]:

                order.append(param)

        grouped_data = {}
        for param in order: # loops through parameters determined by order

            # if it's the last grouping parameter, convert keys --> data
            convert = param == order[-1]

            # Create grouped data (nested dictionary) based on order (get_nest_dict is a far more complicated function)
            grouped_data = get_nest_dict(data=data , nest_dict=grouped_data , param=param , convert=convert)


        return grouped_data                

#%%
# Format Data functions

class format:

    def get_labels(dict1):
        # Get all keys in a nested dictionary (doesn't have to be nested), likely will be used as labels for plots
        # Outputs a similar dictionary with one level less of nest (is input is a {} output will be a list)

        labels = {}
        label_list = []
        for key1 , value1 in dict1.items():

            if isinstance(value1 , dict):
                dict2 = value1

                labels[key1] = format.get_labels(dict1=dict2) # iterate through nests

            else:
                label_list.append(key1) # Get list of keys
        
        if isinstance(value1 , dict):
            return labels
        else:
            return label_list
        
    def unest_layer(dict1 , take_average=False):
        # remove one layer of nest
        # if take_average=True --> the result will be averages of the values for the last key:value pairs
        # if False --> the result will be all values with one layer removed
        # ex: {A1:{B1:{C1:[1,5] , C2:[4,6,2]} , B2:{C3:[3,1] , C4:5}}} --> {A1: {B1:[3,6] , B2:[2,5]} } (True)
        #                                                              --> {A1: {B1:[1,5,4,6,2] , B2:[3,1,5]} } (False)

        new_dict = {}
        value_list = []

        for key1 , value1 in dict1.items():

            if isinstance(value1 , dict):
                dict2 = value1

                new_dict[key1] = format.unest_layer(dict1=dict2 , take_average=take_average)

            else:

                if take_average:
                    value_list.append(np.mean(value1))
                else:
                    value_list.extend(value1)

        if isinstance(value1 , dict):
            return new_dict 
        else:
            return value_list


    def horhist(data , bins = 50):
        # Input = Data Dictionary (values are a list (can be nested))
        #   Only Effects the bottom two nests (in a tripple nested dictionary the first set of key/value won't be effected)
        #   First nest = number of groups of horhists
        #   Second nest = number of horhists in a group
        #   if data is a single (nonnested) dictionary {} the output will be for one group

        # bin_data = What bins will be 
        #   bins remain constant throughout group
        #   if vector (list , numpy) --> bins will be that vector (the same for all groups)
        #   if int --> number of bins based on group values
        #   if None --> 50 bins based on group values

        dict1 = data # first dictionary (nested)
        horhist_data = {}
        bin_data = {}

        # Group Data
        bins_list = [] # 1D list 
        horhist_list = [] # 2D list
        for key1 , value1 in dict1.items(): # iterate through original data
            
            if isinstance(value1 , list): # if the value is data (needs to be in list form)
                calculate = True

                bins_list.extend(unnest_list(value1)) # put into global(groupwise) list
                horhist_list.append(unnest_list(value1))

            elif isinstance(value1 , dict):
                calculate = False
                dict2 = value1

                horhist_data[key1],bin_data[key1] = format.horhist(data=dict2 , bins = bins) # run function again at nested value               
                
            else:
                raise TypeError("data needs to be a dictionary(can be nested) with a list(can be nested) as values")
        
        if calculate: # if the dictionary values are a list, calculate the histogram data
            # Get Bin Data
            if isinstance(bins , int):
                _ , bin_data = np.histogram(a=bins_list , bins=bins)

            elif isinstance(bins , (list , np.ndarray)):
                bin_data = bins

            else:
                raise TypeError("bins needs to be type int,list,np.ndarray")
            
            # Get Horhist Data
            horhist_data_list = []          
            for horhistvalues in horhist_list:
                horhist_data_list.append(np.histogram(a=horhistvalues , bins=bin_data)[0])
            horhist_data = np.vstack(horhist_data_list)
            
        return horhist_data , bin_data
    
    def image(data , cbar_lims):
        # data = Input Data Dictionary (can be nested)
        #   last nest layer with data indicates the image plots
        #   the layer before that indicates groups, the cbar will be based on those groups
        # cbar_lims = [cbar_min , cbar_max] --> each on a 0-100 scale of the percentile of what the colorbar should include
        # THE DATA DICIONARY DOESN'T CHANGE

        dict1 = data    

        colorbar = {}
        values_list = []
        for key1 , value1 in dict1.items():

            if isinstance(value1 , dict):
                dict2 = value1

                values_list = format.image(data=dict2 , cbar_lims=cbar_lims)
                values_array = np.array(values_list)

                colorbar[key1] = []
                for lim in cbar_lims:
                    colorbar[key1].append(np.percentile(values_array , lim))   

            else:
                values_list.append(value1)

        if isinstance(value1 , dict):
            return colorbar
        else:
            return values_list

    def bar(data , bargap = .2 , groupgap = .2 , first_call = True):
        # Assuming data is a dictionary (could be nested) with values as type list: 
        # if points = True
        #   nest order = point values + bar/error values <--- group sorting <--- axis sorting <--- misc. sorting
        # if points = False
        #   nest order = bar values <-- group sorting <-- axis sorting <--- misc. sorting
                        
        # Makes new variables bar , error, and points 
        #   bar = mean of point values under the specific key
        #   error = standard deviationss of values under the specific key
        #   points = values which are under a specific key

        dict1 = data
        
        bar_data = {}
        error_data = {}
        points_data = {}

        bar_list = []
        error_list = []
        points_list = []
        x_list = []

        groupoffset = 0

        for key1 , value1 in dict1.items(): # Axis level - [drugs]

            if isinstance(value1 , dict):
                dict2 = value1
                get_points = True

                numpoints_list = []
                for key2 , value2 in dict2.items(): # Group level - [organoids]

                    if isinstance(value2 , dict): 
                        dict3 = value2
                        value_level = False

                        bar = bar_data[key1] = {}
                        error = error_data[key1] = {}
                        points = points_data[key1] = {}
                        
                        bar["data"] , error["data"] , points["data"] , x_list = format.bar(data = dict2 , first_call = False)

                    elif isinstance(value2 , list):
                        value_level = True

                        # put into value level list
                        bar_list.append(np.mean(value2))
                        error_list.append(np.std(value2))
                        points_list.extend(value2)
                        numpoints_list.append(len(value2))

                if value_level:
                    # Get group x values
                    xgroup = list(np.arange(len(dict2))*bargap + groupoffset)
                    groupoffset = xgroup[-1] + bargap + groupgap

                    for xidx , x in enumerate(xgroup):
                        x_list.extend([x]*numpoints_list[xidx])      

                # get x values for bar and error
                x_unique = list(np.unique(x_list))

                if not value_level or first_call:
                    if value_level:
                        bar = bar_data = {}
                        error = error_data = {}
                        points = points_data = {}

                        bar["data"] = bar_list
                        error["data"] = error_list
                        points["data"] = points_list 

                    # Store x values into global dictionary
                    bar["xvalues"] = x_unique
                    error["xvalues"] = x_unique
                    points["xvalues"] = list(x_list + ((np.random.random(len(x_list)))-1/2)*(bargap/2))

            elif isinstance(value1 , list):
                get_points = False

                # This will only happen if the original isn't nested
                bar_list.extend(value1)

                xgroup = list(np.arange(len(value1))*bargap + groupoffset)
                groupoffset = xgroup[-1] + bargap + groupgap
                x_list.extend(xgroup)
        
        if not get_points:
            bar_data["data"] = bar_list
            bar_data["xvalues"] = x_list

            return bar_data
            
        elif value_level and not first_call:
            return bar_list , error_list , points_list , x_list
        
        else:
            return bar_data , error_data , points_data



        
# %%
# Plot Data functions

class plot:

    def get_bar(xvalues , bar_data , barwidth = None):
        # make bar plot

        # xvalues = 1D numpy of xaxis values for the bars
        # bar_data = 1D numpy of bar heights
        # barwidth = width of bars
        if barwidth is None:
            barwidth = .2

        bar_ax = plt.bar(xvalues , bar_data , barwidth , edgecolor='k')

        return bar_ax
    
    def get_scatter(xvalues , scatter_data):
        # get scatter plot
        
        # xvalues = 1D numpy of x values for the points
        # scatter_data = 1D numpy of y values for the points

        scatter_ax = plt.scatter(xvalues , scatter_data)

        return scatter_ax
    
    def get_errorbar(xvalues , yvalues , errorbar_data):
        # get errorbars
        # xvalues = 1D numpy of x values for the errorbars
        # yvalues = 1D numpy of y values for the errorbars (center)
        # errrorbar_data = 1D numpy of errorbar heights (height from center (1/2))

        errorbar_ax = plt.errorbar(xvalues , yvalues , yerr=errorbar_data , fmt='o' , color='k' , capsize=4 , markersize=0)

        return errorbar_ax
    
    def get_line(line_data , xvalues = None):
        # get line plot

        # line = 1D numpy line to be drawn
        # x = 1D numpy or None 

        if xvalues is None:
            xvalues = np.arange(len(line_data))
        
        line_ax = plt.plot(xvalues , line_data)

        return line_ax
    
    def get_image(image_data):
        # get image plot

        image_ax = plt.imshow(image_data)

        return image_ax
    
    def get_hist(hist_data , bins = None):
        # get histogram plot

        # hist_data = data to be put into histogram plot (don't need to break up into bins before entering)
        # bins = bin values
            # if None --> default
            # if int --> # of bins
            # if 1D numpy or list --> bin values

        hist_ax = plt.hist(hist_data , bins=bins)

        return hist_ax
    
    def get_horhist(horhist_data , bins , groupgap = None):
        # get horizontal histogram plot

        # hist_amp = 2D numpy, each 1D numpy histogram amplitude values based on the bin values for a single group
        # bins = 1D numpy of the bin values for all groups
        # groupgap = gap between groups (baseline to baseline)(default is the max * 1.2)

        # horhist_ax = A nested list of the [[bars for group 1] [bars for group 2] ...]
                
        # determine groupgap if None
        if groupgap == None:
            groupgap = np.max(horhist_data) * 1.2

        # determine bin width
        bindiff = np.diff(bins)
        nbins = len(bindiff)

        # make sure dimensions match
        if not horhist_data.shape[1] == nbins:
            raise Exception("The group histogram amplitude and bin length need to agree (bin = amp+1)")
        
        # set global axis
        horhist_ax = []

        for group , grouphist in enumerate(horhist_data): # loop through groups
            
            # set group axis (with consistent x axis)
            gax = []

            for i in range(nbins): # loop through each bin

                # get plot values (for one bar) 
                plot_hist = [(group*groupgap , grouphist[i])] # (start , height)
                plot_bins = (bins[i] , bindiff[i]) # (start , width)

                # plot (append onto group axis (with individual bars))
                gax.append(plt.broken_barh(plot_hist , plot_bins))
            
            # Set xticks to baselines for each group
            plt.xticks(np.arange(group+1)*groupgap)

            horhist_ax.append(gax)
        
        return horhist_ax
    
    def get_figure(figure_key , figure_data):
        # Figure key = 1D or 2D numpy with string values determining the type of plot for each subplot
            # Can use / to have multiple plots on one subplot. ex: "bar/scatter/errobar" will make a barplot then scatter then error
        # Figure Data = 1D or 2D numpy. Each value within the numpy is a dicionary containing the data to be used. 
            # Key names will be the type of data, ex: for a line plot, {"line_data":data...}
        nrows , ncols = figure_key.shape

        # Generate Figure
        fig , ax = plt.subplots(nrows=nrows , ncols=ncols)

        plot_ax = np.empty((nrows,ncols) , dtype=object)

        # Plot data
        for x in range(nrows):

            for y in range(ncols):
                
                # Get Info based on subplot (axis) within figure
                axis_key = figure_key[x,y]
                axis_dict = figure_data[x,y]
                pax_dict = {}
                for key in axis_key.split("/"): # splits and iterates if there's a "/" (will just run once if not)
                
                    # Set current axis ((x,y) doesn't work if ax is 1D)
                    if nrows == ncols == 1:
                        plt.sca(ax)
                    elif nrows == 1:
                        plt.sca(ax[y])
                    elif ncols == 1:
                        plt.sca(ax[x])
                    else:
                        plt.sca(ax[x,y])
                    
                    # Get Data based on key
                    datadict = axis_dict[key]

                    # Plot Data based on which plot the key starts with (get individual plot axis (pax))
                    if key.startswith("bar_"):

                        if not "barwidth" in datadict:
                            datadict["barwidth"] = None

                        pax = plot.get_bar(xvalues=datadict["xvalues"] , bar_data=datadict["bar_data"] , barwidth=datadict["barwidth"])

                    elif key.startswith("errorbar_"):

                        pax = plot.get_errorbar(xvalues=datadict["xvalues"] , yvalues=datadict["yvalues"] , errorbar_data=datadict["errorbar_data"])

                    elif key.startswith("scatter_"):

                        pax = plot.get_scatter(xvalues=datadict["xvalues"] , scatter_data=datadict["scatter_data"])
                        
                    elif key.startswith("line_"):
                        
                        if not "xvalues" in datadict:
                            datadict["xvalues"] = None

                        pax = plot.get_line(line_data=datadict["line_data"] , xvalues=datadict["xvalues"])

                    elif key.startswith("image_"):

                        pax = plot.get_image(image_data=datadict["image_data"])

                    elif key.startswith("hist_"):

                        if not "bins" in datadict:
                            datadict["bins"] = None

                        pax = plot.get_hist(hist_data=datadict["hist_data"] , bins=datadict["bins"])

                    elif key.startswith("horhist_"):

                        if not "groupgap" in datadict:
                            datadict["groupgap"] = None

                        pax = plot.get_horhist(horhist_data=datadict["horhist_data"] , bins=datadict["bins"] , groupgap=datadict["groupgap"])

                    else:
                        raise Exception(f"Invalid Plot type at row = {x} and col = {y}. Must start with 'plottype_'")
                    
                    # Save pax in pax_dict
                    pax_dict[key] = pax

                plot_ax[x,y] = pax_dict


        return fig , ax , plot_ax