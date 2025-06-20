#include <iostream>
#include <vector>
#include <cassert>
#include <opencv2/opencv.hpp>
#include <fstream>
#include <sstream>
#include <cmath>
#include <unordered_map>
#include <chrono>
#include <pybind11/stl.h>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>


void printMat(cv::Mat mat)
{
    for (int row = 0; row < mat.rows; ++row)
    {
        for (int col = 0; col < mat.cols; ++col)
        {
            uchar pixel = mat.at<uchar>(row, col);

            std::cout << static_cast<int>(pixel) << " ";
        }
        std::cout << std::endl;

    }
}

static void write2File(const std::string& filename, const cv::Mat& input) {
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Open file failed: " << filename << std::endl;
        return;
    }


    for (int i = 0; i < input.rows; ++i) {
        for (int j = 0; j < input.cols; ++j) {
            if (input.channels() == 1) {
                file << static_cast<int>(input.at<uchar>(i, j));
            } else if (input.channels() == 3) {
                cv::Vec3b pixel = input.at<cv::Vec3b>(i, j);
                file << static_cast<int>(pixel[0]) << ","  // B
                     << static_cast<int>(pixel[1]) << ","  // G
                     << static_cast<int>(pixel[2]);        // R
            }
            file << (j < input.cols - 1 ? " " : "");
        }
        file << "\n";
    }

    file.close();
    std::cout << "W2F success: " << filename << std::endl;
}
namespace LBP
{
    class MRELBP
    {
    private:
        int r[3] = {2, 4, 6};
    public:
     double convertToFixedPoint(uint32_t value, int frac_bits = 16) {
        return static_cast<double>(value) / (1 << frac_bits);
    }
    double bilinearInterpolation(const cv::Mat& image, float x, float y) {
        int width = image.cols;
        int height = image.rows;

        int x1 = static_cast<int>(std::floor(x));
        int y1 = static_cast<int>(std::floor(y));
        int x2 = x1 + 1;
        int y2 = y1 + 1;

        // Clamp to bounds
        if (x1 < 0 || y1 < 0 || x2 >= width || y2 >= height)
            return 0.0;

        double dx = x - x1;
        double dy = y - y1;

        double I11 = image.at<uchar>(y1, x1);
        double I21 = image.at<uchar>(y1, x2);
        double I12 = image.at<uchar>(y2, x1);
        double I22 = image.at<uchar>(y2, x2);

        double I = I11 * (1 - dx) * (1 - dy) +
                   I21 * dx * (1 - dy) +
                   I12 * (1 - dx) * dy +
                   I22 * dx * dy;

        return I;
}
     double getInterpolationRphi(const cv::Mat& image, float x, float y, int r, int phi) {
        using Key = std::pair<int, int>;
        using Coeffs = std::tuple<uint32_t, uint32_t, uint32_t, uint32_t>;

        static std::map<Key, Coeffs> lookup_table = {
            {{45, 2}, {0x0003E1D, 0x00057D8, 0x0002BEC, 0x0003E1D}},
            {{135, 2}, {0x0002BEC, 0x0003E1D, 0x0003E1D, 0x00057D8}},
            {{225, 2}, {0x0003E1D, 0x0002BEC, 0x00057D8, 0x0003E1D}},
            {{315, 2}, {0x00057D8, 0x0003E1D, 0x0003E1D, 0x0002BEC}},
            {{45, 3}, {0x0001B4A, 0x000C5A6, 0x00003C4, 0x0001B4A}},
            {{135, 3}, {0x00003C4, 0x0001B4A, 0x0001B4A, 0x000C5A6}},
            {{225, 3}, {0x0001B4A, 0x00003C4, 0x000C5A6, 0x0001B4A}},
            {{315, 3}, {0x000C5A6, 0x0001B4A, 0x0001B4A, 0x00003C4}},
            {{45, 4}, {0x002463, 0x000789, 0x00AFB0, 0x002463}},
            {{135, 4}, {0x00AFB0, 0x002463, 0x002463, 0x000789}},
            {{225, 4}, {0x002463, 0x00AFB0, 0x000789, 0x002463}},
            {{315, 4}, {0x000789, 0x002463, 0x002463, 0x00AFB0}},
            {{45, 5}, {0x0003FAD, 0x0003739, 0x000496B, 0x0003FAD}},
            {{135, 5}, {0x000496B, 0x0003FAD, 0x0003FAD, 0x0003739}},
            {{225, 5}, {0x0003FAD, 0x000496B, 0x0003739, 0x0003FAD}},
            {{315, 5}, {0x0003739, 0x0003FAD, 0x0003FAD, 0x000496B}},
            {{45, 6}, {0x0002F0B, 0x00092D6, 0x0000F12, 0x0002F0B}},
            {{135, 6}, {0x0000F12, 0x0002F0B, 0x0002F0B, 0x00092D6}},
            {{225, 6}, {0x0002F0B, 0x0000F12, 0x00092D6, 0x0002F0B}},
            {{315, 6}, {0x00092D6, 0x0002F0B, 0x0002F0B, 0x0000F12}},
            {{45, 7}, {0x0000C37, 0x00000A5, 0x000E6EA, 0x0000C37}},
            {{135, 7}, {0x000E6EA, 0x0000C37, 0x0000C37, 0x00000A5}},
            {{225, 7}, {0x0000C37, 0x000E6EA, 0x00000A5, 0x0000C37}},
            {{315, 7}, {0x00000A5, 0x0000C37, 0x0000C37, 0x000E6EA}},
            {{45, 8}, {0x00039B3, 0x0001E24, 0x0006E73, 0x00039B3}},
            {{135, 8}, {0x0006E73, 0x00039B3, 0x00039B3, 0x0001E24}},
            {{225, 8}, {0x00039B3, 0x0006E73, 0x0001E24, 0x00039B3}},
            {{315, 8}, {0x0001E24, 0x00039B3, 0x00039B3, 0x0006E73}}
        };

        auto coeffs = lookup_table[{phi, r}];

        double r1 = convertToFixedPoint(std::get<0>(coeffs));
        double r2 = convertToFixedPoint(std::get<1>(coeffs));
        double r3 = convertToFixedPoint(std::get<2>(coeffs));
        double r4 = convertToFixedPoint(std::get<3>(coeffs));

        int x1 = std::floor(x);
        int x2 = std::ceil(x);
        int y1 = std::floor(y);
        int y2 = std::ceil(y);

        // Kiểm tra biên để không truy cập ngoài ảnh
        if (x1 < 0 || x2 >= image.rows || y1 < 0 || y2 >= image.cols)
            return 0;

        double interpolated_value =
            image.at<uchar>(x1, y1) * r1 +
            image.at<uchar>(x1, y2) * r2 +
            image.at<uchar>(x2, y1) * r3 +
            image.at<uchar>(x2, y2) * r4;

        return interpolated_value;
    }

