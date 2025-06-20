from scipy.ndimage import median_filter
import cv2
import numpy as np
class MRELBP():
    def __init__(self, r=[2, 4, 6, 8], p = 8, w_c = 3, w_r = [3, 5, 7, 9]):
        self.r = r
        self.p = p
        self.w_c = w_c
        self.w_r = w_r
        self.count = 0
        # step :
        #   RGB2Gray
        #   Median
        #   CI
        #   Bi-interpolation -> RI & ND
        #   Histogram

    def median_processing(self, image):
        m_3x3 = median_filter(image, size = self.w_r[0], mode='constant', cval=0)
        m_5x5 = median_filter(image, size = self.w_r[1], mode='constant', cval=0)
        m_7x7 = median_filter(image, size = self.w_r[2], mode='constant', cval=0)
        return m_3x3, m_5x5, m_7x7



    def mrelbp_ci(self, image, in_r):
        window_size = 2 * in_r + 1

        height, width = image.shape
        out = np.zeros((height - 2 * in_r, width - 2 * in_r), dtype=np.uint8)

        sum_o = np.zeros((height - 2 * in_r, width - 2 * in_r))

        pixel_central =  np.zeros((height - 2 * in_r, width - 2 * in_r))
  


        for i in range(0,height - 2 * in_r ):
            for j in range(0,width - 2 * in_r ):
                area = image[i : i +window_size, j :j +  window_size]
                
                sum_o[i, j] = np.sum(area)
                pixel_central[i, j] = image[i + in_r, j + in_r]
                scale_value = pixel_central[i, j] * ((2*in_r + 1)**2)
                out[i,j] =  (scale_value >= sum_o[i, j])


        return out

   
    def getInterpolation(self, image, x, y):
        x1 = int(np.floor(x))
        x2 = int(np.ceil(x))
        y1 = int(np.floor(y))
        y2 = int(np.ceil(y))

        a = x - x1
        b = y - y1

        r1 = (1 - a) * (1-b)
        r2 =  a * (1 - b)
        r3 = (1 - a) * b
        r4 = a * b

        interpolated_value = (
            image[x1, y1] * r1 +
            image[x1, y2] * r2 +
            image[x2, y1] * r3 +
            image[x2, y2] * r4
        )
        fraction_bits = 16

        fixed_r1 = int(r1 * (1 << fraction_bits))
        fixed_r2 = int(r2 * (1 << fraction_bits))
        fixed_r3 = int(r3 * (1 << fraction_bits))
        fixed_r4 = int(r4 * (1 << fraction_bits))




        return interpolated_value
    def convertToFixedPoint(self, value, frac_bits=16):
        integer_value = int(value)  # Convert hex to integer
        fractional_value = integer_value / (1 << frac_bits)
        return fractional_value
    def getinterpolation_r_phi(self, image, x, y, r, phi):
        lookup_table = {
            (45, 2): (0x0003E1D, 0x00057D8, 0x0002BEC, 0x0003E1D),
            (135, 2): (0x0002BEC, 0x0003E1D, 0x0003E1D, 0x00057D8),
            (225, 2): (0x0003E1D, 0x0002BEC, 0x00057D8, 0x0003E1D),
            (315, 2): (0x00057D8, 0x0003E1D, 0x0003E1D, 0x0002BEC),
            (45, 3): (0x0001B4A, 0x000C5A6, 0x00003C4, 0x0001B4A),
            (135, 3): (0x00003C4, 0x0001B4A, 0x0001B4A, 0x000C5A6),
            (225, 3): (0x0001B4A, 0x00003C4, 0x000C5A6, 0x0001B4A),
            (315, 3): (0x000C5A6, 0x0001B4A, 0x0001B4A, 0x00003C4),
            (45, 4): (0x002463, 0x000789, 0x00AFB0, 0x002463),
            (135, 4): (0x00AFB0, 0x002463, 0x002463, 0x000789),
            (225, 4): (0x002463, 0x00AFB0, 0x000789, 0x002463),
            (315, 4): (0x000789, 0x002463, 0x002463, 0x00AFB0),
            (45, 5): (0x0003FAD, 0x0003739, 0x000496B, 0x0003FAD),
            (135, 5): (0x000496B, 0x0003FAD, 0x0003FAD, 0x0003739),
            (225, 5): (0x0003FAD, 0x000496B, 0x0003739, 0x0003FAD),
            (315, 5): (0x0003739, 0x0003FAD, 0x0003FAD, 0x000496B),
            (45, 6): (0x0002F0B, 0x00092D6, 0x0000F12, 0x0002F0B),
            (135, 6): (0x0000F12, 0x0002F0B, 0x0002F0B, 0x00092D6),
            (225, 6): (0x0002F0B, 0x0000F12, 0x00092D6, 0x0002F0B),
            (315, 6): (0x00092D6, 0x0002F0B, 0x0002F0B, 0x0000F12),
            (45, 7): (0x0000C37, 0x00000A5, 0x000E6EA, 0x0000C37),
            (135, 7): (0x000E6EA, 0x0000C37, 0x0000C37, 0x00000A5),
            (225, 7): (0x0000C37, 0x000E6EA, 0x00000A5, 0x0000C37),
            (315, 7): (0x00000A5, 0x0000C37, 0x0000C37, 0x000E6EA),
            (45, 8): (0x00039B3, 0x0001E24, 0x0006E73, 0x00039B3),
            (135, 8): (0x0006E73, 0x00039B3, 0x00039B3, 0x0001E24),
            (225, 8): (0x00039B3, 0x0006E73, 0x0001E24, 0x00039B3),
            (315, 8): (0x0001E24, 0x00039B3, 0x00039B3, 0x0006E73),
        }
        r1 = lookup_table[(phi, r)][0]
        r2 = lookup_table[(phi, r)][1]
        r3 = lookup_table[(phi, r)][2]
        r4 = lookup_table[(phi, r)][3]
        x1 = int(np.floor(x))
        x2 = int(np.ceil(x))
        y1 = int(np.floor(y))
        y2 = int(np.ceil(y)) 
        r1_ = self.convertToFixedPoint(r1)
        r2_ = self.convertToFixedPoint(r2)
        r3_ = self.convertToFixedPoint(r3)
        r4_ = self.convertToFixedPoint(r4)
        # print(r1_, r2_, r3_, r4_)
        # print(r1)

        interpolated_value = (
            image[x1, y1] * r1_ +
            image[x1, y2] * r2_ +
            image[x2, y1] * r3_ +
            image[x2, y2] * r4_
        )
        

      
        return interpolated_value
        
    def jointHistogram(self, ci, ni, rd):
        # with open("joint_code_python.txt", 'w') as f:
        width, height = ci.shape
        out_matrix = np.zeros(200, dtype=np.uint32)
        for i in  range(0, width):
            for j in range(0, height):
                out_matrix[ci[i, j] * 100 + ni[i, j] * 10 + rd[i, j]] += 1
        return out_matrix


    def getNIDescriptor(self, NI, r, sum):
        ni_des = 0
        self.count = self.count + 1

        for index in range(1, 9):
            scale_value = NI[index] * ((2 * r + 1) ** 2)

            if scale_value >= sum:
                ni_des  = ni_des + 2**(index - 1)
        return ni_des

    def getRDDescriptor(self, r2, r1):
        sum = 0
        for i in range(1, 9):
            if r2[i] >= r1[i]:
                sum = sum + 2**(i - 1)

        return sum
    def ror(self, pixel):
        min_value = 255
        binary_pixel = bin(pixel)[2:].zfill(8)
        binary_pixel_int = int(binary_pixel, 2)

        for i in range(8):
            result = ((binary_pixel_int >> i) | ((binary_pixel_int << (8 - i))) & 0xFF)
            if min_value > result:
                min_value = result
        return  min_value

    def checkU2(self, pixel):

        binary_pixel = bin(pixel)[2:].zfill(8)

        transitions = 0

        for i in range(8):
            current_bit = binary_pixel[i]
            next_bit = binary_pixel[(i + 1) % 8]  #

            # Check transitions
            if current_bit == '1' and next_bit == '0':
                transitions += 1
            elif current_bit == '0' and next_bit == '1':
                transitions += 1

        # Print the results
        return transitions
    def getSumPixel(self, pixel):
        sum = 0
        binary_pixel = bin(pixel)[2:].zfill(8)
        for i in range(0, 8):
            sum += int(binary_pixel[i])
        return sum


    def NI_RD_descriptor(self, image_r1, image_r2, r2):
        NI, RD = self.getNI_RD(image_r1, image_r2, r2)
        # print(NI)
        # print(RD)
        NI_out  = np.zeros(NI.shape, dtype= np.uint8)
        RD_out  = np.zeros(NI.shape, dtype= np.uint8)
        
        NI_height, NI_width = NI.shape
        for i in range(0, NI_height):
            for j in range(0, NI_width):
                NI_transitions = self.checkU2(np.uint8(NI[i, j]))
                NI_des = 0
                if NI_transitions <= 2:
                    NI_des = self.getSumPixel(np.uint8(NI[i, j]))
                else:
                    NI_des = 9
                NI_out[i, j] = NI_des

                RD_transitions = self.checkU2(np.uint8(RD[i, j]))
                RD_des = 0
                if RD_transitions <= 2:
                    RD_des = self.getSumPixel(np.uint8(RD[i, j]))
                else:
                    RD_des = 9
                RD_out[i, j] = RD_des
   
        NI_histogram = np.histogram(NI_out,  10)[0].astype(dtype=np.int32)
        RD_histogram = np.histogram(RD_out, 10)[0].astype(dtype=np.int32)
        

        return NI_out, RD_out
    def MRELBP(self, image):
        m_3x3, m_5x5, m_7x7 = self.median_processing(image)
        # np.savetxt("median_3x3_py.txt", m_3x3, fmt="%d")
        # np.savetxt("median_5x5_py.txt", m_5x5, fmt="%d")
        # np.savetxt("median_7x7_py.txt", m_7x7, fmt="%d")


        ci_r2 = self.mrelbp_ci(m_3x3, 2)
        ci_r4 = self.mrelbp_ci(m_3x3, 4)
        ci_r6 = self.mrelbp_ci(m_3x3, 6)
        # np.savetxt("ci_r2_py.txt", ci_r2, fmt="%d")
        # np.savetxt("ci_r4_py.txt", ci_r4, fmt="%d")
        # np.savetxt("ci_r6_py.txt", ci_r6, fmt="%d")

        NI_r2, RD_r2= self.NI_RD_descriptor(image, m_3x3, 2)
        NI_r4, RD_r4= self.NI_RD_descriptor(m_3x3, m_5x5, 4)
        NI_r6, RD_r6= self.NI_RD_descriptor(m_5x5, m_7x7, 6)

        # np.savetxt("ni_r2_py.txt", NI_r2, fmt="%d")
        # np.savetxt("ni_r4_py.txt", NI_r4, fmt="%d")
        # np.savetxt("ni_r6_py.txt", NI_r6, fmt="%d")



        # np.savetxt("rd_r2_py.txt", RD_r2, fmt="%d")
        # np.savetxt("rd_r4_py.txt", RD_r4, fmt="%d")
        # np.savetxt("rd_r6_py.txt", RD_r6, fmt="%d")

        hist_r2 = self.jointHistogram(ci_r2, NI_r2, RD_r2)
        hist_r4 = self.jointHistogram(ci_r4, NI_r4, RD_r4)
        hist_r6 = self.jointHistogram(ci_r6, NI_r6, RD_r6)

        hist_o = np.concatenate((hist_r2, hist_r4, hist_r6))

        return hist_o





    def getInterNeighbors(self, image, r, i, j):

        if r == 1:
            S =  np.zeros(9, dtype = np.uint8)
            S[1] = image[i, j + r]
            S[2] = image[i -r , j + r]
            S[3] = image[i -r, j]
            S[4] = image[i -r, j - r]
            S[5] = image[i, j -r ]
            S[6] = image[i + r, j - r]
            S[7] = image[i + r , j]
            S[8] = image[i + r, j + r]
            return S
        angles = [45, 135, 225, 315]
        results = {}
        S =  np.zeros(9)
        S[1] = image[i, j + r]
        S[3] = image[i - r, j]
        S[5] = image[i, j - r]
        S[7] = image[i + r, j]

        for angle in angles:
            theta = np.radians(angle)
            target_x = i - r * np.sin(theta)
            target_y = j + r * np.cos(theta)
            
            results[f"{angle}"] = self.getinterpolation_r_phi(image, target_x, target_y, r, angle )


        S[2] = results["45"]
        S[4] = results["135"]
        S[6] = results["225"]
        S[8] = results["315"]

        return S

    def getNI_RD(self, image_r1, image_r2, r2, save_path_r1='r1_desc.txt', save_path_r2='r2_desc.txt'):
        height, width = image_r2.shape
        NI = np.zeros((height - 2 * r2, width - 2 * r2), dtype = np.uint8)
        RD = np.zeros((height - 2 * r2, width - 2 * r2), dtype = np.uint8)
        r1 = r2 - 1
        # with open(save_path_r1, 'w') as f_r1, open(save_path_r2, 'w') as f_r2:
        for i in range(r2,height - r2):
            for j in range(r2,width -r2):
                area = image_r2[i - r2  : i  + r2 + 1 , j  - r2 :j + r2 + 1]
                sum_r2_patch = np.sum(area)
                    
                r1_descriptor = self.getInterNeighbors(image_r1, r1, i, j)
                r2_descriptor = self.getInterNeighbors(image_r2, r2, i, j)
                    # f_r1.write(" ".join([f"{int(x) & 0xFFFF:04X}" for x in r1_descriptor]) + "\n")
                    # f_r2.write(" ".join([f"{int(x) & 0xFFFF:04X}" for x in r2_descriptor]) + "\n")        
                NI[i - r2, j - r2] = self.getNIDescriptor(r2_descriptor, r2, sum_r2_patch)
                RD[i - r2, j - r2] = self.getRDDescriptor(r2_descriptor, r1_descriptor)

        return NI, RD

