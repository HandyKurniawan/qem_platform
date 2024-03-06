for i in range(3, 46):
    # print ("NewFakeBrisbaneRecent{},".format(i), "NewFakeBrisbaneRecent{},".format(i + 1), "NewFakeBrisbaneRecent{},".format(i + 2), "NewFakeBrisbaneRecent{} \ ".format(i +3))

    # print("class NewFakeBrisbaneRecent{}(NewFakeBrisbane):".format(i))
    # print("""    props_filename = "props_{}_recent_{}.json".format(hw_name, {})""".format("{}", "{}", i))
    # print("""    backend_name = "new_fake_{}_recent_{}".format(hw_name, {})""".format("{}", "{}", i))
    # print("")

    print("elif recent_n == {} : tmp_backend = NewFakeBrisbaneRecent{}()".format(i, i))