"""Convert Intan RHD data to NWB format and be compatible with DANDI upload requirements"""
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


from utils.rhd_folder import read_rhd_folder, add_imp_to_nwb
# from read_channel_info_script_oe import SESSION_XML_NAMING_PATTERN, DATETIME_STR_PATTERN, HEADSTAGE_NAME

N_CH = 32
ANIMAL_ID_INT = 3

if __name__ == "__main__":
    
    # Nora - 5
    # session_infos = [
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221117_225954"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221118_222513"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221130_094643"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221204_204553"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221207_081815"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/nora_221213_224340"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/Nora_230113_170031"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/Nora_230224_163014"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/tosort/nora_221116_114205"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nora_112522_7refOut/Weekly_Recordings/tosort/nora_221122_185629"},
    # ]
    # session_folder_out = "/storage/wd_pcie1_4T/sc32_chronicAnimals/converted_nwb/animal5_nora/"

    # Nacho - 4
    # session_infos = [
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210907_204305"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210908_212657"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210909_191046"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210910_211048"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210915_110424"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210917_162917"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210922_130346"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_210928_190207"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_211006_121226"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_211019_162829"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_211109_131436"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_211126_151258"},
    #     {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Nacho_090721_1um_4refOut_600um/nacho_awake_220201_170805"},
    # ]
    # session_folder_out = "/storage/wd_pcie1_4T/sc32_chronicAnimals/converted_nwb/animal4_nacho/"

    # Mustang - 3
    session_infos = [
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/2022 Animals/Mustang_220114_202913"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220117_140130"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/GaitTestMustang/Mustang_220120_215625"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/2022 Animals/Mustang_220123_183709"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220203_130448"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220208_150824"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220215_171504"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220218_201717"},
        {"session_folder_raw": "/media/xlsmb/xl_spinal_cord_electrode/Animals/active_Animals/Mustang_011422_DoubleShank_6refOut/Mustang_220225_184110"},
    ]
    session_folder_out = "/storage/wd_pcie1_4T/sc32_chronicAnimals/converted_nwb/animal3_mustang/"

    chmap_csvpath = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/spksorting/geom_channel_maps/map.csv"
    chmap_dict = {
        "map_style": "coordinates",
        "map_data": pd.read_csv(chmap_csvpath, header=None).values
    }
    if not os.path.exists(session_folder_out):
        os.makedirs(session_folder_out)
    
    for session_info in session_infos:
        # session_datestr = get_oe_datestr(session_folder_raw)
        # session_datetime = datetime.datetime.strptime(session_datestr, "%Y-%m-%d_%H-%M-%S")
        # subject needs to be created for each NWB file separately, even if the info is the same
        session_folder_raw = session_info['session_folder_raw']
        imp_csvpath = session_info.get('imp_csvpath', None)
        sub = Subject(
            subject_id="Chronic Implant %d"%(ANIMAL_ID_INT),
            description="Chronic spinal cord implant mouse",
            species="Mus musculus",
            age="P08W/",
            sex="U",
        )
        metadata = {
            "session_desc": "OpenEphys data converted to NWB",
            "identifier_top": "Chronic Implant %d - "%(ANIMAL_ID_INT), # `identifier` will be populated by the conversion function
            # "start_time": session_datetime, # `start_time` will be populated by the conversion function
            "experimenter": "YW/NS",
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
        info_ = read_rhd_folder(
            session_folder_raw,
            expose_to_ram=False,
            use_memmap=False,
            export_nwb_path=export_nwb_path,
            channel_map=chmap_dict,
            metadata=metadata,
            channel_mask=None,
            amplifier_rawbits=True,
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
        if imp_csvpath is not None:
            add_imp_to_nwb(imp_csvpath, export_nwb_path, verbose=True)
        else:
            add_imp_to_nwb(info_["rhd_fullfilenames"][0], export_nwb_path, verbose=True)
