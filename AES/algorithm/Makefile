TARGET = aes_run

CXX = g++

CXXFLAGS = -Wall -Wextra -std=c++17

SRCS = main.cpp aes.cpp

HDRS = *.hpp

OBJS = $(SRCS:.cpp=.o)

PHONY: all
all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $^

%.o: %.cpp $(HDRS)
	$(CXX) $(CXXFLAGS) -c $< -o $@

PHONY: clean
clean:
	rm -f $(OBJS) $(TARGET)
