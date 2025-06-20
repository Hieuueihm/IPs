import numpy as np
import os
import cv2

from MRELBP import MRELBP
import time

lbp = MRELBP()



np.random.seed(10)

img = cv2.imread("sample.bmp", cv2.IMREAD_GRAYSCALE);
random_matrix = np.random.randint(0, 256, size=(128, 128), dtype=np.uint8)
np.savetxt("random_matrix.txt", random_matrix, fmt='%d')
# print(random_matrix)
start = time.time()

res = lbp.MRELBP(random_matrix)
end = time.time()
print(f"Time taken: {end - start:.6f} seconds")

# res = lbp.MRELBP(random_matrix)
with open("histogram_py.txt", "w") as f:
    for i in range(0, 600):
        f.write(str(res[i]) + "\n")


