'''
Count chronic stats of a mouse for EBL implantations
20250501
'''
import os
import json
import re
import datetime
import traceback
from collections import OrderedDict
# import typing

import shutil
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
# font = {# 'family' : 'monospace',
#         # 'weight' : 'bold',
#         'size'   : 26}

# matplotlib.rc('font', **font)


AMP_LIMIT_UV = 500
FR_LIMIT_HZ = 0.5

# fixed storage structure for spinal cord project chronic data
# SESSION_NAMING_PATTERN = {}
# DATETIME_STR_PATTERN = {}
# SESSION_NAMING_PATTERN["RHD"] = r"[A-Za-z_ ]+_([0-9]+_[0-9]+)"
DATETIME_STR_PATTERN = "%Y%m%d" # YYYYMMDD
SESSION_NAMING_PATTERN = r"([0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])" # eg 20230806
# SESSION_NAMING_PATTERN["OPENEPHYS"] = r"[0-9]+_([0-9]+-[0-9]+-[0-9]+_[0-9]+-[0-9]+-[0-9]+)"
# DATETIME_STR_PATTERN["OPENEPHYS"] = "%Y-%m-%d_%H-%M-%S"

DATA_SAVE_FOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_ebl_data_250430"

SORTING_SUBDIRS = [
    "spksort_allday/mountainsort4",
    "spksort_allday/ms4_whiten_bothpeaks_thr4d5",
    "spksort_allday/ms4_whiten_ebl128-18",
    "spksort_allday/ms4_whiten_conventional",
    "spksort_allday/ms4_whiten_bothpeaks_thr4d5_upto1100",
]

def get_session_stat(session_folder):
    template_waveforms = None
    for sorting_subdir in SORTING_SUBDIRS:
        sorting_dir = os.path.join(session_folder, sorting_subdir)
        try:
            template_waveforms = np.load(os.path.join(sorting_dir, "sorted_waveforms", "templates_average.npy"))
            single_unit_mask = pd.read_csv(os.path.join(sorting_dir, "accept_mask.csv"), header=None).values.squeeze().astype(bool)
            sinmul_unit_mask = pd.read_csv(os.path.join(sorting_dir, "accept_mask_with_multi.csv"), header=None).values.squeeze().astype(bool)
            m = pd.read_csv(os.path.join(sorting_dir, "sorted_waveforms", "quality_metrics", "metrics.csv"))
            print("Successfully loaded from %s"%(sorting_dir))
            break
        except:
            continue
    if template_waveforms is None:
        raise ValueError
    n_ch = template_waveforms.shape[2]
    # n_clus = template_waveforms.shape[0]
    firing_rates = m["firing_rate"]
    snrs = m["snr"]
    template_peaks = np.max(template_waveforms, axis=1) # (n_clus, n_ch)
    template_troughs = np.min(template_waveforms, axis=1)
    template_p2ps = template_peaks - template_troughs
    p2p_amplitudes = np.max(template_p2ps, axis=1) # (n_clus, )
    single_unit_mask[p2p_amplitudes>AMP_LIMIT_UV] = False
    single_unit_mask[firing_rates<FR_LIMIT_HZ] = False
    sinmul_unit_mask[p2p_amplitudes>AMP_LIMIT_UV] = False
    sinmul_unit_mask[firing_rates<FR_LIMIT_HZ] = False
    p2p_amplitudes = p2p_amplitudes[sinmul_unit_mask]
    n_single_units = np.sum(single_unit_mask)
    n_sing_or_mult = np.sum(sinmul_unit_mask)
    stat_dict = {}
    stat_dict['n_single_units'] = n_single_units
    stat_dict['n_sing_or_mult'] = n_sing_or_mult
    stat_dict['template_peaks'] = template_peaks
    stat_dict['n_ch'] = n_ch
    stat_dict['p2p_amplitudes'] = p2p_amplitudes
    stat_dict['snrs'] = snrs
    stat_dict['firing_rates'] = firing_rates
    return stat_dict

