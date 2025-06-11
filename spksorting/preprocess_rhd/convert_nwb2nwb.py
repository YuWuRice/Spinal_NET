"""Modify NWB metadata to for compatibility with DANDI upload requirements"""
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
from pynwb import NWBHDF5IO, NWBFile
from pynwb.ecephys import ElectricalSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO


from utils.rhd_folder import read_rhd_folder, add_imp_to_nwb
# from read_channel_info_script_oe import SESSION_XML_NAMING_PATTERN, DATETIME_STR_PATTERN, HEADSTAGE_NAME

N_CH = 32
ANIMAL_ID_INT = 2

def update_and_resize_nwb(input_nwbpath, output_nwbpath, metadata):
    """
    Update and resize an existing NWB file with new metadata.
    Helped by ChatGPT
    """
    # file operations
    nwbio_in = NWBHDF5IO(input_nwbpath, "r")
    nwbf_in : NWBFile = nwbio_in.read()
    # create new file with updated metadata
    nwbhead_description = metadata.get("session_desc", nwbf_in.session_description)
    nwbhead_start_time = metadata.get("start_time", nwbf_in.session_start_time)
    # nwbhead_identifier = metadata.get("identifier", nwbf_in.identifier)
    if "identifier" in metadata:
        nwbhead_identifier = metadata["identifier"]
    elif "identifier_top" in metadata:
        nwbhead_identifier = metadata["identifier_top"] + "_" + nwbhead_start_time.strftime("%Y%m%d-%H%M%S")
    else:
        nwbhead_identifier = nwbf_in.identifier
    nwbhead_experimenter = metadata.get("experimenter", nwbf_in.experimenter)
    nwbhead_lab = metadata.get("lab", nwbf_in.lab)
    nwbhead_institution = metadata.get("institution", nwbf_in.institution)
    nwbhead_expdesc = metadata.get("exp_desc", nwbf_in.experiment_description)
    nwbhead_session_id = metadata.get("session_id", nwbf_in.session_id)
    subject = metadata.get("subject", nwbf_in.subject)
    nwbf_out = NWBFile(
        session_description=nwbhead_description,
        identifier=nwbhead_identifier,
        session_start_time=nwbhead_start_time,
        experimenter=nwbhead_experimenter,
        lab=nwbhead_lab,
        institution=nwbhead_institution,
        experiment_description=nwbhead_expdesc,
        session_id=nwbhead_session_id,
        subject=subject,
    )
    # copy devices
    device_map = {}
    for name, device in nwbf_in.devices.items():
        new_device = nwbf_out.create_device(name=name, description=device.description)
        device_map[name] = new_device
    # copy electrode groups
    group_map = {}
    for name, group in nwbf_in.electrode_groups.items():
        new_group = nwbf_out.create_electrode_group(
            name=name,
            description=group.description,
            location=group.location,
            device=device_map[group.device.name]
        )
        group_map[name] = new_group
    # copy electrodes
    elec_idx_map = {} 
    # elec_idx_map is just a placeholder in case there really is 
    # arbitrary remapping of channels when creating a new NWB file.
    # print("# electrodes in source NWB:", len(nwbf_in.electrodes))
    # this line is copied from my custom Intan to NWB conversion script
    # TODO read columns in source file and create accordingly
    nwbf_out.add_electrode_column(name="label", description="Descriptive label")
    for idx in range(len(nwbf_in.electrodes)):
        row = nwbf_in.electrodes[idx]
        elec_kwargs = dict(
            group=group_map[row['group_name'].values[0]],
            id=idx, # assume id is 0 thru n_channels
            # id=row['id'],
            label=str(row['label'].values[0]),
            location="Spinal cord",
            # group_name=row['group_name'],
            rel_x=row['rel_x'].values[0],
            rel_y=row['rel_y'].values[0],
            rel_z=row['rel_z'].values[0],
            x=row['x'].values[0],
            y=row['y'].values[0],
            z=row['z'].values[0]
        )
        if "imp" in row:
            elec_kwargs["imp"] = row['imp'].values[0]
        nwbf_out.add_electrode(**elec_kwargs)
        elec_idx_map[idx] = idx # map original index to new index; so far this is transparent
    # quantize and copy data
    for name, item in nwbf_in.acquisition.items():
        if not isinstance(item, ElectricalSeries):
            continue
        print(f"Processing acquisition '{name}'")
        # Convert data to int16
        data = item.data[:]
        print(f"Data shape: {data.shape}, dtype: {data.dtype}")
        data_int16 = data.astype(np.int16)
        print("Data is converted to int16")
        del data
        data = None # free memory
        gc.collect() # collect garbage to free memory
        # data_int16 = data.astype(np.int16)
        # Map electrodes
        original_electrodes = item.electrodes
        new_electrodes = nwbf_out.create_electrode_table_region(
            region=[elec_idx_map[i] for i in original_electrodes.data[:]],
            description=original_electrodes.description
        )
        new_es = ElectricalSeries(
            name=name,
            data=H5DataIO(data_int16, compression="gzip"),
            electrodes=new_electrodes,
            starting_time=item.starting_time,
            rate=item.rate,
            conversion=item.conversion,
            offset=item.offset
        )
        nwbf_out.add_acquisition(new_es)
    
    nwbio_out = NWBHDF5IO(output_nwbpath, 'w')
    nwbio_out.write(nwbf_out)
    print(f"Saved converted file to: {output_nwbpath}")
    nwbio_in.close()
    nwbio_out.close()



