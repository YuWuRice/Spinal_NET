"""
plotcurve_chronic_scatters.py
Plot chronic experiement performance statistics. Each experiemnt is a dataset of (n_chs) or (n_units)
So each experiemnt is plotted as scatters on a vertical line (same time axis)
"""
import os
from copy import deepcopy
from collections import OrderedDict
from itertools import groupby
import warnings

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager
from matplotlib.colors import ListedColormap
from matplotlib.cm import get_cmap
import scipy.stats as stats

print("- matplotlib version:", matplotlib.__version__)
# matplotlib.font_manager.get_font_names()
# flist = matplotlib.font_manager.get_fontconfig_fonts()
# print(flist)
# names = [matplotlib.font_manager.FontProperties(fname=fname, size=22).get_name() for fname in flist]
# print(names)
font = {'style' : 'normal',
        'weight' : 'normal',
        'size'   : 22}

matplotlib.rc('font', **font)
CMAP_STR = "tab10" #"Set3"

# YLABEL = "Amplitude (\u03bcV)"
# FEATURESET_OF_INTEREST = "p2p_amplitudes"
# YLIM = None

# YLABEL = "Firing rate (spikes/sec)"
# FEATURESET_OF_INTEREST = "firing_rates"
# YLIM = [0, 25]

# YLABEL = "SNR (single unit)"
# FEATURESET_OF_INTEREST = "snrs_su"
# YLIM = None

YLABEL = "SNR"
FEATURESET_OF_INTEREST = "snrs"
YLIM = None

# FOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_data_250422"
# PLOTFOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_plots_250422"
# ["BenMouse0", "nora", "mustang", "nacho", "S02"]# ["BenMouse0", "BenMouse1", "nora", "mustang", "nacho"]

# FOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_ebl_data_250430"
# PLOTFOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_ebl_plots_250430"
# GROUP_NICE = ["EBL10", "EBL11", "EBL12"]

FOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_pl32_data_250516"
PLOTFOLDER = "/home/xlruut/jiaao_workspace/legacy/Spinal_NET/_pls_ignore_chronic_pl32_plots_250516"
GROUP_NICE = ["BenMouse0", "nora", "mustang", "nacho", "S02"]

ANIMAL_NAME_LUT = {
    "BenMouse0": "Chronic Implant 1",
    "nora": "Chronic Implant 5",
    "mustang": "Chronic Implant 3",
    "nacho": "Chronic Implant 4",
    "S02": "Chronic Implant 2",
}

PLOT_NAME = "interval"
N_DAYS = 84
PERIOD_IN_DAYS = 7
# PLOT_NAME = "daily"
# N_DAYS = 14
# PERIOD_IN_DAYS = 2


def read_chronic_animal_npz(npzpath, keep_valid_only=True):
    # TODO process keep_valid_only argument
    npzdict = np.load(npzpath, allow_pickle=True)
    ddict = dict(npzdict.items())
    # print("DBG %s ddict.keys()" % (npzpath), list(ddict.keys()))

    if keep_valid_only:
        assert np.all(np.diff(ddict["valid_timedelta_floats"])>0) # assert that the sessions are already sorted by datetime
        valid_session_ids = np.where(np.array(ddict['units_per_channel'])>0)[0]
        ddict["day_after_surgery"] = (ddict['valid_timedelta_floats']/(24*3600)).astype(int)
        for kn, v in ddict.items():
            if len(v) > len(valid_session_ids):
                ddict[kn] = v[valid_session_ids]
    else: 
        assert np.all(np.diff(ddict["timedelta_floats"])>0) # assert that the sessions are already sorted by datetime
        ddict["day_after_surgery"] = (ddict['timedelta_floats']/(24*3600)).astype(int)
    # if "units_per_channel" in ddict:
        # warnings.warn()
    # ddict["units_per_channel"] = ddict["n_sing_or_mult"]/ddict["n_ch"] 
    return ddict