    std::vector<double> getInterNeighbors(const cv::Mat& image, int r, int i, int j) {
    std::vector<double> S(9, 0);  // S[0] unused, S[1]..S[8]

    if (r == 1) {
        S[1] = image.at<uchar>(i, j + r);
        S[2] = image.at<uchar>(i - r, j + r);
        S[3] = image.at<uchar>(i - r, j);
        S[4] = image.at<uchar>(i - r, j - r);
        S[5] = image.at<uchar>(i, j - r);
        S[6] = image.at<uchar>(i + r, j - r);
        S[7] = image.at<uchar>(i + r, j);
        S[8] = image.at<uchar>(i + r, j + r);
        return S;
    }

    // Góc rời rạc
    std::vector<int> angles = {45, 135, 225, 315};
    std::vector<double> results(4, 0);  // results[0] -> 45, results[1] -> 135, etc.

    S[1] = image.at<uchar>(i, j + r);
    S[3] = image.at<uchar>(i - r, j);
    S[5] = image.at<uchar>(i, j - r);
    S[7] = image.at<uchar>(i + r, j);

    for (int idx = 0; idx < angles.size(); ++idx) {
        int angle = angles[idx];
        float theta = angle * static_cast<float>(CV_PI) / 180.0f;
        float target_x = i - r * std::sin(theta);
        float target_y = j + r * std::cos(theta);
    #ifdef FIX_INTER
        results[idx] = getInterpolationRphi(image, target_x, target_y, r, angle);
    #else 
        results[idx] = bilinearInterpolation(image, target_x, target_y);
    #endif
    }

    S[2] = results[0];  
    S[4] = results[1]; 
    S[6] = results[2];  
    S[8] = results[3];  

    return S;
}
    int getSumPixel(uint8_t pixel) {
        int sum = 0;
        for (int i = 0; i < 8; ++i) {
            sum += (pixel >> i) & 1;
        }
        return sum;
    }
 int checkU2(uint8_t pixel) {
    int transitions = 0;
    uint8_t first_bit = (pixel >> 7) & 1;
    uint8_t last_bit = pixel & 1;

    for (int i = 0; i < 7; ++i) {
        uint8_t current_bit = (pixel >> (7 - i)) & 1;
        uint8_t next_bit = (pixel >> (7 - (i + 1))) & 1;

        if (current_bit != next_bit)
            transitions++;
    }

    if (first_bit != last_bit)
        transitions++;

    return transitions;
}

