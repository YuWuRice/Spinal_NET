import datetime

# SI_SUBDIR = "ms4_whiten_conventional"
SI_SUBDIR = "ms4_whiten_bothpeaks_thr4d5_upto1100"
list_animals_metadata = []
si_subdir = SI_SUBDIR

def datestr2datetime(datestr):
    return datetime.datetime.strptime(datestr, "%Y%m%d")
# JAN018
animal_id = "JAN018"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250216"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250219"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250306"%(animal_id), "spksort_allday/%s"%(si_subdir)),
]
surg_datestr = "20250210"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL20
animal_id = "EBL20"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250320/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250324/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250328/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
]
surg_datestr = "20250317"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL16
animal_id = "EBL16"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250113/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250115/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
    # "/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250125/spksort_allday/%s"%(animal_id, si_subdir),
]
surg_datestr = "20250110"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

animal_id = "EBL11"
# session_names = [
#     "/storage/SSD_slot0_2T/spinalEBL/proc/EBL11/20240831/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20240911/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20240929/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241007/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241012/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241107/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241118/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241125/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241202/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241205/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
#     # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241209/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
# ]
session_names = [
    ("/storage/SSD_slot0_2T/spinalEBL/proc/EBL11/20240831/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20240911/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20240929/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241007/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241107/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241118/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241125/", "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241202/", "spksort_allday/ms4_whiten_conventional"),
    # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241012/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
    # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241205/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
    # "/storage/wd_pcie1_4T/spinalEBL/proc/EBL11/20241209/spksort_allday/ms4_whiten_bothpeaks_thr4d5",
]
surg_datestr = "20240818"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL22
animal_id = "EBL22"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20250405/"%(animal_id), "spksort_allday/%s"%(si_subdir)),
]
surg_datestr = "20250401"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL07
animal_id = "EBL07"
session_names = [
    ("/storage/SSD_slot0_2T/spinalEBL/proc/%s/20240610/"%(animal_id), "spksort_allday/ms4_whiten_ebl128-18"),
]
surg_date = datestr2datetime("20240604")
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL09
animal_id = "EBL09"
session_names = [
    ("/storage/SSD_slot0_2T/spinalEBL/proc/%s/20240731/"%(animal_id), "spksort_allday/ms4_whiten_conventional"),
]
surg_datestr = "20240722"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL10
animal_id = "EBL10"
session_names = [
    ("/storage/SSD_slot0_2T/spinalEBL/proc/%s/20240820/"%(animal_id), "spksort_allday/ms4_whiten_conventional"),
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20240826/"%(animal_id),  "spksort_allday/ms4_whiten_conventional"),
]
surg_datestr = "20240712"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL12
animal_id = "EBL12"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20240930/"%(animal_id), "spksort_allday/ms4_whiten_conventional"),
]
surg_datestr = "20240826"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL14
animal_id = "EBL14"
session_names = [
    ("/storage/wd_pcie1_4T/spinalEBL/proc/%s/20241118/"%(animal_id), "spksort_allday/ms4_whiten_conventional"),
]
surg_datestr = "20241105"
surg_date = datestr2datetime(surg_datestr)
list_animals_metadata.append(dict(
    animal_id=animal_id,
    session_names=session_names,
    surg_date=surg_date,
    surg_datestr=surg_datestr
))

# EBL15
# animal_id = "EBL15"
# session_names = [
#     "/storage/wd_pcie1_4T/spinalEBL/proc/%s/20241210/spksort_allday/ms4_whiten_conventional"%(animal_id),
# ]
# surg_date = datestr2datetime("20241207")
# list_animals_metadata.append(dict(
#     animal_id=animal_id,
#     session_names=session_names,
#     surg_date=surg_date
# ))