def truncate_timeseries_in_dict(animal_dict, first_day, last_day):
    daysstamp = animal_dict["day_after_surgery"]
    mask_inds = (daysstamp>=first_day) & (daysstamp<=last_day)
    newdict = {}
    for kname, timeseries in animal_dict.items():
        newdict[kname] = timeseries[mask_inds]
    return newdict

def remove_datapoints(animal_dict, inds_to_remove):
    n_sessions = len(animal_dict["day_after_surgery"])
    inds_mask = np.ones(n_sessions).astype(bool)
    inds_mask[inds_to_remove] = 0
    new_dict = {}
    for kname, val in animal_dict.items():
        if isinstance(val, np.ndarray):
            new_dict[kname] = val[inds_mask]
        else:
            new_dict[kname] = [v for i, v in enumerate(val) if inds_mask[i]]
    return new_dict


def custom_curation(animal_name, animal_dict):
    # just switch (animal_name) and pour in shit code for curation
    if animal_name.lower()=="tacoma":
        animal_dict = remove_datapoints(animal_dict, [-1])
    elif animal_name.lower()=="yogurt":
        animal_dict = remove_datapoints(animal_dict, [-1,-2,-3])
    return animal_dict

def group_by_period(animal_dict, duration_in_days, period_in_days):
    animal_dict = truncate_timeseries_in_dict(animal_dict, 0, duration_in_days-1)
    daysstamp = animal_dict["day_after_surgery"]
    n_sessions = len(daysstamp)
    sess_inds = list(range(n_sessions))
    sess_inds_grouped = [[] for _ in range(int(np.ceil(duration_in_days/period_in_days)))]
    for period, inds in groupby(sess_inds, key=lambda k: (daysstamp[k]//period_in_days)):
        sess_inds_grouped[period] = list(inds)
    # print("DBG sess_inds_grouped", sess_inds_grouped)
    # print("DBG days_grouped", [[daysstamp[i] for i in inds] for inds in sess_inds_grouped])
    # n_weeks_actual = len(sess_inds_grouped)
    # if (duration_in_weeks is not None) and (n_weeks_actual<duration_in_weeks):
    #     sess_inds_grouped.extend([[] for _ in range(duration_in_weeks-n_weeks_actual)])
    animal_dict_grouped = {}
    for kname, timeseries in animal_dict.items():
        # print(kname)
        # print("DBG", n_sessions, timeseries.shape)
        animal_dict_grouped[kname] = [timeseries[inds] for inds in sess_inds_grouped]
    # print(animal_dict_grouped.keys())
    return animal_dict_grouped

def stat_datapoints_by_period(dict_animals, duration_in_days, period_in_days):
    """make a boxplot of unit yield for given animals; x-axis it in days """
    # first group the sessions by week for each animal
    dict_animals_gbw = {}
    animal_names = list(dict_animals.keys())
    for animal_name, animal_dict in dict_animals.items():
        dict_animals_gbw[animal_name] = group_by_period(animal_dict, duration_in_days, period_in_days)
    n_periods = int(np.ceil(duration_in_days/period_in_days))
    datasets = []
    for i_week in range(n_periods):
        tmp_datasets_all_animals = [np.array([])]# [np.concatenate(ad["impedances_all"][i_week].tolist()) for ad in dict_animals_gbw.values()]
        for adict in dict_animals_gbw.values():
            # print(adict.keys())
            datasets_this_animal = adict["%s_all"%(FEATURESET_OF_INTEREST)][i_week].tolist() # list of ndarrays
            if len(datasets_this_animal)>0:
                tmp_datasets_all_animals.extend(datasets_this_animal)
        datasets.append(np.concatenate(tmp_datasets_all_animals))
        # print("DBG datasets[-1].shape", datasets[-1].shape)
    means = np.array([(np.mean(dataset) if dataset.shape[0]>0 else np.nan) for dataset in datasets ])
    # std_errors = np.array([(np.std(dataset)/np.sqrt(dataset.shape[0]) if dataset.shape[0]>0 else np.nan) for dataset in datasets ])
    std_errors = np.array([(stats.sem(dataset) if dataset.shape[0]>1 else np.nan) for dataset in datasets])
    days_approx = np.arange(0, duration_in_days, period_in_days) # a rough count of days as a potential x-axis when plotting
    # ax.boxplot(datasets, positions=3.5+np.arange(duration_in_weeks)*7, widths=4, showfliers=False)
    return means, std_errors, days_approx

def plot_shaded_datapoints(dict_animals, duration_in_days, animal_colors_, ax=None):
    dict_animals_t = {}
    for animal_name, animal_dict in dict_animals.items():
        dict_animals_t[animal_name] = truncate_timeseries_in_dict(animal_dict, 0, duration_in_days-1)
    if ax is None:
        _, ax = plt.subplots()
    for animal_name, animal_dict in dict_animals_t.items():
        animal_label = ANIMAL_NAME_LUT.get(animal_name, animal_name)
        # ax.plot(animal_dict["day_after_surgery"], animal_dict["impedances_mean"], label=animal_name, linewidth=0.3, alpha=0.3, marker='s')
        ax.plot(
            animal_dict["timedelta_floats"]/(24*3600), 
            animal_dict["%s_mean"%(FEATURESET_OF_INTEREST)], 
            label=animal_label, linewidth=0.3, alpha=1, marker='s', 
            color=animal_colors_[animal_name]
        )
        # scatters = []
        for k in range(len(animal_dict["day_after_surgery"])):
            # print(animal_dict["%s_all"%(FEATURESET_OF_INTEREST)][k])
            this_day=animal_dict["timedelta_floats"][k]/(24*3600)
            ax.scatter(
                [this_day]*len(animal_dict["%s_all"%(FEATURESET_OF_INTEREST)][k]), 
                animal_dict["%s_all"%(FEATURESET_OF_INTEREST)][k], 
                alpha=1, marker='s', s=2, color=animal_colors_[animal_name]
            )
    plt.legend(loc="best", prop={"size":16}, borderpad=0.6)
    # ax.legend(handles=[(pltt,) for pltt in plots ], 
    #       labels=[animal_name for animal_name in dict_animals.keys()])
    return ax


if __name__ == "__main__":

    if not os.path.exists(PLOTFOLDER):
        os.makedirs(PLOTFOLDER)
    
    npznames = sorted(list(filter(lambda x: x.endswith("_firings.npz"), os.listdir(FOLDER))))
    print(npznames)
    dict_animals = OrderedDict()
    for npzname in npznames:
        aname = npzname.split("_")[0]
        npzfullpath = os.path.join(FOLDER, npzname)
        adict = read_chronic_animal_npz(npzfullpath)
        dict_animals[aname] = custom_curation(aname, adict)
    print(dict_animals.keys())
    group_nice = GROUP_NICE
    group_meeh = list(set(dict_animals.keys()) - set(group_nice))
    animal_groups = [
        group_nice,
        group_meeh
    ]
    group_names = ["gud", "meh"]

    means, stdes, days_approx = stat_datapoints_by_period(dict_animals, N_DAYS, PERIOD_IN_DAYS)
    tmp_mask = (~np.isnan(means))
    means = means[tmp_mask]
    stdes = stdes[tmp_mask]
    days_approx = days_approx[tmp_mask]
    
    # all animals
    fig = plt.figure(figsize=(12,8))
    ax = fig.add_subplot(111)
    cmap = get_cmap(CMAP_STR, len(dict_animals))
    animal_colors = {}
    for i, animal_name in enumerate(dict_animals.keys()):
        animal_colors[animal_name] = cmap(i)
    plot_shaded_datapoints(dict_animals, duration_in_days=N_DAYS, animal_colors_=animal_colors, ax=ax)
    ax.plot(days_approx+(PERIOD_IN_DAYS-1)/2, means, color='k', marker='s', linewidth=1.5, alpha=1)
    ax.errorbar(days_approx+(PERIOD_IN_DAYS-1)/2, means, yerr=stdes, fmt='', color='k', capsize=5)
    # ax.plot(days_approx+PERIOD_IN_DAYS, means, color='k', marker='s', linewidth=1.5, alpha=1)
    # ax.errorbar(days_approx+PERIOD_IN_DAYS, means, yerr=stdes, fmt='', color='k', capsize=5)
    ax.set_xlim([-1, N_DAYS+PERIOD_IN_DAYS])
    ax.set_xticks(np.arange(0, N_DAYS+1, PERIOD_IN_DAYS))
    ax.set_xticklabels(np.arange(0, N_DAYS+1, PERIOD_IN_DAYS))
    if YLIM is not None:
        ax.set_ylim(YLIM)
    ax.set_xlabel("Day")
    ax.set_ylabel(YLABEL)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTFOLDER, "%s_%s_all.png"%(FEATURESET_OF_INTEREST, PLOT_NAME)))
    plt.savefig(os.path.join(PLOTFOLDER, "%s_%s_all.eps"%(FEATURESET_OF_INTEREST, PLOT_NAME)))
    plt.show()

    # for each group of animals
    for group_name, animal_group in zip(group_names, animal_groups):
        dict_animals_subset = dict((k,dict_animals[k]) for k in dict_animals.keys() if k in animal_group)
        means_s, stdes_s, days_approx_s = stat_datapoints_by_period(dict_animals_subset, N_DAYS, PERIOD_IN_DAYS)
        tmp_mask = (~np.isnan(means_s))
        means_s = means_s[tmp_mask]
        stdes_s = stdes_s[tmp_mask]
        days_approx_s = days_approx_s[tmp_mask]
        fig = plt.figure(figsize=(12,8))
        ax = fig.add_subplot(111)
        # box_plot_weekly(dict_animals_subset, duration_in_weeks=N_DAYS, ax=ax)
        # scatter_datapoints(dict_animals_subset, duration_in_days=N_DAYS*7, ax=ax)
        plot_shaded_datapoints(dict_animals_subset, duration_in_days=N_DAYS, animal_colors_=animal_colors, ax=ax)
        ax.plot(days_approx_s+(PERIOD_IN_DAYS-1)/2, means_s, color='k', marker='s', linewidth=1.5, alpha=1)
        ax.errorbar(days_approx_s+(PERIOD_IN_DAYS-1)/2, means_s, yerr=stdes_s, fmt='', color='k', capsize=5)
        # ax.plot(days_approx_s+PERIOD_IN_DAYS, means_s, color='k', marker='s', linewidth=1.5, alpha=1)
        # ax.errorbar(days_approx_s+PERIOD_IN_DAYS, means_s, yerr=stdes_s, fmt='', color='k', capsize=5)
        ax.set_xlim([-1, N_DAYS+PERIOD_IN_DAYS])
        # ax.set_xticks(np.arange(N_DAYS))
        # ax.set_xticklabels(np.arange(N_DAYS))
        ax.set_xticks(np.arange(0, N_DAYS+1, PERIOD_IN_DAYS))
        ax.set_xticklabels(np.arange(0, N_DAYS+1, PERIOD_IN_DAYS))
        ax.set_xlabel("Day")
        ax.set_ylabel(YLABEL)
        if YLIM is not None:
            ax.set_ylim(YLIM)
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTFOLDER, "%s_%s_%s.png"%(FEATURESET_OF_INTEREST, PLOT_NAME, group_name)))
        plt.savefig(os.path.join(PLOTFOLDER, "%s_%s_%s.eps"%(FEATURESET_OF_INTEREST, PLOT_NAME, group_name)))
        plt.show()