def process_one_animal(animal_name, session_folders, surgery_datestr, plot_axes):
    session_folders = sorted(session_folders)
    surgery_date = datetime.datetime.strptime(surgery_datestr, DATETIME_STR_PATTERN)
    session_datetimes = []
    session_stats = {}
    session_stats['n_single_units'] = []
    session_stats['n_sing_or_mult'] = []
    session_stats['n_ch'] = []
    session_stats['p2p_amplitudes'] = []
    session_stats["snrs"] = []
    session_stats["firing_rates"] = []
    session_datetimestrs = []
    f_err = open("./tmp_errormsg.txt", "w")
    for session_folder in session_folders:
        try:
            if session_folder.endswith("/"):
                session_folder = session_folder[:-1]
            session_subfolder = os.path.basename(session_folder)
            print("session_subfolder:", session_subfolder)
            datetimestr = re.match(SESSION_NAMING_PATTERN, session_subfolder)[1]
            session_datetime = datetime.datetime.strptime(datetimestr, DATETIME_STR_PATTERN)
            stat_dict = get_session_stat(session_folder)
            session_stats['n_single_units'].append(stat_dict['n_single_units'])
            session_stats['n_sing_or_mult'].append(stat_dict['n_sing_or_mult'])
            session_stats['n_ch'].append(stat_dict['n_ch'])
            session_stats['p2p_amplitudes'].append(stat_dict['p2p_amplitudes'])
            session_stats['snrs'].append(stat_dict['snrs'])
            session_stats['firing_rates'].append(stat_dict['firing_rates'])
            session_datetimes.append(session_datetime)
            session_datetimestrs.append(datetimestr)
            print(session_subfolder, stat_dict['n_single_units'], stat_dict['n_sing_or_mult'])
        except Exception as e:
            traceback.print_exc(file=f_err)
            # break
            continue
    f_err.close()

    # timedelta relative to first session.
    timedelta_floats = np.array([(sdt - surgery_date).total_seconds() for sdt in session_datetimes])
    print("N_sessions_total", timedelta_floats.shape)
    # fig = plt.figure(figsize=(10,5))
    # ax = fig.add_subplot(111)
    units_per_channel = np.array(session_stats['n_sing_or_mult'])/np.array(session_stats['n_ch'])
    plot_axes[0].plot(timedelta_floats, units_per_channel, label=animal_name, marker='.')
    # ax.plot(session_datetimes, np.array(session_stats['n_single_units'])/np.array(session_stats['n_ch']), label='# single-units')
    # ax.legend()
    # plt.xticks(session_datetimes, rotation=45)
    

    # fig = plt.figure(figsize=(10,5))
    # ax = fig.add_subplot(111)
    valid_session_ids = np.where(np.array(session_stats['n_sing_or_mult'])>0)[0]
    p2p_amplitudes_mean = [np.mean(session_stats['p2p_amplitudes'][sid]) for sid in valid_session_ids]
    firing_rates_mean = [np.mean(session_stats['firing_rates'][sid]) for sid in valid_session_ids]
    snrs_mean = [np.mean(session_stats['snrs'][sid]) for sid in valid_session_ids]
    valid_timedelta_floats = timedelta_floats[valid_session_ids]
    plot_axes[1].plot(valid_timedelta_floats, p2p_amplitudes_mean, label=animal_name, marker='.')
    p2p_amplitudes_all = session_stats['p2p_amplitudes']
    firing_rates_all = session_stats['firing_rates']
    snrs_all = session_stats['snrs']
    ret = {
        "timedelta_floats": timedelta_floats,
        "units_per_channel": units_per_channel,
        "valid_timedelta_floats": valid_timedelta_floats,
        "p2p_amplitudes_mean": p2p_amplitudes_mean,
        "p2p_amplitudes_all": p2p_amplitudes_all,
        "snrs_mean": snrs_mean,
        "snrs_all":  snrs_all,
        "firing_rates_mean": firing_rates_mean,
        "firing_rates_all":  firing_rates_all,
        "session_datetimestrs": session_datetimestrs,
        "n_ch": session_stats['n_ch']
    }
    return ret
    # return timedelta_floats, units_per_channel, valid_timedelta_floats, p2p_amplitudes_mean, p2p_amplitudes_all, session_datetimestrs, session_stats['n_ch']
    
    # # ax.plot(session_datetimes, np.array(session_stats['n_single_units'])/np.array(session_stats['n_ch']), label='# single-units')
    # # ax.legend()
    # plt.xticks(timedelta_floats, np.round(timedelta_floats/(24*3600)).astype(int))#, rotation=45)
    # plt.subplots_adjust(bottom=0.2)
    # plt.savefig(os.path.join(result_folder, "amplitudes.png"))
    # plt.close()

