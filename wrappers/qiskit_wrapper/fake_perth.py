import os
from qiskit.providers.fake_provider import fake_backend

class NewFakePerth(fake_backend.FakeBackendV2):
    """A fake 7 qubit backend."""
    dirname = os.path.expanduser("~/qem_platform/wrappers/qiskit_wrapper/fake_backend/ibm_perth")

    conf_filename = "conf_perth.json"
    defs_filename = "defs_perth.json"

    props_filename = "props_perth.json"
    backend_name = "new_fake_perth"

class NewFakePerthRealAdjust(NewFakePerth):
    props_filename = "props_perth_real_adjust.json"
    backend_name = "new_fake_perth_real_adjust"

class NewFakePerthRecent15(NewFakePerth):
    props_filename = "props_perth_recent_15.json"
    backend_name = "new_fake_perth_recent_15"

class NewFakePerthRecent15Adjust(NewFakePerth):
    props_filename = "props_perth_recent_15_adjust.json"
    backend_name = "new_fake_perth_recent_15_adjust"

class NewFakePerthMix(NewFakePerth):
    props_filename = "props_perth_mix.json"
    backend_name = "new_fake_perth_mix"

class NewFakePerthMixAdjust(NewFakePerth):
    props_filename = "props_perth_mix_adjust.json"
    backend_name = "new_fake_perth_mix_adjust"

class NewFakePerthAverage(NewFakePerth):
    props_filename = "props_perth_avg.json"
    backend_name = "new_fake_perth_avg"

class NewFakePerthAverageAdjust(NewFakePerth):
    props_filename = "props_perth_avg_adjust.json"
    backend_name = "new_fake_perth_avg_adjust"

