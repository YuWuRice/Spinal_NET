"""Convert Open Ephys data to NWB format and be compatible with DANDI upload requirements"""
import os
import gc
import warnings
from copy import deepcopy
from time import time
import re
import datetime
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import pynwb
from pynwb.file import Subject

from openEphys import Binary
from utils.nwb_utils import initiate_nwb
from read_channel_info_script_oe import SESSION_XML_NAMING_PATTERN, DATETIME_STR_PATTERN, HEADSTAGE_NAME

N_CH = 32

# def walk_dict(dict_node, depth=0):
#     for k in dict_node.keys():
#         print("  "*depth + k)
#         if isinstance(dict_node[k], dict):
#             # print('haha')
#             walk_dict(dict_node[k], depth=depth+1)
#         else:
#             print("  "*(depth+1), type(dict_node[k]))

def get_data(dict_node):
    """Assume the dict has a linear structure with random key names and arbitrary depth, and eventually only one piece of data inside it"""
    _, first_value = list(dict_node.items())[0]
    if isinstance(first_value, dict):
        return get_data(first_value)
    return first_value

def convert_one_session(session_folder_raw, export_nwb_path, channel_map_full, metadata):
    if os.path.exists(export_nwb_path):
        print("  NWB file %s already exists, skipping conversion." % (export_nwb_path))
        return None
    ts_session = time()
    print("  Starting session: %s" % (session_folder_raw))
    data_dict, fs_dict = Binary.Load(session_folder_raw)#, Experiment=0, Recording=1)
    data_float = get_data(data_dict) # in uV
    data_ephys_short = data_float[:,:N_CH].astype(np.int16) # (n_samples, n_channels)
    del data_float
    data_float = None
    gc.collect()
    sample_freq = get_data(fs_dict)
    print("    data.shape=", data_ephys_short.shape, "F_SAMPLE=", sample_freq)
    # write to mda
    n_ch= data_ephys_short.shape[0]
    n_samples = data_ephys_short.shape[1]
    # mdapath = os.path.join(session_folder_mda, "converted_data.mda")
    # writer = DiskWriteMda(mdapath, (n_ch, n_samples), dt="int16")
    # writer.writeChunk(data_ephys_short, i1=0, i2=0)
    # del data_ephys_short
    gc.collect()
    print("  Session data loaded in %.2f sec" % (time()-ts_session))
    info_struct = {}
    info_struct['sample_freq'] = sample_freq
    info_struct['notch_freq'] = None
    info_struct['chs_info'] = {"OpenEphys": "O"}
    info_struct['n_samples'] = n_samples
    # info_struct is returned so that the calling context can write it to disk
    recording_info = {
        "sample_rate": float(sample_freq)
    }
    initiate_nwb(export_nwb_path, data_ephys_short, recording_info, channel_map_full, metadata)
    # TODO create NWB file
    return info_struct

def get_oe_datestr(session_folder):
    """Get the date string from the session folder name."""
    if session_folder.endswith('/'):
        session_folder = session_folder[:-1]
    namestr = session_folder.split("/")[-1]
    t = re.match(r"^[0-9][0-9][0-9]_(.*?)$", namestr)
    print("Date str", t[0], t[1])
    return t[1]

def read_impedance_xml(xml_fname):
    root = ET.parse(xml_fname).getroot()
    for headstage in root:
        if headstage.tag != "HEADSTAGE" or headstage.attrib['name'] != HEADSTAGE_NAME:
            continue
        # chs_numbers0 = [ch.attrib['number'] for ch in headstage]
        chs_impedance = np.array([float(ch.attrib['magnitude']) for ch in headstage])
        return chs_impedance
    raise ValueError("No headstage named %s found in XML file %s" % (HEADSTAGE_NAME, xml_fname))

