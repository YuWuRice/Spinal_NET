import numpy as np
import pynwb
from pynwb import NWBFile, NWBHDF5IO
from pynwb.ecephys import ElectricalSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO

def lookup_channel_map_corstyle(
        ch_ids: list | np.ndarray,
        channel_maps: np.ndarray):
    """ Look up channel map for a list of channel IDs.
    `ch_ids`: list of channel IDs. Must be in [0, N_total_channels-1]. Altho its length can be smaller than N_total_channels. 
    `channel_maps`: an arr of chan map (coordinates style).
        each row is (X, Y, [shank])
        TODO consider support for 3D positioning
    Hence no need to account for spacing
    """
    if isinstance(ch_ids, list):
        ch_ids = np.array(ch_ids)
    if len(ch_ids.shape) != 1:
        raise ValueError("ch_ids must be 1D; got {}".format(ch_ids.shape))
    # shank_ids = np.full_like(ch_ids, -1)
    # locations = np.zeros((len(ch_ids), 2))
    # for i_, ch_id in enumerate(ch_ids):
    #     locations[i_, 0] = channel_maps[ch_id][0] # X coordinate (horizontal)
    #     locations[i_, 1] = channel_maps[ch_id][1] # Y coordinate (vertical)
    #     shank_ids[i_] = channel_maps[ch_id][2] # shank ID
    locations = channel_maps[ch_ids, :2]
    if channel_maps.shape[1] == 3:
        shank_ids = channel_maps[ch_ids, 2].astype(int)
    else:
        shank_ids = np.zeros(len(ch_ids), dtype=int)
    return shank_ids, locations

def initiate_nwb(
        export_nwb_path: str,
        data_array: np.ndarray,
        recording_info: dict,
        channel_map: dict,
        metadata: dict,
        mask : np.ndarray = None,
        data_conv: dict = None
        ):
    """ Initiate NWB file object and write constant parameters.
    `export_nwb_path`: path of the NWB file to create and write data to.
    `data_array`: (n_times, n_channels) data to save in the NWB file.
    `recording_info`: dict. Keys: "sample_rate"
    `channel_map`: dict. Keys: "map_style", "map_data"; 
        "map_data" should be:
        - if `map_style`=="coordinates": a numpy array of (n_ch,2) or (n_ch,3)
        - if `map_style`=="map_by_shank": a list of channel maps by shank.
        Only "coordinates" is implemented now.
    `metadata`: dict. Keys:
        - "session_desc": str. Description of the session.
        - "identifier": str. Identifier of the session. E.g. animal-date
        - "start_time": datetime.datetime. Start time of the session.
        - "experimenter": str. Name of the experimenter.
        - "lab": str. Name of the lab.
        - "institution": str. Name of the institution.0
        - "exp_desc": str. Details of the experiment.
    `mask` : ndarry of bools. Indicates which electrodes to keep.
    `data_conv` : dict with keys "conversion" and "offset". The read-out data equals
        conversion*stored_data + offset ONLY WHEN you call `nwb.TimeSeries.get_data_in_units`
    """
    n_samples, n_channels_all = data_array.shape
    if mask is None:
        mask = np.ones(n_channels_all, dtype=bool)
    else:
        print(mask.shape, n_channels_all)
        if not(mask.dtype==bool and mask.shape[0]==n_channels_all):
            raise ValueError("MASK shape and DATA shape do not match in 0th dim: %s - %s" % (mask.shape, n_channels_all))
    n_channels_accepted = int(np.sum(mask))
    if data_conv is None:
        data_conv = {"conversion": 1.0, "offset":0.0}
    if isinstance(channel_map, np.ndarray):
        channel_map = [channel_map]
    fs_ampli = recording_info["sample_rate"]
    # fs_digin = parsed_rhd["frequency_parameters"]["board_dig_in_sample_rate"]
    # if fs_ampli != fs_digin:
    #     raise AssertionError(
    #         "Amplifier and dig-in have different sampling rates - not supported"
    #     )
    nwbhead_description = metadata.get("session_desc", "NWB file for spinal cord data")
    nwbhead_identifier = metadata.get("identifier", "TODO MANDATORY")
    nwbhead_start_time = metadata.get("start_time", "TODO MANDATORY")
    nwbhead_experimenter = metadata.get("experimenter", "BT")
    nwbhead_lab = metadata.get("lab", "Luan/Xie/Pfaff Labs")
    nwbhead_institution = metadata.get("institution", "Rice U & Salk Institute")
    nwbhead_expdesc = metadata.get("exp_desc", "None")
    nwbhead_session_id = metadata.get("session_id", "None")
    nwbhead_subject = metadata.get("subject", None)
    nwbfile = NWBFile(
        session_description=nwbhead_description,
        identifier=nwbhead_identifier,
        session_start_time=nwbhead_start_time,
        experimenter=nwbhead_experimenter,
        lab=nwbhead_lab,
        institution=nwbhead_institution,
        experiment_description=nwbhead_expdesc,
        session_id=nwbhead_session_id,
        subject=nwbhead_subject
    )
    device = nwbfile.create_device(
        name="--", description="--", manufacturer="--"
    )

    # set up electrode groups and recording channels
    ch_native_orders = np.arange(mask.shape[0])[mask]
    n_chs = ch_native_orders.shape[0]
    if channel_map["map_style"] == "coordinates":
        shankids, locations = lookup_channel_map_corstyle(ch_native_orders, channel_map["map_data"]) # only support single port from Intan
        # shankids, locations = lookup_channel_map_corstyle(np.arange(n_chs), channel_map["map_data"])
    elif channel_map["map_style"] == "map_by_shank":
        raise NotImplementedError
    else:
        raise ValueError("Unknown channel map style: {}".format(channel_map["map_style"]))
    electrode_groups = []
    nwbfile.add_electrode_column(name="label", description="Descriptive label")
    for shankid in np.sort(np.unique(shankids)):
        electrode_group = nwbfile.create_electrode_group(
            name="shank{}".format(shankid),
            description="electrode group for shank {}".format(shankid),
            device=device,
            location="Spinal cord"
        )
        electrode_groups.append(electrode_group)

    for ch_id in range(n_chs):
        nwbfile.add_electrode(
            group=electrode_groups[shankids[ch_id]],
            id=ch_native_orders[ch_id],
            label="native{}_ovr{}_shank{}".format(ch_native_orders[ch_id], ch_id, shankids[ch_id]),
            location="Spinal cord",
            rel_x=float(locations[ch_id][0]),
            rel_y=float(locations[ch_id][1]),
            rel_z=0.0,
            x=float(locations[ch_id][0]),
            y=float(locations[ch_id][1]),
            z=0.0
        )
    all_table_region = nwbfile.create_electrode_table_region(
        region=list(range(n_chs)),  # reference row indices 0 to N-1
        description="all electrodes"
    )

    # add amplifier data
    raw_electrical_series = ElectricalSeries(
        name="ElectricalSeries",
        data=H5DataIO(data=data_array[:, mask], maxshape=(None, n_channels_accepted)),
        electrodes=all_table_region,
        starting_time=0.0,  # timestamp of the first sample in seconds relative to the session start time
        rate=fs_ampli, # in Hz
        conversion=data_conv["conversion"],
        offset=data_conv["offset"]
    )
    nwbfile.add_acquisition(raw_electrical_series)

    with NWBHDF5IO(export_nwb_path, "w") as io:
        io.write(nwbfile)
    # return nwbfile
