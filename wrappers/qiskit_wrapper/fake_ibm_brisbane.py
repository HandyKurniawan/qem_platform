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

class NewFakeBrisbaneRecent1(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 1)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 1)

class NewFakeBrisbaneRecent2(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 2)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 2)

class NewFakeBrisbaneRecent3(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 3)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 3)

class NewFakeBrisbaneRecent4(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 4)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 4)

class NewFakeBrisbaneRecent5(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 5)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 5)

class NewFakeBrisbaneRecent6(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 6)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 6)

class NewFakeBrisbaneRecent7(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 7)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 7)

class NewFakeBrisbaneRecent8(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 8)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 8)

class NewFakeBrisbaneRecent9(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 9)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 9)

class NewFakeBrisbaneRecent10(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 10)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 10)

class NewFakeBrisbaneRecent11(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 11)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 11)

class NewFakeBrisbaneRecent12(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 12)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 12)

class NewFakeBrisbaneRecent13(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 13)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 13)

class NewFakeBrisbaneRecent14(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 14)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 14)

class NewFakeBrisbaneRecent15(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 15)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 15)

class NewFakeBrisbaneRecent16(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 16)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 16)

class NewFakeBrisbaneRecent17(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 17)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 17)

class NewFakeBrisbaneRecent18(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 18)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 18)

class NewFakeBrisbaneRecent19(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 19)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 19)

class NewFakeBrisbaneRecent20(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 20)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 20)

class NewFakeBrisbaneRecent21(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 21)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 21)

class NewFakeBrisbaneRecent22(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 22)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 22)

class NewFakeBrisbaneRecent23(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 23)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 23)

class NewFakeBrisbaneRecent24(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 24)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 24)

class NewFakeBrisbaneRecent25(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 25)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 25)

class NewFakeBrisbaneRecent26(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 26)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 26)

class NewFakeBrisbaneRecent27(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 27)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 27)

class NewFakeBrisbaneRecent28(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 28)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 28)

class NewFakeBrisbaneRecent29(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 29)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 29)

class NewFakeBrisbaneRecent30(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 30)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 30)

class NewFakeBrisbaneRecent31(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 31)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 31)

class NewFakeBrisbaneRecent32(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 32)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 32)

class NewFakeBrisbaneRecent33(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 33)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 33)

class NewFakeBrisbaneRecent34(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 34)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 34)

class NewFakeBrisbaneRecent35(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 35)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 35)

class NewFakeBrisbaneRecent36(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 36)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 36)

class NewFakeBrisbaneRecent37(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 37)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 37)

class NewFakeBrisbaneRecent38(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 38)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 38)

class NewFakeBrisbaneRecent39(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 39)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 39)

class NewFakeBrisbaneRecent40(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 40)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 40)

class NewFakeBrisbaneRecent41(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 41)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 41)

class NewFakeBrisbaneRecent42(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 42)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 42)

class NewFakeBrisbaneRecent43(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 43)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 43)

class NewFakeBrisbaneRecent44(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 44)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 44)

class NewFakeBrisbaneRecent45(NewFakeBrisbane):
    props_filename = "props_{}_recent_{}.json".format(hw_name, 45)
    backend_name = "new_fake_{}_recent_{}".format(hw_name, 45)

class NewFakeBrisbaneRecentNAdjust(NewFakeBrisbane):
    def __init__(self, n):
        self.props_filename = "props_{}_recent_{}_adjust.json".format(hw_name, n)
        self.backend_name = "new_fake_{}_recent_{}_adjust".format(hw_name, n)
