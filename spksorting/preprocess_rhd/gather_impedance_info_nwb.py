'''
read channel info
4/23/2025 jz103
'''

import os
import gc
import warnings
from copy import deepcopy
from time import time
import re
import datetime
import json
import traceback
# import xml.etree.ElementTree as ET

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pynwb
from pynwb import NWBHDF5IO

VALID_SESSION_LAMBDA = lambda x: (('_' in x) and ('.' not in x) and ('__' not in x) and ('bad' not in x))
DATA_SAVE_FOLDER = "../_pls_ignore_chronic_ebl_data_250430"
DATETIME_STR_PATTERN = "%Y%m%d" # YYYYMMDD
SESSION_NAMING_PATTERN = r"([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])" # eg 20230806
# # RHD PARAMETERS
# SESSION_NAMING_PATTERN = r"[A-Za-z_ ]+_([0-9]+_[0-9]+)"
# # OPENEPHYS PARAMETERS
# SESSION_XML_NAMING_PATTERN = r"([0-9]+_[0-9]+)_Impedances.xml"
# DATETIME_STR_PATTERN = "(%Y)%m_%d"
# HEADSTAGE_NAME = 'B1'
# IMPEDANCE_MEASUREMENT_OFFSET_DAY = 2

# def get_datetimestr_from_filename(filename):
#     """
#         Assume the rhd filename takes the form of either
#         ParentPath/Animalname_YYMMDD_HHMMSS.rhd
#         or 
#         Animialname_YYMMDD_HHMMSS.rhd
#     """
#     tmp = filename.split("/")[-1].split("_")
#     return tmp[1]+'_'+tmp[2].split('.')[0]

def get_session_stat(session_folder):
    # sorting_subdir = "spksort_allday/mountainsort4"
    # sorting_dir = os.path.join(session_folder, sorting_subdir)
    # template_waveforms = np.load(os.path.join(sorting_dir, "sorted_waveforms", "templates_average.npy"))
    # single_unit_mask = pd.read_csv(os.path.join(sorting_dir, "accept_mask.csv"), header=None).values.squeeze().astype(bool)
    # sinmul_unit_mask = pd.read_csv(os.path.join(sorting_dir, "accept_mask_with_multi.csv"), header=None).values.squeeze().astype(bool)
    nwbfname = next(filter(lambda x: x.endswith(".nwb"), os.listdir(session_folder)))
    nwbio = NWBHDF5IO(os.path.join(session_folder, nwbfname), "r")
    nwbf = nwbio.read()
    imps = nwbf.electrodes.to_dataframe()["imp"].values
    nwbf = None
    nwbio.close()
    imps = imps[(imps>1e5) & (imps<6e6)]
    return imps

def process_one_animal(animal_name, session_folders, surgery_datestr, plot_axes):
    session_folders = sorted(session_folders)
    surgery_date = datetime.datetime.strptime(surgery_datestr, DATETIME_STR_PATTERN)
    session_datetimes = []
    session_imp_sets = []
    session_datetimestrs = []
    f_err = open("./tmp_errormsg.txt", "w")
    for session_folder in session_folders:
        try:
            if session_folder.endswith("/"):
                session_folder = session_folder[:-1]
            session_subfolder = os.path.basename(session_folder)
            datetimestr = re.match(SESSION_NAMING_PATTERN, session_subfolder)[1]
            session_datetime = datetime.datetime.strptime(datetimestr, DATETIME_STR_PATTERN)
            ch_impedances = get_session_stat(session_folder)
            session_imp_sets.append(ch_impedances)
            session_datetimes.append(session_datetime)
            session_datetimestrs.append(datetimestr)
        except Exception as e:
            traceback.print_exc(file=f_err)
            # break
            pass
    f_err.close()

    # timedelta relative to first session.
    timedelta_floats = np.array([(sdt - surgery_date).total_seconds() for sdt in session_datetimes])
    print("N_sessions_total", timedelta_floats.shape)

    imp_means = np.array([np.mean(k) for k in session_imp_sets])
    valid_ch_counts = np.array([session_imp_sets[i_session].shape[0] for i_session in range(timedelta_floats.shape[0])])
    plot_axes[0].plot(timedelta_floats, imp_means, label=animal_name, marker='.')
    plot_axes[1].plot(timedelta_floats, valid_ch_counts, label=animal_name, marker='.')
    return timedelta_floats, session_imp_sets, session_datetimestrs