        cv::Mat rdCalc(cv::Mat m1, cv::Mat m2, int r){
            cv::Mat newMat = cv::Mat::zeros(m2.rows - 2 * r, m2.cols - 2 * r, CV_8U);
            for (int i = r; i < m2.rows - r; i++)
            {
                for (int j = r; j < m2.cols - r; j++)

                {                  
                    std::vector<double> r1Neighbors = getInterNeighbors(m1, r - 1, i, j);
                    std::vector<double> r2Neighbors = getInterNeighbors(m2, r, i, j);
                    uint8_t res = 0;
                    for(int i = 1; i < 9; i++){
                        if(r2Neighbors[i] >= r1Neighbors[i]){
                             res += static_cast<uint8_t>(1 << (i - 1));
                        }

                    }
                    int x = 9;
                    if(checkU2(res) <= 2){
                        x =  getSumPixel(res);
                    }
                    newMat.at<uchar>(i - r, j - r) = static_cast<uchar>(x);
 


                }
            }
            return newMat;

        }
        cv::Mat niCalc(cv::Mat medianImage, int r){
            cv::Mat newMat = cv::Mat::zeros(medianImage.rows - 2 * r, medianImage.cols - 2 * r, CV_8U);
            int size = (2 * r + 1) * (2 * r + 1);
             for (int i = r; i < medianImage.rows - r; i++)
            {
                for (int j = r; j < medianImage.cols - r; j++)

                {
                    uint16_t sum = 0;

                    for (int k = -r; k <= r; k++)
                    {
                        for (int l = -r; l <= r; l++)
                        {
                            sum += medianImage.at<uchar>(i + k, j + l);
                        }
                    }
                    std::vector<double> r2Neighbors = getInterNeighbors(medianImage, r, i, j);
                    uint8_t res = 0;
                    for(int i = 1; i < 9; i++){
                        double scale = r2Neighbors[i] * size;
                        if(scale >= sum){
                             res += static_cast<uint8_t>(1 << (i - 1));
                        }

                    }
                    int x = 9;
                    if(checkU2(res) <= 2){
                        x =  getSumPixel(res);
                    }
                    newMat.at<uchar>(i - r, j - r) = static_cast<uchar>(x);
 


                }
            }
            return newMat;



        }