if __name__ == "__main__":
    
    # S02 - 2
    session_infos = [
        {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230720/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230723/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230726/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230802/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230803/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230806/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230808/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230809/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230810/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230824/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230826/ephys_allday.nwb"},
        # {"session_nwbpath": "/storage/SSD_2T/spinal_stim_exp/processed/S02/20230831/ephys_allday.nwb"},
    ]
    session_folder_out = "/storage/wd_pcie1_4T/sc32_chronicAnimals/converted_nwb/animal2_S02/"
    get_session_identifier = lambda path_: "ChronicImplant2-" + path_.split("/")[-2] # e.g. "20230723"

    # chmap_csvpath = "/storage/SSD_2T/sc_chmaps/zigzag_rhs32_map.csv"
    # chmap_dict = {
    #     "map_style": "coordinates",
    #     "map_data": pd.read_csv(chmap_csvpath, header=None).values
    # }
    if not os.path.exists(session_folder_out):
        os.makedirs(session_folder_out)
    
    for session_info in session_infos:
        # session_datestr = get_oe_datestr(session_folder_raw)
        # session_datetime = datetime.datetime.strptime(session_datestr, "%Y-%m-%d_%H-%M-%S")
        # subject needs to be created for each NWB file separately, even if the info is the same
        session_nwbpath = session_info['session_nwbpath']
        sub = Subject(
            subject_id="Chronic Implant %d"%(ANIMAL_ID_INT),
            description="Chronic spinal cord implant mouse",
            species="Mus musculus",
            age="P08W/",
            sex="U",
        )
        metadata = {
            "session_desc": "Intan RHS data converted to NWB",
            "identifier_top": "Chronic Implant %d - "%(ANIMAL_ID_INT), # `identifier` will be populated by the conversion function
            # "start_time": session_datetime, # `start_time` will be populated by the conversion function
            "experimenter": "JZ",
            "lab": "Luan/Xie/Pfaff Labs",
            "institution": "Rice U & Salk Institute",
            "exp_desc": "Intraspinal recording of mouse lumbar spinal cord",
            "subject": sub,
        }
        assert session_nwbpath.endswith(".nwb"), "Session NWB path must end with .nwb"
        
        nwb_filename = get_session_identifier(session_nwbpath) + ".nwb"
        export_nwb_path = os.path.join(session_folder_out, nwb_filename)
        print("Converting session %s to %s..." % (session_nwbpath, export_nwb_path))
        update_and_resize_nwb(session_nwbpath, export_nwb_path, metadata)

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
        # if imp_csvpath is not None:
        #     add_imp_to_nwb(imp_csvpath, export_nwb_path, verbose=True)
        # else:
        #     add_imp_to_nwb(info_["rhd_fullfilenames"][0], export_nwb_path, verbose=True)