def process_multi_animals(animal_list, save, output_folder):
    fig1 = plt.figure(figsize=(10,5))
    ax1 = fig1.add_subplot(111)
    fig2 = plt.figure(figsize=(10,5))
    ax2 = fig2.add_subplot(111)
    # for i_animal, (animal_folder, surgery_datestr) in enumerate(animal_list):
        # animal_name = os.path.basename(animal_folder)
        # print(i_animal, animal_folder, animal_name)
        # timedelta_floats, units_per_channel, valid_timedelta_floats, p2p_amplitudes_mean, p2p_amplitudes_all, session_datetimestrs
        # session_folders = list(map(lambda x: os.path.join(animal_folder, x), filter(lambda x: re.match(SESSION_NAMING_PATTERN, x) is not None, os.listdir(animal_folder))))
    for i_animal, animal_metadata in enumerate(animal_list):
        animal_name = animal_metadata["animal_id"]
        session_folders = [k[0] for k in animal_metadata["session_names"]]
        surgery_datestr = animal_metadata["surg_datestr"]
        print(i_animal, animal_name)
        save_dict = process_one_animal(animal_name, session_folders, surgery_datestr, [ax1, ax2])
        if save:
            np.savez(
                os.path.join(output_folder, animal_name+"_firings.npz"),
                timedelta_floats=save_dict['timedelta_floats'],
                units_per_channel=save_dict['units_per_channel'],
                valid_timedelta_floats=save_dict['valid_timedelta_floats'],
                p2p_amplitudes_mean=save_dict['p2p_amplitudes_mean'],
                p2p_amplitudes_all=np.array(save_dict['p2p_amplitudes_all'], dtype=object),
                firing_rates_mean=save_dict['firing_rates_mean'],
                firing_rates_all=np.array(save_dict['firing_rates_all'], dtype=object),
                snrs_mean=save_dict['snrs_mean'],
                snrs_all=np.array(save_dict['snrs_all'], dtype=object),
                )
            df_save = pd.DataFrame()
            df_save['dayAfterSurgery'] = (save_dict['timedelta_floats']/(24*3600)).astype(int)
            df_save['datetime'] = save_dict['session_datetimestrs']
            df_save['n_units'] = [len(p2p_amplitudes) for p2p_amplitudes in save_dict['p2p_amplitudes_all']]
            df_save['n_channels'] = save_dict['n_ch']
            df_save['amplitudes_accepted_units'] = save_dict['p2p_amplitudes_all']
            df_save['firing_rates_accepted_units'] = save_dict['firing_rates_all']
            df_save['snrs_accepted_units'] = save_dict['snrs_all']
            df_save.to_csv(os.path.join(output_folder, animal_name+"_firings.csv"), index=False)

    for ax in [ax1, ax2]:
        ax.legend()
        # ax.set_xticks(np.arange(0, 61, 10)*24*3600)
        # ax.set_xticklabels(np.arange(0, 61, 10))
        # ax.set_xticklabels(np.round(ax.get_xticks()/(24*3600)).astype(int))
        xtickmax = int(ax.get_xticks()[-1] / (24*3600))
        # print(xtickmax)
        ax.set_xticks(np.arange(0, xtickmax, 20)*24*3600)
        ax.set_xticklabels(np.arange(0, xtickmax, 20))
        ax.set_xlabel("Days after Implantation")
        # ax.set_xlim([-1*(10*3600), 60*(24*3600)])
    ax1.set_ylabel("#Units")
    ax2.set_ylabel(r"Avg Amplitude ($\mu V$)")
    ax2.set_ylim([0, 220])
    # for ax in [ax1,ax2]:
    #     ax.set_xlim([-1*(10*3600), ax.get_xlim()[1]+40*24*3600])
    # plt.subplots_adjust(bottom=0.1)
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_n_units.eps"))
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_n_units.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_ampltud.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_ampltud.eps"))
    for ax in [ax1,ax2]:
        ax.set_xlim([-1*(10*3600), 120*(24*3600)])
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_n_units_120days.eps"))
    fig1.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_n_units_120days.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_ampltud_120days.png"))
    fig2.savefig(os.path.join(DATA_SAVE_FOLDER, "_pls_ignore_ampltud_120days.eps"))
    plt.close()
    plt.close()


if __name__=="__main__":
    # animals_list = [
    #     # ("/storage/SSD_2T/spinal_stim_exp/processed/S02", "20230713"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/JAN018", "20250210"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL20", "20250317"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL16", "20250110"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11", "20240818"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL22", "20250401"),
    #     ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL07", "20250604"),
    # ]
    from cfg_counting import list_animals_metadata
    n_animals = len(list_animals_metadata)
    print("STARTING")
    if not os.path.exists(DATA_SAVE_FOLDER):
        os.makedirs(DATA_SAVE_FOLDER)
    process_multi_animals(list_animals_metadata , save=True, output_folder=DATA_SAVE_FOLDER)
    