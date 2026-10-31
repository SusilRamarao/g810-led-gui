CXX ?= g++
CXXFLAGS ?= -O2 -Wall -fPIC -std=c++11

INCLUDES = -I. -I../src/classes -I../../g810-led-gui/src/classes -I/usr/include
LIB_DIRS = -L../lib -L../../g810-led-gui/lib -L/usr/lib -L/usr/local/lib
LIBS = -lg810-led -lhidapi-hidraw

OUTPUT = libg810_bridge.so

.PHONY: all clean

all: $(OUTPUT)

$(OUTPUT): g810_bridge.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -shared -Wl,-soname,$(OUTPUT) -Wl,-rpath,'$$ORIGIN/../lib' -Wl,-rpath,'$$ORIGIN' -o $@ $^ $(LIB_DIRS) $(LIBS)
	mkdir -p ../lib
	cp $(OUTPUT) ../lib/$(OUTPUT)

clean:
	rm -f $(OUTPUT) ../lib/$(OUTPUT)
