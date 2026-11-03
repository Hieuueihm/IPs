// Black-box driver for the isolated sharing experiment. Golden input/output files
// are unchanged; this driver only loads RAM, starts the core and compares outputs.
#include "Vntt_core.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static uint64_t simulation_ticks = 0;
double sc_time_stamp() { return static_cast<double>(simulation_ticks); }

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc != 2) return 2;
    std::ifstream in(argv[1]);
    if (!in) return 3;
    Vntt_core d;
    auto tick = [&]() { d.clk=0; ++simulation_ticks; d.eval(); d.clk=1; ++simulation_ticks; d.eval(); };
    d.rst=1; d.load_valid=0; d.read_valid=0; d.start=0;
    for (int i=0;i<4;++i) tick();
    d.rst=0; tick();
    int prof,logn,op,cases=0;
    uint64_t errors=0;
    auto word = [&]() {
        std::string s;
        if (!(in>>s)) throw std::runtime_error("truncated golden vector");
        return static_cast<uint32_t>(std::stoul(s,nullptr,16));
    };
    while (in>>prof>>logn>>op) {
        int fmt=prof>=3 ? prof-3 : 0;
        int n=(1<<logn) << fmt;
        std::vector<uint32_t> a(n),expected(n);
        for(auto &v:a) v=word();
        for(auto &v:expected) v=word();
        if(d.busy) throw std::runtime_error("core still busy before host load");
        for(int l=0;l<n/4;++l) {
            d.load_valid=1;d.load_line=l;
            for(int k=0;k<4;++k)d.load_data[k]=a[4*l+k];
            tick();
        }
        d.load_valid=0;tick();
        d.start_fft=prof>=3;d.start_fmt=fmt;d.start_profile=prof&3;
        d.start_inverse=prof>=3 ? op==1 : op==6;d.start_logn=logn;
        d.start=1;tick();d.start=0;
        int timeout=0;
        while(!d.done && ++timeout<200000)tick();
        if(timeout>=200000 || d.error)throw std::runtime_error("command timeout/error");
        auto cycles=d.cycles;
        uint64_t before=errors;
        for(int l=0;l<n/4;++l) {
            d.read_valid=1;d.read_line=l;tick();d.read_valid=0;
            int wait=0;
            while(!d.read_rsp_valid && ++wait<20)tick();
            if(!d.read_rsp_valid)throw std::runtime_error("read timeout");
            for(int k=0;k<4;++k) if(d.read_data[k]!=expected[4*l+k])++errors;
            tick();
        }
        std::cout<<"CASE "<<cases++<<" profile="<<prof<<" logn="<<logn<<" op="<<op
                 <<" err="<<(errors-before)<<" cycles_b="<<cycles<<std::endl;
    }
    std::cout<<"TOTAL cases="<<cases<<" err="<<errors<<(errors?" FAIL":" PASS")<<std::endl;
    d.final();return errors ? 1 : 0;
}
