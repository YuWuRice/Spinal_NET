import numpy as np
import h5py
import pynwb
from pynwb import NWBFile, NWBHDF5IO
from pynwb.ecephys import ElectricalSeries, TimeSeries
from hdmf.backends.hdf5.h5_utils import H5DataIO

HOTFIX_YW_32ON64 = True

def initiate_temp_hdf5(h5_tmpfilename: str, parsed_rhd: dict, mask=None):
    """
    read and parse one chunked rhd file; use the parsed data to create and 
    initailize a H5 file object (which is memmaped); the datasets in the 
    H5 would be already available for reading
    """
    fs_ampli = parsed_rhd["sample_rate"]
    # fs_digin = parsed_rhd["frequency_parameters"]["board_dig_in_sample_rate"]
    # if fs_digin is not None and fs_ampli != fs_digin:
    #     raise AssertionError(
    #         "Amplifier and dig-in have different sampling rates - not supported"
    #     )
    if mask is None:
        mask = np.ones(parsed_rhd["amplifier_data"].shape[0], dtype=bool)
    else:
        assert mask.dtype==bool and mask.shape[0]==parsed_rhd["amplifier_data"].shape[0]
    ch_native_orders = np.array([
        k["native_order"] for k in parsed_rhd["amplifier_channels"]
    ])[mask]
    ch_imped_mags = np.array([
        k["electrode_impedance_magnitude"] for k in parsed_rhd["amplifier_channels"]
    ])[mask]
    h5_file_obj = h5py.File(h5_tmpfilename, "w")
    # create constant datasets for channel information
    h5dset_ch_native_orders = h5_file_obj.create_dataset(
        name="ch_native_orders", data=ch_native_orders
    )
    h5dset_ch_imped_mags = h5_file_obj.create_dataset(
        name="ch_imped_mags", data=ch_imped_mags
    )
    # create constant scalar dataset for sampling rate
    h5dset_f_sample = h5_file_obj.create_dataset(
        name="f_sample",
        data=fs_ampli,
        shape=()
    )
    # create dataset for amplifier data
    tmp_data = parsed_rhd["amplifier_data"][mask, :] # (n_chs, n_samples)
    h5dset_amplifer_data = h5_file_obj.create_dataset(
        name="amplifier_data", data=tmp_data,
        maxshape=(tmp_data.shape[0], None)
    )
    # create dataset for timestamp
    tmp_data = parsed_rhd["t"]
    h5dset_t = h5_file_obj.create_dataset(
        name="t", data=tmp_data,
        maxshape=(None,)
    )
    # # create dataset for dc_amplifier_data
    # tmp_data = parsed_rhd["dc_amplifier_data"]
    # h5dset_dc_data = h5_file_obj.create_dataset(
    #     name="dc_amplifier_data", data=tmp_data,
    #     maxshape=(tmp_data.shape[0], None)
    # )
    # # create dataset for digital input
    # tmp_data = parsed_rhd["board_dig_in_data"]
    # h5dset_digin_data = h5_file_obj.create_dataset(
    #     name="board_dig_in_data", data=tmp_data,
    #     maxshape=(tmp_data.shape[0], None)
    # )
    return h5_file_obj

def _append_hdf5_dataset(
    h5_file_obj: h5py.File, dataset_name: str,
    new_data: np.ndarray, resize_axis: int
    ):
    # access dataset and prepare variables that describe shape
    dset = h5_file_obj[dataset_name]
    dset_shape = dset.shape # dset[:].shape # the [:] loads everything into ram
    dset_len = dset_shape[resize_axis]
    app_len = new_data.shape[resize_axis]
    dset_len += app_len
    my_slicer = [slice(None) for _ in range(len(dset_shape))]
    my_slicer[resize_axis] = slice(-app_len, None)
    # resize and write
    dset.resize(dset_len, axis=resize_axis)
    dset[tuple(my_slicer)] = new_data

def append_temp_hdf5(h5_file_obj, h5_tmpfilename: str, parsed_rhd: dict, mask=None):
    if mask is None:
        mask = np.ones(parsed_rhd["amplifier_data"].shape[0], dtype=bool)
    else:
        assert mask.dtype==bool and mask.shape[0]==parsed_rhd["amplifier_data"].shape[0]
    # TODO decide whether or not it should close and reopen HDF5 file object
    # TODO assert that constant parameters like sampling rate are consistent
    _append_hdf5_dataset(h5_file_obj, "amplifier_data", parsed_rhd["amplifier_data"][mask, :], 1)
    _append_hdf5_dataset(h5_file_obj, "t", parsed_rhd["t"], 0)
    # _append_hdf5_dataset(h5_file_obj, "dc_amplifier_data", parsed_rhd["dc_amplifier_data"], 1)
    # _append_hdf5_dataset(h5_file_obj, "board_dig_in_data", parsed_rhd["board_dig_in_data"], 1)


# def lookup_channel_map_mapstyle(ch_ids: list | np.ndarray, channel_maps: list):
#     """ Look up channel map for a list of channel IDs.
#     `ch_ids`: list of channel IDs.
#     `channel_maps`: list of arrays, each array is a channel map (map style).
#     TODO account for spacing
#     """
#     vertical_spacing = 25
#     horizontal_spacing = 30
#     if isinstance(ch_ids, list):
#         ch_ids = np.array(ch_ids)
#     shank_ids = np.full_like(ch_ids, -1)
#     locations = np.zeros((len(ch_ids), 2))
#     for i_, ch_id in enumerate(ch_ids):
#         for i_shank, chmap in enumerate(channel_maps):
#             if ch_id in chmap:
#                 shank_ids[i_] = i_shank
#                 tmp_coords = np.where(chmap==ch_id)
#                 locations[i_, 1] = tmp_coords[0][0]*vertical_spacing # Y coordinate
#                 locations[i_, 0] = tmp_coords[1][0]*horizontal_spacing # X coordinate
#                 break
#     return shank_ids, locations

