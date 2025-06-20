import numpy as np

def generate_random_matrix(size, out_file="matrix_input.txt", seed=None):
    if seed is not None:
        np.random.seed(seed)  # reproducible

    matrix = np.random.randint(0, 256, (size, size), dtype=np.uint8)

    # Save matrix to decimal file
    with open(out_file, "w") as f_dec:
        for row in matrix:
            for value in row:
                f_dec.write(f"{value}\n")

    # Save matrix to hex file
    hex_file = out_file.replace(".txt", "_hex.txt")
    with open(hex_file, "w") as f_hex:
        for row in matrix:
            for value in row:
                f_hex.write(f"{value:02X}\n")  # 2-digit uppercase hex

    print(f"[✓] Random {size}x{size} matrix saved to:")
    print(f"    Decimal: {out_file}")
    print(f"    Hex    : {hex_file}")
    return matrix

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=9, help="Matrix size (NxN)")
    parser.add_argument("--out", type=str, default="matrix_input.txt", help="Output file (decimal)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    args = parser.parse_args()

    mat = generate_random_matrix(args.size, args.out, args.seed)
    print("\nGenerated Matrix:\n", mat)
