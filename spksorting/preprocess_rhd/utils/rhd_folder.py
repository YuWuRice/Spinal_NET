"""
The script for reading rhd folder and converting it to 
(1) a memory-mapped HDF5 or 
(2) dict of ndarrays in RAM or
(3) NWB. Notice that NWB stores data in (n_chs, n_samples) format.

"""
import os
import sys
import re
import datetime
import gc
from collections import OrderedDict
import xml.etree.ElementTree as ET

import numpy as np
import h5py
import pandas as pd
import tqdm
import pynwb

from .load_intan_rhd_format_updated import read_data, read_header
from . import rhd_io_utils as rhdio

class NoStdOut():
    def write(self, x): pass
    def flush(self, x=None): pass
NOSTDOUT = NoStdOut()

def load_rhd_file_silently(filename, amplifier_rawbits):
    """
    Load RHD file without printing anything to stdout.
    """
    save_stdout = sys.stdout
    sys.stdout = NOSTDOUT
    rhs_readout_parsed = read_data(filename, amplifier_rawbits=amplifier_rawbits)
    sys.stdout = save_stdout
    return rhs_readout_parsed


RHD_CONV_FACTOR = {
    "conversion": 0.195,
    "offset": -32768*0.195
}

def is_ephys_folder(foldername):
    return re.match(r"([a-zA-Z0-9_\-]+)_(\d{6}_\d{6})", foldername) is not None


TEMP_FOLDER = None
def set_temp_folder(folder_str):
    global TEMP_FOLDER
    TEMP_FOLDER = folder_str
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)



def get_rhd_timestamp(rhd_filename: str):
    x = re.match("([a-zA-Z0-9_\-]+)_([0-9]+_[0-9]+)\.rhd", rhd_filename)
    # fname_prefix=x[1]
    rec_datetimestr = x[2] # yymmdd_HHMMSS
    rec_datetime = datetime.datetime.strptime(rec_datetimestr, "%y%m%d_%H%M%S")
    return rec_datetime



def read_rhd_folder(
        rhd_foldername: str, expose_to_ram: bool, use_memmap: bool, 
        export_nwb_path: str | None = None, 
        channel_map: dict | None = None,
        metadata = None,
        channel_mask: np.ndarray | None = None,
        amplifier_rawbits: bool = False):
    """
        `rhd_foldername` should include a series of rhd files and 
        one `settings.xml`
        TODO add support for `settings.xml`
        `channel_map` : dict with following keys:
            `map_style`: either "coordinates" or "map_by_shank"
            `map_path`: str, path to the map file (csv)
        `channel_mask` : np.ndarray of bool, shape (n_chs,), True for channels to be kept
        `amplifier_rawbits`: whether the parsed amplifier data are in float64 or raw bits in Intan
    """
    
    rhd_filenames = sorted(
        list(filter(lambda x: x.endswith(".rhd"), os.listdir(rhd_foldername))),
        key=get_rhd_timestamp
    )
    rhd_fullfilenames = list(map(
        lambda x: os.path.join(rhd_foldername, x), rhd_filenames
    ))
    
    session_start_time = get_rhd_timestamp(rhd_filenames[0])

    if expose_to_ram and use_memmap:
        mode = "load_memmap"
    elif expose_to_ram:
        mode = "load_ram"
    else:
        mode = "conversion_only"
    
    # initialize the data structure with the first read rhd data
    rhd_readout_parsed = load_rhd_file_silently(rhd_fullfilenames[0], amplifier_rawbits=amplifier_rawbits)
    if mode=="load_memmap":
        assert TEMP_FOLDER is not None
        # create numpy memmaps with HDF5
        h5_tmpfilename = os.path.join(TEMP_FOLDER, "temp_rhd_data.h5")
        # store data as parsed since we are reading it instantly
        print("Creating temporary HDF5 file for rhd data")
        rhd_hdf5 = rhdio.initiate_temp_hdf5(h5_tmpfilename, rhd_readout_parsed, channel_mask)
    elif mode=="load_ram":
        # Everything is in RAM without memmap
        # just create a list for concantenation later on
        amplifier_data = [] # Amplifier data
        dc_amplif_data = [] # DC amplifier data (decide if manadatory or optional?)
        dig_in_data = []    # digital input data
        f_sample = None     # sampling frequency
        channel_info = None # channel info (names, etc.)
        channel_impd = None # channel impedance
    elif mode=="conversion_only":
        assert export_nwb_path is not None
        assert channel_map is not None
        if "map_data" not in channel_map:
            print("Reading channel map from:", channel_map["map_path"])
            channel_map["map_data"] = pd.read_csv(
                channel_map["map_path"], header=None
                ).values.squeeze().astype(int)
        metadata["start_time"] = session_start_time
        if "identifier" not in metadata:
            if "identifier_top" in metadata:
                metadata["identifier"] = metadata["identifier_top"] + "_" + session_start_time.strftime("%y%m%d_%H%M%S")
            else:
                metadata["identifier_top"] = "data_" + session_start_time.strftime("%y%m%d_%H%M%S")
            
        if not os.path.exists(os.path.dirname(export_nwb_path)):
            os.makedirs(os.path.dirname(export_nwb_path))
        if amplifier_rawbits:
            data_conv = RHD_CONV_FACTOR
        else:
            data_conv = None
        rhd_nwb = rhdio.initiate_nwb(export_nwb_path, rhd_readout_parsed, channel_map, metadata, channel_mask, data_conv) # should return None
        # rhd_nwb.close()
        # save data to disk with small RAM usage
        # TODO Consider whether to store data AS-IS or parsed
        # AS-IS: more sufficient; less conversion overhead.
        # Parsed: more convenient for later use. DO PARSED
    else:
        raise ValueError("Mode did not match any supported candidates")
    # important to delete unused data and free up memory
    del rhd_readout_parsed
    gc.collect()
    # read and append the rest of the files
    for i_rhd in tqdm.tqdm(range(1, len(rhd_fullfilenames))):
        rhdpath = rhd_fullfilenames[i_rhd]
        rhd_readout_parsed = load_rhd_file_silently(rhdpath, amplifier_rawbits=amplifier_rawbits)
        if mode=="load_memmap":
            rhdio.append_temp_hdf5(rhd_hdf5, h5_tmpfilename, rhd_readout_parsed, channel_mask)
        elif mode=="load_ram":
            raise NotImplementedError
        elif mode=="conversion_only":
            rhdio.append_nwb(rhd_nwb, export_nwb_path, rhd_readout_parsed, channel_mask)
        else:
            raise ValueError("Mode did not match any supported candidates")
        # important to delete unused data and free up memory
        del rhd_readout_parsed
        gc.collect()
    
    # finally
    if mode=="load_memmap":
        return rhd_hdf5
    elif mode=="load_ram":
        raise NotImplementedError
    elif mode=="conversion_only":
        ret_dict = {
            "session_start_time": session_start_time,
            "rhd_filenames": rhd_filenames,
            "rhd_fullfilenames": rhd_fullfilenames,
        }
        return ret_dict
    else:
        raise ValueError("Mode did not match any supported candidates")
    
    