if __name__ == "__main__":
    # session_folders_raw = [
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/006_2022-02-21_14-15-55",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/007_2022-02-27_15-09-38",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/008_2022-03-04_12-04-03",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/009_2022-03-10_13-20-23",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/012_2022-03-17_15-46-11",
    #     # "/storage/wd_pcie1_4T/sc32_BenMouse0/013_2022-03-20_13-27-50",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/014_2022-03-29_16-01-33",
    # ]
    # impedance_xmlpaths = [
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_21_Impedances.xml",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_27_Impedances.xml",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/3_4_Impedances.xml",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/3_10_Impedances.xml",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/3_17_Impedances.xml",
    #     # "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/3_20_Impedances.xml",
    #     "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/3_29_Impedances.xml",
    # ]
    session_folders_raw = [
        "/storage/wd_pcie1_4T/sc32_BenMouse0/001_2022-02-12_20-08-59",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/002_2022-02-12_20-21-53",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/003_2022-02-13_15-00-04",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/004_2022-02-13_15-11-00",
        # "/storage/wd_pcie1_4T/sc32_BenMouse0/005_2022-02-20_15-50-07",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/016_2022-04-27_16-47-43",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/017_2022-04-28_15-15-56",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/018_2022-04-29_13-29-54",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/019_2022-04-30_16-25-12",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/020_2022-05-01_20-01-57",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/021_2022-05-02_16-52-53",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/022_2022-05-03_16-46-19",
    ]
    impedance_xmlpaths = [
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_12_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_12_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_13_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/2_13_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/4_27_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/4_28_Impedances.xml",
        "/storage/wd_pcie1_4T/sc32_BenMouse0/imp_xmls/4_29_Impedances.xml",
        None,
        None,
        None,
        None,
    ]
    session_folder_out = "/storage/wd_pcie1_4T/sc32_BenMouse0/converted_nwb"
    chmap_csvpath = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/spksorting/geom_channel_maps/ChannelMap_Ben.csv"
    chmap_dict = {
        "map_style": "coordinates",
        "map_data": pd.read_csv(chmap_csvpath, header=None).values
    }
    if not os.path.exists(session_folder_out):
        os.makedirs(session_folder_out)
    
    for session_folder_raw, imp_xmlpath in zip(session_folders_raw, impedance_xmlpaths):
        session_datestr = get_oe_datestr(session_folder_raw)
        session_datetime = datetime.datetime.strptime(session_datestr, "%Y-%m-%d_%H-%M-%S")
        # subject needs to be created for each NWB file separately, even if the info is the same
        sub = Subject(
            subject_id="Chronic Implant 1",
            description="Chronic spinal cord implant mouse",
            species="Mus musculus",
            age="P08W/",
            sex="U",
        )
        metadata = {
            "session_desc": "OpenEphys data converted to NWB",
            "identifier": "Chronic Implant 1 - " + session_datestr,
            "start_time": session_datetime,
            "experimenter": "BT",
            "lab": "Luan/Xie/Pfaff Labs",
            "institution": "Rice U & Salk Institute",
            "exp_desc": "Intraspinal recording of mouse lumbar spinal cord",
            "subject": sub,
        }
        
        if session_folder_raw.endswith('/'):
            nwb_filename = os.path.basename(session_folder_raw[:-1]) + ".nwb"
        else:
            nwb_filename = os.path.basename(session_folder_raw) + ".nwb"
        export_nwb_path = os.path.join(session_folder_out, nwb_filename)
        print("Converting session %s to NWB..." % (session_folder_raw))
        convert_one_session(
            session_folder_raw, export_nwb_path, chmap_dict, metadata
        )

        # add DANDI-required metadata (subject)
        # nwb_io = pynwb.NWBHDF5IO(export_nwb_path, "r+")
        # nwbfile = nwb_io.read()
        # print("subject:", nwbfile.subject)
        # if hasattr(nwbfile, "subject") and nwbfile.subject is not None:
        #     print("Subject already exists in NWB file, skipping.")
        # else:
        #     nwbfile.subject = sub
        #     nwb_io.write(nwbfile)
        # nwb_io.close()
        
        # add impedance
        if imp_xmlpath is not None:
            imps = read_impedance_xml(imp_xmlpath)
            nwb_io = pynwb.NWBHDF5IO(export_nwb_path, "a")
            nwb = nwb_io.read()
            if "imp" in nwb.electrodes.colnames:
                print("Column 'imp' already exists in NWB file, skipping.")
            else:
                nwb.electrodes.add_column(name="imp", description="the impedance of the electrode, in ohms", data=imps)
                nwb_io.write(nwb)
            nwb_io.close()
            mwb_io2 = pynwb.NWBHDF5IO(export_nwb_path, "r")
            nwb2 = mwb_io2.read()
            print(nwb2.electrodes.to_dataframe())
            mwb_io2.close()
