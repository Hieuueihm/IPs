import numpy as np
from scipy.ndimage import median_filter

def load_matrix(filename, img_size, hex_mode=False):
    with open(filename, 'r') as f:
        raw = f.readlines()
        if hex_mode:
            data = [int(x.strip(), 16) for x in raw]
        else:
            data = [int(x.strip()) for x in raw]
    matrix = np.array(data).reshape((img_size, img_size))
    return matrix

def save_output(matrix, filename):
    with open(filename, 'w') as f:
        for value in matrix.flatten():
            f.write(f"{value}\n")

def load_output(filename):
    with open(filename, 'r') as f:
        return [int(line.strip()) for line in f.readlines()]

def compare_outputs(py_output, verilog_output, filter_name):
    if len(py_output) != len(verilog_output):
        print(f"[❌] {filter_name} length mismatch: Python({len(py_output)}) vs Verilog({len(verilog_output)})")
        return

    mismatch = [(i, g, v) for i, (g, v) in enumerate(zip(py_output, verilog_output)) if g != v]
    if mismatch:
        print(f"[❌] {filter_name} mismatch at {len(mismatch)} positions:")
        for i, g, v in mismatch[:10]:
            print(f"  At index {i}: expected {g}, got {v}")
    else:
        print(f"[✅] {filter_name} output matches Verilog.")

def main():


    # Load Verilog and Python outputs
    ni_r2 = load_output("ni_r2.txt")
    rd_r2 = load_output("rd_r2.txt")

    ni_r2_py = load_output("ni_r2_py.txt")
    rd_r2_py = load_output("rd_r2_py.txt")

    ni_r4 = load_output("ni_r4.txt")
    rd_r4 = load_output("rd_r4.txt")

    ni_r4_py = load_output("ni_r4_py.txt")
    rd_r4_py = load_output("rd_r4_py.txt")

    ni_r6 = load_output("ni_r6.txt")
    rd_r6 = load_output("rd_r6.txt")

    ni_r6_py = load_output("ni_r6_py.txt")
    rd_r6_py = load_output("rd_r6_py.txt")
    # Compare
    compare_outputs(ni_r2_py, ni_r2, "ni r2")
    compare_outputs(ni_r2_py, ni_r2, "rd r2")

    compare_outputs(ni_r4_py, ni_r4, "ni r4")
    compare_outputs(ni_r4_py, ni_r4, "rd r4")

    compare_outputs(ni_r4_py, ni_r4, "ni r6")
    compare_outputs(ni_r4_py, ni_r4, "rd r6")
if __name__ == "__main__":
    main()
