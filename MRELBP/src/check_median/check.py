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
    verilog_3x3 = load_output("median_3x3.txt")
    verilog_5x5 = load_output("median_5x5.txt")
    verilog_7x7 = load_output("median_7x7.txt")

    median_3x3_py = load_output("median_3x3_py.txt")
    median_5x5_py = load_output("median_5x5_py.txt")
    median_7x7_py = load_output("median_7x7_py.txt")

    # Compare
    compare_outputs(median_3x3_py, verilog_3x3, "Median 3x3")
    compare_outputs(median_5x5_py, verilog_5x5, "Median 5x5")
    compare_outputs(median_7x7_py, verilog_7x7, "Median 7x7")

if __name__ == "__main__":
    main()