# def intan2nwb_recurse_cat(intan_dname, proc_dname, channel_map, metadata, nwbname="cat_day.nwb"):
#     """
#     Rercursively walk through a folder, convert and concat all rhd folders
#     into one NWB file. This is useful for broken-into-pieces sessions
#     recorded on one day.
#     """
#     # get all the Intan folders
#     intan_folders_dict = OrderedDict()
#     for dirpath, _, filenames in os.walk(intan_dname):
#         intanfilenames = list(filter(lambda x: x.endswith("rhd"), filenames))
#         if len(intanfilenames)==0:
#             continue # Not an Ephys folder
#         intan_folders_dict[dirpath] = sorted(intanfilenames, key=get_rhd_timestamp)


def intans2nwb_cat(ephys_dnames, proc_dname, channel_map, metadata, nwb_fname, 
    sort_by_time=True, amplifier_rawbits=False, channel_masks=None):
    """
    Given a list `ephys_dnames` of ephys folders; read their rhd files and
    concatenate them into one NWB file. This is useful for broken-into-pieces
    sessions recorded on one day.
    Returns a dict of which raw rhd folder starts from which index.
    TODO test the added option to store raw uint16 bits from Intan
    """
    if not os.path.exists(proc_dname):
        os.makedirs(proc_dname)
    nwbpath = os.path.join(proc_dname, nwb_fname)
    
    # read channel maps
    if "map_data" not in channel_map:
        channel_map["map_data"] = pd.read_csv(
            channel_map["map_path"], header=None
            ).values.squeeze().astype(int)
    
    # count ephys files
    ephys_files_tuples = [] # rhd filenames for each session (rhd folder)
    session_start_stamps_dict = OrderedDict()
    for ephys_dname in ephys_dnames:
        rhd_filenames = sorted(
            list(filter(lambda x: x.endswith(".rhd"), os.listdir(ephys_dname))),
            key=get_rhd_timestamp
        )
        ephys_files_tuples.append((ephys_dname, rhd_filenames))
        session_start_stamps_dict[ephys_dname] = get_rhd_timestamp(rhd_filenames[0])
    if sort_by_time:
        # ephys_dnames_sorted = sorted(ephys_dnames, key=lambda x: session_start_stamps_dict[x])
        ephys_files_tuples = sorted(ephys_files_tuples, key=lambda x: session_start_stamps_dict[x[0]])
    beg_samples_dict = OrderedDict() # start index for each session (rhd folder)
    total_samples_cnter = 0
    # now convert 
    rhd_nwb = None
    for i_session, (ephys_dname, rhd_filenames) in tqdm.tqdm(enumerate(ephys_files_tuples), total=len(ephys_files_tuples)):
        # keep track of total samples (which index each session starts from)
        beg_samples_dict[ephys_dname] = total_samples_cnter
        ch_mask = channel_masks[i_session]
        for i_rhd in range(len(rhd_filenames)):
            rhdpath = os.path.join(ephys_dname, rhd_filenames[i_rhd])
            rhd_readout_parsed = load_rhd_file_silently(rhdpath, amplifier_rawbits=amplifier_rawbits)
            # NWB file manuvering
            if i_session==0 and i_rhd==0:
                # first rhd file in first session is different because of metadata
                session_start_time = session_start_stamps_dict[ephys_dname]
                metadata["start_time"] = session_start_time
                if amplifier_rawbits:
                    data_conv = RHD_CONV_FACTOR
                else:
                    data_conv = None
                rhdio.initiate_nwb(nwbpath, rhd_readout_parsed, channel_map, metadata, mask=ch_mask, data_conv=data_conv)
            else:
                rhdio.append_nwb(rhd_nwb, nwbpath, rhd_readout_parsed, mask=ch_mask)
            # keep track of total samples
            total_samples_cnter = total_samples_cnter + rhd_readout_parsed["amplifier_data"].shape[1]
            del rhd_readout_parsed
            gc.collect()
    return beg_samples_dict, total_samples_cnter


