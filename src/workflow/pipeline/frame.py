# Import Modules
import datajoint as dj
from workflow import DB_PREFIX
from element_array_ephys.ephys_no_curation import map_channel_to_electrode

from workflow.pipeline import culture, ephys, mua, probe

import numpy as np
from random import randint
import bottleneck as bn
from scipy.signal import find_peaks
from datetime import timedelta

# Set up schema (connects to database and manages table creation)
schema = dj.schema(DB_PREFIX + "frame")

# Define Lookup Table 
@schema
class TimeFrameParamset(dj.Lookup):
    """
    Time frame extraction parameters for LFP and spike analyses. 
    """

    definition = """
    frame_param_idx: int  # Unique identifier for the frame parameter set
    ---
    num_frames: int  # Number of frames to extract
    min_per_frame: int  # Length of each frame in minutes
    """
    contents = [
        (1, 12, 5),  # 12 frames at 5 minutes each (1 hour total)
        (2, 4, 15), # 4 frames at 15 minutes each (1 hour total)
        (3, 8, 15), # 8 frames at 15 minutes each (2 hours total)
    ]

# Define Manual Table
@schema
class FrameSession(dj.Manual):
    """
    Manually define time boundaries for analysis of each organoid session.
    """

    definition = """ 
    -> culture.Experiment
    -> TimeFrameParamset
    start_boundary     : datetime # Start datetime for analysis
    end_boundary       : datetime # End datetime for analysis
    """

# Define Computed Table
@schema
class FrameAnalysis(dj.Computed):
    """
    Compute active time frames within defined analysis boundaries for the defined organoid session.
    """
    definition = """
    -> FrameSession
    ---
    num_processed_sessions: int # Number of sessions with available data within the analysis boundaries
    num_available_files: int # Number of available ephys files within the analysis boundaries
    """

    class ActiveTimeFrames(dj.Part):
        """
        Identify the "num_frames" most active time frames (length "sec_per_frame") within the analysis boundaries for each organoid session.
        """

        definition = """
        -> master
        frame_start: datetime # Start of active time frame
        frame_end: datetime   # End of active time frame
        ---
        frame_firing_rate: float # Firing rates for each frame
        """

    def make(self, key):
        
        # fetch electrode parameters
        num_elec_inside = (culture.NumElectrodesInside & key).fetch1('num_electrodes')

        # fetch frame parameters
        num_frames, min_per_frame = (TimeFrameParamset & key).fetch1('num_frames', 'min_per_frame')

        # fetch number of processed sessions and available files
        num_processed_sessions = len(mua.MUASpikes & f"organoid_id='{key['organoid_id']}'" & f"start_time BETWEEN '{key['start_boundary']}' AND '{key['end_boundary']}'")
        num_files = len(ephys.EphysRawFile & f"file_time BETWEEN '{key['start_boundary']}' AND '{key['end_boundary']}'")

        # fetch MUA values (needs to be previously )
        spike_rates, start_times, channel_ids = (mua.MUASpikes.Channel & 
                                                    f"organoid_id='{key['organoid_id']}'" &
                                                    f"start_time BETWEEN '{key['start_boundary']}' AND '{key['end_boundary']}'"
                                                    ).fetch('spike_rate', 'start_time', 'channel_idx')

        # convert channel ids to electrode indices
        probe_type = set((ephys.EphysSessionProbe * probe.Probe & key).fetch('probe_type'))
        if len(probe_type) != 1:
            raise ValueError(
                f"Couldn't identify probe type for {key} - expected one, found {len(probe_type)}"
            )
        electrode_ids = map_channel_to_electrode(probe_type.pop(), input_indices=channel_ids)

        time_vector, population_firing_vector = create_population_firing_vector(spike_rates, start_times, electrode_ids, num_elec_inside)

        # filter population firing vector - boxcar with the length of min_per_frame
        filtered_population_firing_vector = bn.move_mean(population_firing_vector, window=min_per_frame, min_count=1)

        # find active frames
        active_frames = find_active_frames(start_times, time_vector, filtered_population_firing_vector, population_firing_vector, num_frames, min_per_frame)

        # insert the parent FrameAnalysis record
        self.insert1({
            **key, 
            'num_processed_sessions': num_processed_sessions, 
            'num_available_files': num_files})

        # insert active frames (and acompannying ephys sessions)
        for active_frame in active_frames:

            # insert into frame table
            self.ActiveTimeFrames.insert1({
                **key,
                'frame_start': active_frame['frame_start'],
                'frame_end': active_frame['frame_end'],
                'frame_firing_rate': active_frame['frame_firing_rate'],
            }) 

# Define used functions
def create_population_firing_vector(spike_rates, start_times, electrode_ids, num_elec_inside):

    # create full time vector from recording start to end (1 minute increments)
    unique_start_times = np.unique(start_times)
    time_vector = np.arange(min(unique_start_times.astype("datetime64[m]")), max(unique_start_times.astype("datetime64[m]"))+np.timedelta64(1, 'm'), np.timedelta64(1, 'm')) # full array of recording timeline (needed to account for missing data)
    population_firing_vector = np.zeros(time_vector.shape)    

    # loop through start times and insert data into population firing vector
    for start_time in unique_start_times:

        time_bool = (start_times == start_time)

        # only consider electrodes inside organoid
        elec_bool = (electrode_ids < num_elec_inside)

        # sum valid electrodes for each time window (minute)
        time_index = np.where(time_vector == np.datetime64(start_time, 'm'))[0][0]
        population_firing_vector[time_index] = np.sum(spike_rates[time_bool & elec_bool])
    
    return time_vector, population_firing_vector

def find_active_frames(start_times, time_vector, filtered_population_firing_vector, population_firing_vector, num_frames, min_per_frame):

    # find active frames
    frame_indices, properties = find_peaks(filtered_population_firing_vector, height=0, distance=min_per_frame)
    frame_amplitudes = properties['peak_heights']

    # remove boundary peaks (these will raise an error when trying to extract burst windows)
    boundary_bool = (min_per_frame <= frame_indices)

    frame_indices = frame_indices[boundary_bool]
    frame_amplitudes = frame_amplitudes[boundary_bool]
    
    # find most active regions -> extract windows
    active_frame_indices = frame_indices[np.argsort(frame_amplitudes)[-num_frames:]]  # indexes of the most active peaks
    
    active_frames = []
    for active_frame_idx in active_frame_indices:
        
        # determine frame boundaries
        frame_bounds = np.array([-min_per_frame, 0]) + active_frame_idx + 1

        # find frame metrics
        start_time, end_time = np.unique(start_times[np.isin(start_times.astype("datetime64[m]"), time_vector[frame_bounds])])
        frame_firing_rate = np.mean(population_firing_vector[frame_bounds[0]:frame_bounds[1]])

        # extract frame info
        active_frames.append(
            {
                'frame_start': start_time,
                'frame_end': end_time - timedelta(seconds = 1),
                'frame_firing_rate': frame_firing_rate
            }
        )
    
    return active_frames      