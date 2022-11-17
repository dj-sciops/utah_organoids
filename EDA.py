# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import numpy as np
import os, sys, struct
import ipywidgets as wg
from pathlib import Path
import matplotlib.pyplot as plt
# %matplotlib inline

# %%
def read_qstring(fid):
    """Read Qt style QString.

    The first 32-bit unsigned number indicates the length of the string (in bytes).
    If this number equals 0xFFFFFFFF, the string is null.

    Strings are stored as unicode.
    """

    (length,) = struct.unpack("<I", fid.read(4))
    if length == int("ffffffff", 16):
        return ""

    if length > (os.fstat(fid.fileno()).st_size - fid.tell() + 1):
        print(length)
        raise Exception("Length too long.")

    # convert length from bytes to 16-bit Unicode words
    length = int(length / 2)

    data = []
    for i in range(0, length):
        (c,) = struct.unpack("<H", fid.read(2))
        data.append(c)

    return "".join(chr(c) for c in data)


def read_header(fid):
    """Reads the Intan File Format header from the given file."""

    # Check 'magic number' at beginning of file to make sure this is an Intan
    # Technologies RHD2000 data file.
    (magic_number,) = struct.unpack("<I", fid.read(4))

    if magic_number != int("0xD69127AC", 16):
        raise Exception("Unrecognized file type.")

    header = {}
    # Read version number.
    version = {}
    (version["major"], version["minor"]) = struct.unpack("<hh", fid.read(4))
    header["version"] = version

    print("")
    print(
        "Reading Intan Technologies RHS2000 Data File, Version {}.{}".format(
            version["major"], version["minor"]
        )
    )
    print("")

    # Read information of sampling rate and amplifier frequency settings.
    (header["sample_rate"],) = struct.unpack("<f", fid.read(4))
    (
        header["dsp_enabled"],
        header["actual_dsp_cutoff_frequency"],
        header["actual_lower_bandwidth"],
        header["actual_lower_settle_bandwidth"],
        header["actual_upper_bandwidth"],
        header["desired_dsp_cutoff_frequency"],
        header["desired_lower_bandwidth"],
        header["desired_lower_settle_bandwidth"],
        header["desired_upper_bandwidth"],
    ) = struct.unpack("<hffffffff", fid.read(34))

    # This tells us if a software 50/60 Hz notch filter was enabled during
    # the data acquisition.
    (notch_filter_mode,) = struct.unpack("<h", fid.read(2))
    header["notch_filter_frequency"] = 0
    header["notch_filter_frequency"] = {1: 50, 2:60}[notch_filter_mode]

    (
        header["desired_impedance_test_frequency"],
        header["actual_impedance_test_frequency"],
    ) = struct.unpack("<ff", fid.read(8))
    (header["amp_settle_mode"], header["charge_recovery_mode"]) = struct.unpack(
        "<hh", fid.read(4)
    )

    frequency_parameters = {}
    frequency_parameters["amplifier_sample_rate"] = header["sample_rate"]
    frequency_parameters["board_adc_sample_rate"] = header["sample_rate"]
    frequency_parameters["board_dig_in_sample_rate"] = header["sample_rate"]
    frequency_parameters["desired_dsp_cutoff_frequency"] = header[
        "desired_dsp_cutoff_frequency"
    ]
    frequency_parameters["actual_dsp_cutoff_frequency"] = header[
        "actual_dsp_cutoff_frequency"
    ]
    frequency_parameters["dsp_enabled"] = header["dsp_enabled"]
    frequency_parameters["desired_lower_bandwidth"] = header["desired_lower_bandwidth"]
    frequency_parameters["desired_lower_settle_bandwidth"] = header[
        "desired_lower_settle_bandwidth"
    ]
    frequency_parameters["actual_lower_bandwidth"] = header["actual_lower_bandwidth"]
    frequency_parameters["actual_lower_settle_bandwidth"] = header[
        "actual_lower_settle_bandwidth"
    ]
    frequency_parameters["desired_upper_bandwidth"] = header["desired_upper_bandwidth"]
    frequency_parameters["actual_upper_bandwidth"] = header["actual_upper_bandwidth"]
    frequency_parameters["notch_filter_frequency"] = header["notch_filter_frequency"]
    frequency_parameters["desired_impedance_test_frequency"] = header[
        "desired_impedance_test_frequency"
    ]
    frequency_parameters["actual_impedance_test_frequency"] = header[
        "actual_impedance_test_frequency"
    ]

    header["frequency_parameters"] = frequency_parameters

    (
        header["stim_step_size"],
        header["recovery_current_limit"],
        header["recovery_target_voltage"],
    ) = struct.unpack("fff", fid.read(12))

    note1 = read_qstring(fid)
    note2 = read_qstring(fid)
    note3 = read_qstring(fid)
    header["notes"] = {"note1": note1, "note2": note2, "note3": note3}

    (header["dc_amplifier_data_saved"], header["eval_board_mode"]) = struct.unpack(
        "<hh", fid.read(4)
    )

    header["ref_channel_name"] = read_qstring(fid)

    # Create structure arrays for each type of data channel.
    header["spike_triggers"] = []
    header["amplifier_channels"] = []
    header["board_adc_channels"] = []
    header["board_dac_channels"] = []
    header["board_dig_in_channels"] = []
    header["board_dig_out_channels"] = []

    # Read signal summary from data file header.
    (number_of_signal_groups,) = struct.unpack("<h", fid.read(2))
    print("n signal groups {}".format(number_of_signal_groups))

    for signal_group in range(1, number_of_signal_groups + 1):
        signal_group_name = read_qstring(fid)
        signal_group_prefix = read_qstring(fid)
        (
            signal_group_enabled,
            signal_group_num_channels,
            signal_group_num_amp_channels,
        ) = struct.unpack("<hhh", fid.read(6))

        if (signal_group_num_channels > 0) and (signal_group_enabled > 0):
            for signal_channel in range(0, signal_group_num_channels):
                new_channel = {
                    "port_name": signal_group_name,
                    "port_prefix": signal_group_prefix,
                    "port_number": signal_group,
                }
                new_channel["native_channel_name"] = read_qstring(fid)
                new_channel["custom_channel_name"] = read_qstring(fid)
                (
                    new_channel["native_order"],
                    new_channel["custom_order"],
                    signal_type,
                    channel_enabled,
                    new_channel["chip_channel"],
                    command_stream,
                    new_channel["board_stream"],
                ) = struct.unpack(
                    "<hhhhhhh", fid.read(14)
                )  # ignore command_stream
                new_trigger_channel = {}
                (
                    new_trigger_channel["voltage_trigger_mode"],
                    new_trigger_channel["voltage_threshold"],
                    new_trigger_channel["digital_trigger_channel"],
                    new_trigger_channel["digital_edge_polarity"],
                ) = struct.unpack("<hhhh", fid.read(8))
                (
                    new_channel["electrode_impedance_magnitude"],
                    new_channel["electrode_impedance_phase"],
                ) = struct.unpack("<ff", fid.read(8))

                if channel_enabled:
                    if signal_type == 0:
                        header["amplifier_channels"].append(new_channel)
                        header["spike_triggers"].append(new_trigger_channel)
                    elif signal_type == 1:
                        raise Exception("Wrong signal type for the rhs format")
                        # header['aux_input_channels'].append(new_channel)
                    elif signal_type == 2:
                        raise Exception("Wrong signal type for the rhs format")
                        # header['supply_voltage_channels'].append(new_channel)
                    elif signal_type == 3:
                        header["board_adc_channels"].append(new_channel)
                    elif signal_type == 4:
                        header["board_dac_channels"].append(new_channel)
                    elif signal_type == 5:
                        header["board_dig_in_channels"].append(new_channel)
                    elif signal_type == 6:
                        header["board_dig_out_channels"].append(new_channel)
                    else:
                        raise Exception("Unknown channel type.")

    # Summarize contents of data file.
    header["num_amplifier_channels"] = len(header["amplifier_channels"])
    header["num_board_adc_channels"] = len(header["board_adc_channels"])
    header["num_board_dac_channels"] = len(header["board_dac_channels"])
    header["num_board_dig_in_channels"] = len(header["board_dig_in_channels"])
    header["num_board_dig_out_channels"] = len(header["board_dig_out_channels"])

    return header