        cv::Mat niCalcOg(cv::Mat medianImage, int r){
            cv::Mat newMat = cv::Mat::zeros(medianImage.rows - 2 * r, medianImage.cols - 2 * r, CV_8U);
            int size = (2 * r + 1) * (2 * r + 1);
             for (int i = r; i < medianImage.rows - r; i++)
            {
                for (int j = r; j < medianImage.cols - r; j++)

                {
                    
                    std::vector<double> r2Neighbors = getInterNeighbors(medianImage, r, i, j);
                    double sum_of_phi_neighbors = 0.0;
                    for (int k = 1; k <= 8; ++k) {
                        sum_of_phi_neighbors += r2Neighbors[k];
                    }
                    uint8_t res = 0;
                    for(int i = 1; i < 9; i++){
                        double scale = r2Neighbors[i] * size;
                        if(scale >= sum_of_phi_neighbors){
                             res += static_cast<uint8_t>(1 << (i - 1));
                        }

                    }
                    int x = 9;
                    if(checkU2(res) <= 2){
                        x =  getSumPixel(res);
                    }
                    newMat.at<uchar>(i - r, j - r) = static_cast<uchar>(x);
 


                }
            }
            return newMat;



        }
        std::vector<uint16_t> jointHistogram(const cv::Mat& ci, const cv::Mat& ni, const cv::Mat& rd) {
            CV_Assert(ci.size() == ni.size() && ni.size() == rd.size());
            int width = ci.rows;
            int height = ci.cols;

            std::vector<uint16_t> out_matrix(200, 0);  // Khởi tạo histogram

            for (int i = 0; i < width; ++i) {
                for (int j = 0; j < height; ++j) {
                    int c = ci.at<uchar>(i, j);
                    int n = ni.at<uchar>(i, j);
                    int r = rd.at<uchar>(i, j);

                    int index = c * 100 + n * 10 + r;
                    if (index < 200) {  
                        out_matrix[index]++;
                    }
                }
            }

            return out_matrix;
        }

        cv::Mat medianProcessing(cv::Mat gray, int window_size)
        {
            assert(window_size == 3 || window_size == 5 || window_size == 7 || window_size == 9);

            int w = window_size / 2;
            cv::Mat padded;

            // std::cout << "Size" << " " << w <<   " " << gray.rows << " " <<gray.cols << std::endl;
            cv::copyMakeBorder(gray, padded,
                               w, w, w, w,
                               cv::BORDER_CONSTANT, cv::Scalar(0));

            cv::Mat medianMat(gray.rows, gray.cols, CV_8U, cv::Scalar(0));
            // std::cout << medianMat.size() << std::endl;
            // printMat(padded);
            for (int i = w; i <=gray.rows + (w - 1); i++)
            {
                for (int j = w; j <= gray.cols + (w - 1); j++)
                {
                    std::vector<int> window_t(window_size * window_size);
                    int idx = 0;
                    for (int k = -w; k <= w; k++)
                    {
                        for (int l = -w; l <= w; l++)
                        {
                            window_t[idx++] = static_cast<int>(padded.at<uchar>(i +k, j +l ));
                        }
                    }
                //    if(i == 4 && j == 31){
                //     for(int i = 0 ;i < window_t.size(); i++){
                //         std::cout << window_t[i] <<  " ";
                //     }
                //     std::cout<<std::endl;
                // }
                    std::sort(window_t.begin(), window_t.end());
                    
                    // return medianMat;
                    medianMat.at<uchar>(i - w, j - w) = window_t[window_t.size() / 2];
                }
            }
            return medianMat;
        }
        cv::Mat ciCal(cv::Mat medianImage, int r)
        {

            cv::Mat newMat = cv::Mat::zeros(medianImage.rows - 2 * r, medianImage.cols - 2 * r, CV_8U);
            for (int i = r; i < medianImage.rows - r; i++)
            {
                for (int j = r; j < medianImage.cols - r; j++)
                {
                    uint8_t center = medianImage.at<uchar>(i, j);
                    uint16_t sum = 0;

                    for (int k = -r; k <= r; k++)
                    {
                        for (int l = -r; l <= r; l++)
                        {
                            sum += medianImage.at<uchar>(i + k, j + l);
                            // std::cout << static_cast<int>(medianImage.at<uchar>(i + k, j + l)) << " ";
                        }
                        // std::cout << std::endl;
                    }
                    // std::cout << sum << std::endl;

                    uint16_t center_scale = center * ((2 * r + 1) * (2 * r + 1));
                    int decision = 0;
                    if (center_scale >= sum)
                    {
                        decision = 1;
                    }
                    newMat.at<uchar>(i - r, j - r) = static_cast<uchar>(decision);
                }
            }

            return newMat;
        }