def lookup_channel_map_corstyle(
        ch_ids: list | np.ndarray,
        channel_maps: np.ndarray):
    """ Look up channel map for a list of channel IDs.
    `ch_ids`: list of channel IDs.
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
        parsed_rhd: dict,
        channel_map: dict,
        metadata: dict,
        mask : np.ndarray = None,
        data_conv: dict = None
        ):
    """ Initiate NWB file object and write constant parameters.
    `export_nwb_path`: path of the NWB file to create and write data to.
    `rhd_readout_parsed`: parsed rhd readout data.
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
    if mask is None:
        mask = np.ones(parsed_rhd["amplifier_data"].shape[0], dtype=bool)
        # following is for the pre-2023 experiments with 32ch probes recorded with 64ch Intan boards
        if HOTFIX_YW_32ON64 and parsed_rhd["amplifier_data"].shape[0] > 32 and parsed_rhd["amplifier_data"].shape[0] <= 64:
            # this is a hack to make it work with the old data
            ch_native_orders_tmp = np.array([k["native_order"] for k in parsed_rhd["amplifier_channels"]])
            mask[(ch_native_orders_tmp<16)|(ch_native_orders_tmp>=48)] = False
    else:
        print(mask.shape, parsed_rhd["amplifier_data"].shape, len(parsed_rhd["amplifier_channels"]))
        if not(mask.dtype==bool and mask.shape[0]==parsed_rhd["amplifier_data"].shape[0]):
            raise ValueError("MASK shape and AMPLIFIER_DATA shape do not match in 0th dim: %s - %s" % (mask.shape, parsed_rhd["amplifier_data"].shape))
    if data_conv is None:
        data_conv = {"conversion": 1.0, "offset":0.0}
    if isinstance(channel_map, np.ndarray):
        channel_map = [channel_map]
    fs_ampli = parsed_rhd["sample_rate"]
    # fs_digin = parsed_rhd["frequency_parameters"]["board_dig_in_sample_rate"]
    # if fs_ampli != fs_digin:
    #     raise AssertionError(
    #         "Amplifier and dig-in have different sampling rates - not supported"
    #     )
    nwbhead_description = metadata.get("session_desc", "NWB file for RHD data")
    nwbhead_identifier = metadata.get("identifier", "TODO MANDATORY")
    nwbhead_start_time = metadata.get("start_time", "TODO MANDATORY")
    nwbhead_experimenter = metadata.get("experimenter", "Mpty Field")
    nwbhead_lab = metadata.get("lab", "XL Lab")
    nwbhead_institution = metadata.get("institution", "Rice U")
    nwbhead_expdesc = metadata.get("exp_desc", "None")
    nwbhead_session_id = metadata.get("session_id", "None")
    subject = metadata.get("subject", None)
    if subject is None:
        print("No subject metadata provided; DANDI will complain if you upload it")
    nwbfile = NWBFile(
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
    device = nwbfile.create_device(
        name="--", description="--", manufacturer="--"
    )

    # set up electrode groups and recording channels
    
    ch_native_orders = np.array([
        k["native_order"] for k in parsed_rhd["amplifier_channels"]
    ])[mask]
    if HOTFIX_YW_32ON64:
        chids4maplookup = ch_native_orders - 16
    else:
        chids4maplookup = ch_native_orders
    n_chs = ch_native_orders.shape[0]
    print("Number of channels: %d"%(n_chs))
    if channel_map["map_style"] == "coordinates":
        shankids, locations = lookup_channel_map_corstyle(chids4maplookup, channel_map["map_data"]) # only support single port from Intan
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
        data=H5DataIO(data=parsed_rhd["amplifier_data"][mask, :].T, maxshape=(None, parsed_rhd["amplifier_data"][mask, :].shape[0])),
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

def _append_nwb_dset(dset, data_to_append, resize_axis):
    dset_shape = dset.shape
    dset_len = dset_shape[resize_axis]
    app_len = data_to_append.shape[resize_axis]
    dset_len += app_len
    my_slicer = [slice(None) for _ in range(len(dset_shape))]
    my_slicer[resize_axis] = slice(-app_len, None)
    dset.resize(dset_len, axis=resize_axis)
    dset[tuple(my_slicer)] = data_to_append

def append_nwb(nwb_obj, export_nwb_path: str, parsed_rhd: dict, mask : np.ndarray = None):
    # nwb_obj is ignored
    if mask is None:
        mask = np.ones(parsed_rhd["amplifier_data"].shape[0], dtype=bool)
    else:
        assert mask.dtype==bool and mask.shape[0]==parsed_rhd["amplifier_data"].shape[0]
    io = NWBHDF5IO(export_nwb_path, "a")
    nwb_obj_ = io.read()
    _append_nwb_dset(nwb_obj_.acquisition["ElectricalSeries"].data, parsed_rhd["amplifier_data"][mask, :].T, 0)
    io.write(nwb_obj_)
