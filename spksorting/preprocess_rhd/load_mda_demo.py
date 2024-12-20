import numpy as np
import matplotlib.pyplot as plt
import scipy.signal

from utils.mdaio import DiskReadMda, readmda


mdafile_path = "CombinedSessions.mda"
firings_path = "firings_curated.mda"
templte_path = "templates.mda"

mda = DiskReadMda(mdafile_path)

fs = 30000 # sampling rate of recording device

data_dims = mda.dims()
assert len(data_dims) == 2
n_chs = data_dims[0]
n_samples = data_dims[1]
dt = mda.dt() # data type as stored in disk, e.g. "int16"
print("# channels in data = %d" % (n_chs))
print("# samples in data = %d" % (n_samples))
print("Duration of data in seconds (fs=30kHz): %.2f" % (n_samples/fs))


# example: read signal from all channels from 600 to 605 seconds
beg_second = 600
end_second = 605
beg_sample = int(beg_second*fs)
dur_sample = int((end_second - beg_second) * fs)
sample_data = mda.readChunk(i1=0, i2=beg_sample, N1=n_chs, N2=dur_sample)
print("Shape of read chunk:", sample_data.shape)
# filter to multi-unit-activity band
sos = scipy.signal.butter(5, [500, 3000], btype="bandpass", output='sos', fs=fs)
sample_data_mua = scipy.signal.sosfiltfilt(sos, sample_data, axis=-1)
plt.figure()
t_axis = np.arange(sample_data.shape[1])/fs
plt.plot(t_axis, sample_data[0, :], color="k", linewidth=1)
plt.xlabel("Time (sec)")
plt.ylabel("Voltage $(\\mu V)$")
plt.title("Raw data on one channel")

plt.figure()
plt.plot(t_axis, sample_data_mua.T + np.arange(n_chs)*10*np.std(sample_data_mua), linewidth=1)
plt.xlabel("Time (sec)")
plt.yticks([])
plt.title("MUA-band data on all channels\n(channels plotted in arbitrary order)")

plt.show()

# load the spike stamps
print("Loading spike timestamps from %s", firings_path)
firings = readmda(firings_path)
print(firings.shape) # (3, n_spikes_in_session)
print("Primary channels of first 30 spikes detected in session:")
print(firings[0, :30]) # (primary channel of the unit)
print("Timestamps (in n_samples) of first 30 spikes detected in session:")
print(firings[1, :30])
print("Labels of first 30 spikes detected in session:")
print(firings[2, :30])

# load templates
templates = readmda(templte_path)
n_chs4template, len_waveform, n_units = templates.shape # (n_channels, length_of_template, n_units)
assert n_chs4template == n_chs
print("# accepted units in session:", len(np.unique(firings[2,:])))
print("The labels of those units are:")
print(np.sort(np.unique(firings[2,:])))
print("# total units in session:", n_units)
print("Duration of a template waveform in samples:", len_waveform)