def process_multi_animals(list_animals_metadata, save):
    fig1 = plt.figure(figsize=(10,5))
    ax1 = fig1.add_subplot(111)
    fig2 = plt.figure(figsize=(10,5))
    ax2 = fig2.add_subplot(111)
    # for i_animal, (animal_folder, surgery_datestr) in enumerate(animal_list):
    #     animal_name = os.path.basename(animal_folder)
    #     print(i_animal, animal_folder, animal_name)
    #     # timedelta_floats, units_per_channel, valid_timedelta_floats, p2p_amplitudes_mean, p2p_amplitudes_all, session_datetimestrs
    #     session_folders = list(map(lambda x: os.path.join(animal_folder, x), filter(lambda x: re.match(SESSION_NAMING_PATTERN, x) is not None, os.listdir(animal_folder))))
    for i_animal, animal_metadata in enumerate(list_animals_metadata):
        animal_name = animal_metadata["animal_id"]
        session_folders = [k[0] for k in animal_metadata["session_names"]]
        surgery_datestr = animal_metadata["surg_datestr"]
        print(i_animal, animal_name)
        timedelta_floats, ch_impedances, datetimestrs = process_one_animal(animal_name, session_folders, surgery_datestr, [ax1, ax2])
        ch_impedance_dict = dict(zip(["session%d"%(d) for d in range(len(ch_impedances))], ch_impedances))
        if save:
            np.savez(
                os.path.join(DATA_SAVE_FOLDER, animal_name+'_impedances.npz'),
                time_in_seconds=timedelta_floats,
                **ch_impedance_dict
            )
            df_save = pd.DataFrame()
            df_save['dayAfterSurgery'] = (timedelta_floats/(24*3600)).astype(int)
            df_save['datetime'] = datetimestrs
            df_save['impedances'] = ch_impedances
            df_save.to_csv(os.path.join(DATA_SAVE_FOLDER, animal_name+"_impedances.csv"), index=False)

    for ax in [ax1, ax2]:
        ax.legend()
        xtickmax = int(ax.get_xticks()[-1] / (24*3600))
        print(xtickmax)
        ax.set_xticks(np.arange(0, xtickmax, 10)*24*3600)
        ax.set_xticklabels(np.arange(0, xtickmax, 10))
        # ax.set_xticklabels(np.round(ax.get_xticks()/(24*3600)).astype(int))
        ax.set_xlabel("Days after Implantation")
    print("Setting Axis Labels")
    ax1.set_ylabel(r"Avg Impedance ($\Omega$)")
    ax2.set_ylabel(r"# Channels with Impedance < 3M$\Omega$")
    ax2.set_ylim([0, 32.5])
    print("Saving figures")
    # plt.subplots_adjust(bottom=0.1)
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_impedances.eps"))
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_impedances.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_valid_ch_cnts.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_valid_ch_cnts.eps"))
    for ax in [ax1,ax2]:
        ax.set_xlim([-1*(10*3600), 120*(24*3600)])
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_impedances_120days.eps"))
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_impedances_120days.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_valid_ch_cnts_120days.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_valid_ch_cnts_120days.eps"))
    plt.close()
    plt.close()


if __name__=="__main__":
    print(os.getcwd())
    print(os.listdir())
    from cfg_counting import list_animals_metadata
    if not os.path.exists(DATA_SAVE_FOLDER):
        os.makedirs(DATA_SAVE_FOLDER)
    process_multi_animals(list_animals_metadata, save=True)