        cv::Mat ciCalNoOP(cv::Mat medianImage, int r)
        {

            cv::Mat newMat = cv::Mat::zeros(medianImage.rows - 2 * r, medianImage.cols - 2 * r, CV_8U);
            long long sum = 0;
            for(int i = 0 ;i < medianImage.rows; i++){
                for(int j = 0; j < medianImage.cols; j++){
                    sum +=  medianImage.at<uchar>(i, j);
                }
            }
            double mean = (double)sum* 1.00 / (medianImage.rows * medianImage.cols) ;
            for (int i = r; i < medianImage.rows - r; i++)
            {
                for (int j = r; j < medianImage.cols - r; j++)
                {
                    uint8_t center = medianImage.at<uchar>(i, j);
                        
                    int decision = 0;
                    if (center >= center)
                    {
                        decision = 1;
                    }
                    newMat.at<uchar>(i - r, j - r) = static_cast<uchar>(decision);
                }
            }

            return newMat;
        }

        std::vector<uint16_t> run(cv::Mat image)
        {
            cv::Mat m_3x3 = medianProcessing(image, 3);
            cv::Mat m_5x5 = medianProcessing(image, 5);
            cv::Mat m_7x7 = medianProcessing(image, 7);
        #ifdef USE_R8
            cv::Mat m_9x9 = medianProcessing(image, 9);
        #endif
            // write2File("../median_3x3_cpp.txt", m_3x3);
            // write2File("../median_5x5_cpp.txt", m_5x5);
            // write2File("../median_7x7_cpp.txt", m_7x7);
            // printMat(m_3x3);
            // std::cout << m_5x5.rows << " " << m_5x5.cols << std::endl;


#ifdef CI_HARDWARE
            cv::Mat ci_r2 = ciCal(m_3x3, 2);
            cv::Mat ci_r4= ciCal(m_3x3, 4);
            cv::Mat ci_r6 = ciCal(m_3x3, 6);
            #ifdef USE_R8
            cv::Mat ci_r8 = ciCal(m_3x3, 8);
            #endif
#else 
            cv::Mat ci_r2 = ciCalNoOP(m_3x3, 2);
            cv::Mat ci_r4= ciCalNoOP(m_3x3, 4);
            cv::Mat ci_r6 = ciCalNoOP(m_3x3, 6);
            #ifdef USE_R8
            cv::Mat ci_r8 = ciCalNoOP(m_3x3, 8);
            #endif
#endif 

            // write2File("../ci_r2_cpp.txt", ci_r2);
            // write2File("../ci_r4_cpp.txt", ci_r4);
            // write2File("../ci_r6_cpp.txt", ci_r6);
#ifdef NI_OP
            cv::Mat ni_r2 = niCalc(m_3x3, 2);
            cv::Mat ni_r4 = niCalc(m_5x5, 4);
            cv::Mat ni_r6 = niCalc(m_7x7, 6);
            #ifdef USE_R8
            cv::Mat ni_r8 = niCalc(m_9x9, 8);
            #endif

#else 
            cv::Mat ni_r2 = niCalcOg(m_3x3, 2);
            cv::Mat ni_r4 = niCalcOg(m_5x5, 4);
            cv::Mat ni_r6 = niCalcOg(m_7x7, 6);
            #ifdef USE_R8
            cv::Mat ni_r8 = niCalcOg(m_9x9, 8);
            #endif



#endif

            // write2File("../ni_r2_cpp.txt", ni_r2);
            // write2File("../ni_r4_cpp.txt", ni_r4);
            // write2File("../ni_r6_cpp.txt", ni_r6);


            cv::Mat rd_r2 = rdCalc(image, m_3x3, 2);
            cv::Mat rd_r4 = rdCalc(m_3x3, m_5x5, 4);
            cv::Mat rd_r6 = rdCalc(m_5x5, m_7x7, 6);
            #ifdef USE_R8
            cv::Mat rd_r8 = rdCalc(m_7x7, m_9x9, 8);
            #endif


            // write2File("../rd_r2_cpp.txt", rd_r2);
            // write2File("../rd_r4_cpp.txt", rd_r4);
            // write2File("../rd_r6_cpp.txt", rd_r6);

            std::vector<uint16_t> hist_r2 = jointHistogram(ci_r2, ni_r2, rd_r2);
            std::vector<uint16_t> hist_r4 = jointHistogram(ci_r4, ni_r4, rd_r4);
            std::vector<uint16_t> hist_r6 = jointHistogram(ci_r6, ni_r6, rd_r6);
            #ifdef USE_R8
            std::vector<uint16_t> hist_r8 = jointHistogram(ci_r8, ni_r8, rd_r8);
            #endif
            std::vector<uint16_t> hist_o;
            hist_o.reserve(600);
            hist_o.insert(hist_o.end(), hist_r2.begin(), hist_r2.end());
            hist_o.insert(hist_o.end(), hist_r4.begin(), hist_r4.end());
            hist_o.insert(hist_o.end(), hist_r6.begin(), hist_r6.end());

            #ifdef USE_R8
            hist_o.insert(hist_o.end(), hist_r8.begin(), hist_r8.end());
            #endif

            // std::ofstream fout("../histogram_cpp.txt");
            //     if (!fout.is_open()) {
            //         std::cerr << "Cannot open file: " << std::endl;
            //         return;
            //     }

            //     for (const auto& val : hist_o) {
            //         fout << val << "\n";
            //     }
            // fout.close();
            return hist_o;

        }
    };
};