def add_imp_to_nwb(intan_imp_obj, nwbpath, verbose=False):
    """
    Add Intan-CSV-format/RHD-format/RHD-header impedence measurement to NWB file.
    intan_imp_obj : could be the csv-format impedance file OR or a RHD file where there is impedance measurement
    """
    if isinstance(intan_imp_obj, str) and intan_imp_obj.endswith(".csv"):
        print("Loading impedance measurement CSV file onto NWB")
        imp_table = pd.read_csv(intan_imp_obj)
        imp_native_chids = list(map(lambda x: int(re.match("[ABCD]-([0-9][0-9][0-9])", x)[1]), imp_table["Channel Number"].values))
        imp_ohms = imp_table["Impedance Magnitude at 1000 Hz (ohms)"].values
    else:
        if isinstance(intan_imp_obj, str) and intan_imp_obj.endswith(".rhd"):
            print("Loading impedance measurement RHD file onto NWB")
            f = open(intan_imp_obj, "rb")
            x = read_header(f, verbose=False)
        elif isinstance(intan_imp_obj, dict):
            print("Loading RHD header object onto NWB")
            x = intan_imp_obj
        else:
            raise ValueError("Unrecognized intan_imp_obj format. Must be one of {csv path (str), rhd path (str) or rhd header object (dict)}")
        imp_native_chids = [k["native_order"] for k in x["amplifier_channels"]]
        imp_ohms = np.array([k["electrode_impedance_magnitude"] for k in x["amplifier_channels"]])
        if np.all(imp_ohms==0):
            raise ValueError("RHD header suggests no impedance measurement! Aborting")
    # print(imp_native_chids, imp_ohms)


    # read NWB file
    nwb_io = pynwb.NWBHDF5IO(nwbpath, "a")
    nwb = nwb_io.read()

    ch_imps_for_nwb = [] # impedence values to store in NWB

    assert ("imp" not in nwb.electrodes.colnames), "imp column already found in NWB file"

    for elec in nwb.electrodes:
        tmp = elec.label.values
        if not (len(tmp)==1 and tmp.dtype==object and isinstance(tmp[0], str)):
            raise AssertionError("unexpected elec.label format")
        ch_labelstr = tmp[0]
        ch_native_id = int(re.match("native([0-9]+)_ovr([0-9]+)_shank([0-9]+)", ch_labelstr)[1])
        ch_imp = imp_ohms[imp_native_chids.index(ch_native_id)]
        ch_imps_for_nwb.append(ch_imp)

    nwb.electrodes.add_column(name="imp", description="the impedance of the electrode, in ohms", data=ch_imps_for_nwb)
    print(nwb.electrodes.to_dataframe())
    nwb_io.write(nwb)
    nwb_io.close()
    if verbose:
        print("SAVED AND OPENING AGAIN TO CHECK THE CHANGE")
        mwb_io2 = pynwb.NWBHDF5IO(nwbpath, "r")
        nwb2 = mwb_io2.read()
        print(nwb2.electrodes.to_dataframe())
        mwb_io2.close()