# %%
INBOX = Path("/Users/tolgadincer/ClientData/Utah_Alex/2020Data/RawData/Organoid21")

time_filename = INBOX / "020820_estimsham/O21_estim2_200208_165037/time.dat"
header_filename = INBOX / "020820_estimsham/O21_estim2_200208_165037/info.rhs"

relative_paths = [
    "020820_estimsham/O21_estim2_200208_165037/amp-B-000.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-001.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-002.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-003.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-004.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-005.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-006.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-007.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-008.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-009.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-010.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-011.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-012.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-013.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-B-015.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-000.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-001.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-002.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-003.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-004.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-005.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-006.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-007.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-008.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-009.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-010.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-011.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-012.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-013.dat",
    "020820_estimsham/O21_estim2_200208_165037/amp-D-015.dat",
]
file_paths = [INBOX / x for x in relative_paths]


# %%
def read_ephys(file_paths, time_filename="time.dat"):
    time = (np.memmap(time_filename, dtype=np.int32))

    signals = np.empty([len(file_paths), len(time)])
    for i, file_path in enumerate(file_paths):
        signals[i, :] = np.memmap(
            file_path, dtype=np.int16)#, offset=n*size, shape=size
    #signals = signals * 0.195  # Convert to microvolts

    return signals, time


# %%
INBOX = Path("/Users/tolgadincer/ClientData/Utah_Alex/2020Data/RawData/Organoid21")
header_filename = INBOX / "020820_estimsham/O21_estim2_200208_165037/info.rhs"
with open(header_filename, "rb") as fid:
    header = read_header(fid)

# %%
signals, time = read_ephys(file_paths, time_filename)

increment = wg.IntSlider(value=300, min=0, max=1000, description='Increment:')
window = wg.IntRangeSlider(value=[0, 1000], min=0, max=9627519, description='Window:', readout=True, orientation='horizontal', step=increment.value, disabled=False, layout=wg.Layout(width="95%"))


def update_window(value):
    window.step = increment.value

window.observe(update_window)


def update(window):
    """Remove old lines from plot and plot new one"""    
    #[l.remove() for l in ax.lines]
    fig, ax = plt.subplots(figsize=(25, 20), dpi=500)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Signal (microvolts)')
    #ax.set_ylim([-500, 300])
    signal = signals[:, slice(*window)] * 0.195
    t = time[slice(*window)] / header["frequency_parameters"]["amplifier_sample_rate"]
    for i, s in enumerate(signal):
        ax.plot(t, s+i*100)#, label=relative_paths[i].split('/')[1])
    #plt.legend(bbox_to_anchor = (1.1, 1.))
    #ax.set_ylim()
    fig.canvas.draw()

display(increment)
wg.interact(update, window=window);
