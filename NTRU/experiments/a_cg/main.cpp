#include "Va_cg_core.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>

static uint64_t ticks=0;
double sc_time_stamp(){return static_cast<double>(ticks);}
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);
    if(argc!=2)return 2;
    std::ifstream f(argv[1],std::ios::binary);
    auto word=[&](){uint32_t x;f.read(reinterpret_cast<char*>(&x),4);if(!f)throw std::runtime_error("short fixture");return x;};
    if(word()!=0x43474131)throw std::runtime_error("fixture magic");
    auto count=word(); Va_cg_core d;
    auto tick=[&](){d.clk=0;++ticks;d.eval();d.clk=1;++ticks;d.eval();};
    auto wait=[&](auto predicate,int max,const char*what){int n=0;while(!predicate()){if(n++>max)throw std::runtime_error(what);tick();}};
    d.rst=1;d.cfg_valid=0;d.root_we=0;d.root_commit=0;d.desc_we=0;
    d.load_valid=0;d.read_valid=0;d.start=0;
    for(int j=0;j<4;++j)tick();d.rst=0;tick();
    uint64_t errors=0;
    // A command without configuration must fail without starting the engine.
    d.start=1;tick();d.start=0;if(!d.done||!d.error||d.busy)throw std::runtime_error("unconfigured start accepted");tick();
    for(unsigned c=0;c<count;++c){
        auto fft=word(),fmt=word(),ln=word(),hm=word(),inv=word(),q=word(),qi=word();
        auto stages=word(),nr=word(),nw=word();uint64_t beginning=ticks;
        wait([&](){return d.cfg_ready;},50,"cfg ready");
        d.cfg_fft=fft;d.cfg_fmt=fmt;d.cfg_logn=ln;d.cfg_hmin=hm;
        d.cfg_inverse=inv;d.cfg_q=q;d.cfg_qinv=qi;d.cfg_valid=1;tick();d.cfg_valid=0;
        if(d.error)throw std::runtime_error("valid cfg rejected");
        for(unsigned s=0;s<stages;++s){
            d.desc_mask=word();d.desc_root_base=word();d.desc_root_mask=word();
            d.desc_stage=s;d.desc_we=1;tick();
        }d.desc_we=0;
        for(unsigned b=0;b<16;++b)for(unsigned a=0;a<nr;++a){
            d.root_bank=b;d.root_addr=a;d.root_data=word();d.root_we=1;tick();
        }d.root_we=0;d.root_commit=1;tick();d.root_commit=0;
        std::vector<uint32_t>a(nw),z(nw);for(auto&v:a)v=word();for(auto&v:z)v=word();
        for(unsigned l=0;l<(nw+3)/4;++l){
            wait([&](){return d.load_ready;},50,"load ready");
            d.load_line=l;for(unsigned j=0;j<4;++j)d.load_data[j]=4*l+j<nw?a[4*l+j]:0;
            d.load_valid=1;tick();d.load_valid=0;
        }
        wait([&](){return d.load_ready;},50,"final load");
        d.start=1;tick();d.start=0;
        wait([&](){return d.done;},200000,"kernel timeout");
        if(d.error)throw std::runtime_error("kernel error");
        auto cycles=d.cycles;unsigned errs=0;tick();
        for(unsigned l=0;l<(nw+3)/4;++l){
            wait([&](){return d.read_ready;},50,"read ready");
            d.read_line=l;d.read_valid=1;tick();d.read_valid=0;
            wait([&](){return d.read_rsp_valid;},50,"read response");
            for(unsigned j=0;j<4&&4*l+j<nw;++j)if(d.read_data[j]!=z[4*l+j]){
                if(errs<4)std::cout<<"MISMATCH case="<<c<<" word="<<4*l+j<<" got="<<std::hex<<d.read_data[j]<<" expected="<<z[4*l+j]<<std::dec<<std::endl;
                ++errs;
            }
            tick();
        }
        errors+=errs;
        std::cout<<"CASE "<<c<<" fft="<<fft<<" fmt="<<fmt<<" logn="<<ln<<" hmin="<<hm<<" inverse="<<inv
                 <<" q="<<q<<" errors="<<errs<<" cycles="<<cycles<<" all_host_cycles="<<(ticks-beginning)/2<<std::endl;
        if(errs)break;
    }
    std::cout<<"TOTAL cases="<<count<<" errors="<<errors<<(errors?" FAIL":" PASS")<<std::endl;
    d.final();return errors?1:0;
}
