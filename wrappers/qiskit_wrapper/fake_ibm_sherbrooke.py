import os
from qiskit.providers.fake_provider import fake_backend

hw_name = "ibm_sherbrooke"

class NewFakeSherbrooke(fake_backend.FakeBackendV2):
    """A fake 127 qubit backend."""
    dirname = os.path.expanduser("~/qem_platform/wrappers/qiskit_wrapper/fake_backend/ibm_sherbrooke")

    conf_filename = "conf_sherbrooke.json"
    defs_filename = "defs_sherbrooke.json"

    props_filename = "props_{}.json".format(hw_name)
    backend_name = "new_fake_{}".format(hw_name)

class NewFakeSherbrookeRealAdjust(NewFakeSherbrooke):
    props_filename = "props_{}_real_adjust.json".format(hw_name)
    backend_name = "new_fake_ibm_sherbrooke_real_adjust".format(hw_name)

class NewFakeSherbrookeRecent15Adjust(NewFakeSherbrooke):
    props_filename = "props_{}_recent_15_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_recent_15_adjust".format(hw_name)

class NewFakeSherbrookeMix(NewFakeSherbrooke):
    props_filename = "props_{}_mix.json".format(hw_name)
    backend_name = "new_fake_{}_mix".format(hw_name)

class NewFakeSherbrookeMixAdjust(NewFakeSherbrooke):
    props_filename = "props_{}_mix_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_mix_adjust".format(hw_name)

class NewFakeSherbrookeAverage(NewFakeSherbrooke):
    props_filename = "props_{}_avg.json".format(hw_name)
    backend_name = "new_fake_{}_avg".format(hw_name)

class NewFakeSherbrookeAverageAdjust(NewFakeSherbrooke):
    props_filename = "props_{}_avg_adjust.json".format(hw_name)
    backend_name = "new_fake_{}_avg_adjust".format(hw_name)

class NewFakeSherbrookeRecentNAdjust(NewFakeSherbrooke):
    def __init__(self, n):
        self.props_filename = "props_{}_recent_{}_adjust.json".format(hw_name, n)
        self.backend_name = "new_fake_{}_recent_{}_adjust".format(hw_name, n)

class NewFakeSherbrookeRecent15(NewFakeSherbrooke):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 15)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 15)
