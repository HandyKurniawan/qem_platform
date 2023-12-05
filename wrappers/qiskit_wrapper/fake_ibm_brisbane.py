import os
from qiskit.providers.fake_provider import fake_backend

hw_name = "ibm_brisbane"

class NewFakeBrisbane(fake_backend.FakeBackendV2):
    """A fake 7 qubit backend."""
    dirname = os.path.expanduser("~/qem_platform/wrappers/qiskit_wrapper/fake_backend/ibm_brisbane")

    conf_filename = "conf_brisbane.json"
    defs_filename = "defs_brisbane.json"

    props_filename = "props_{}.json".format(hw_name)
    backend_name = "new_fake_{}".format(hw_name)

class NewFakeBrisbaneRealAdjust(NewFakeBrisbane):
    props_filename = "props_{}_real_adjust.json".format(hw_name)
    backend_name = "new_fake_ibm_brisbane_real_adjust".format(hw_name)

class NewFakeBrisbaneRecent15(NewFakeBrisbane):
    props_filename = "props_{}_recent_15.json".format(hw_name)
    backend_name = "new_fake_{}_recent_15".format(hw_name)

class NewFakeBrisbaneRecent15Adjust(NewFakeBrisbane):
    props_filename = "props_{}_recent_15_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_recent_15_adjust".format(hw_name)

class NewFakeBrisbaneMix(NewFakeBrisbane):
    props_filename = "props_{}_mix.json".format(hw_name)
    backend_name = "new_fake_{}_mix".format(hw_name)

class NewFakeBrisbaneMixAdjust(NewFakeBrisbane):
    props_filename = "props_{}_mix_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_mix_adjust".format(hw_name)

class NewFakeBrisbaneAverage(NewFakeBrisbane):
    props_filename = "props_{}_avg.json".format(hw_name)
    backend_name = "new_fake_{}_avg".format(hw_name)

class NewFakeBrisbaneAverageAdjust(NewFakeBrisbane):
    props_filename = "props_{}_avg_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_avg_adjust".format(hw_name)