cv::Mat readMatrixFromFile(const std::string &filename, int rows, int cols)
{
    std::ifstream file(filename);
    if (!file.is_open())
    {
        std::cerr << "Error: Unable to open file!" << std::endl;
        return cv::Mat();
    }

    std::vector<uint8_t> data;
    std::string line;

    // Read the file line by line
    while (std::getline(file, line))
    {
        std::istringstream stream(line);
        int value;
        while (stream >> value)
        {
            data.push_back(static_cast<uint8_t>(value));
        }
    }

    file.close();

    // Ensure the data matches the expected size
    if (data.size() != rows * cols)
    {
        std::cerr << "Error: Mismatch between file data and specified dimensions!" << std::endl;
        return cv::Mat();
    }

    // Create the matrix from the data
    cv::Mat mat(rows, cols, CV_8U, data.data());
    return mat.clone(); // Clone to ensure independent memory allocation
}

// int main()
// {
//     // Path to the input image and the output grayscale image
//     // std::string inputPath = "/home/ms1sm/Documents/Code/Thesis/data/Ex/sample.bmp"; // Change to your input image path
//     std::string input_matrix_path = "../random_matrix.txt";
//     // // // Create an instance of MRELBP and process the image
//     LBP::MRELBP processor;
//     // cv::Mat image = cv::imread(inputPath, cv::IMREAD_COLOR);

//     // if (image.empty()) {
//     //     std::cout << "Not a valid image file" << std::endl;
//     //     return -1;
//     // }

//     // std::vector<cv::Mat> channels(3);
//     // cv::split(image, channels);

//     // // cv::namedWindow("Simple Demo", cv::WINDOW_AUTOSIZE);
//     // // cv::imshow("Simple Demo", image);

//     // // cv::waitKey(0);
//     // // cv::destroyAllWindows();
//     // std::cout << CV_VERSION << std::endl;

//     cv::Mat mat = readMatrixFromFile(input_matrix_path, 128, 128);
//     // printMat(mat);

//     // cv::Mat medianMat = processor.medianProcessing(mat, 3);
//     // printMat(medianMat);
//         auto start = std::chrono::high_resolution_clock::now();

//     processor.run(mat);
//         auto end = std::chrono::high_resolution_clock::now();
// std::chrono::duration<double> duration = end - start;
//     std::cout << "Time taken by run(): " << duration.count() << " seconds\n";

//     return 0;
// }


namespace py = pybind11;
LBP::MRELBP processor;
std::vector<uint16_t> run_from_python(py::array_t<uint8_t> input_array) {
    py::buffer_info buf = input_array.request();
    int height = buf.shape[0];
    int width = buf.shape[1];
    uint8_t* ptr = static_cast<uint8_t*>(buf.ptr);

    cv::Mat input_image(height, width, CV_8UC1, ptr);
    return processor.run(input_image);
}

PYBIND11_MODULE(mrelbp, m) {
    m.def("run", &run_from_python, "Run MRELBP on image");
}