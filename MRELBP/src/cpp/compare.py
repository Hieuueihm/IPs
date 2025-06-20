def compare2File(path1, path2):
    with open(path1, 'r') as file1, open(path2, 'r') as file2:
        lines1 = file1.readlines()
        lines2 = file2.readlines()

    if len(lines1) != len(lines2):
        print(f"Number of line is diff: {len(lines1)} vs {len(lines2)}")
        return False

    for i, (l1, l2) in enumerate(zip(lines1, lines2), 1):
        if l1.strip() != l2.strip():
            print(f"❌ diff in {i}:\n  File1: {l1.strip()}\n  File2: {l2.strip()}")
            return 


    print("same.")
    return True


# compare2File("median_3x3_py.txt", "median_3x3_cpp.txt")


# compare2File("median_5x5_py.txt", "median_5x5_cpp.txt")

# compare2File("median_7x7_py.txt", "median_7x7_cpp.txt")

# compare2File("ci_r2_py.txt", "ci_r2_cpp.txt")
# compare2File("ci_r4_py.txt", "ci_r4_cpp.txt")
# compare2File("ci_r6_py.txt", "ci_r6_cpp.txt")

# compare2File("ni_r2_py.txt", "ni_r2_cpp.txt")
# compare2File("ni_r4_py.txt", "ni_r4_cpp.txt")
# compare2File("ni_r6_py.txt", "ni_r6_cpp.txt")


# compare2File("rd_r2_py.txt", "rd_r2_cpp.txt")
# compare2File("rd_r4_py.txt", "rd_r4_cpp.txt")
# compare2File("rd_r6_py.txt", "rd_r6_cpp.txt")


# compare2File("histogram_py.txt", "histogram_cpp.txt")
compare2File("histogram_py.txt", "histogram_cpp_py.txt")
