#include "Va_cg_fast.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <map>

static uint64_t ticks=0;
double sc_time_stamp(){return static_cast<double>(ticks);}
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);
    if(argc!=2&&argc!=3)return 2;
    std::ifstream f(argv[1],std::ios::binary);
    auto word=[&](){uint32_t x;f.read(reinterpret_cast<char*>(&x),4);if(!f)throw std::runtime_error("short fixture");return x;};
    if(word()!=0x43474632)throw std::runtime_error("fixture magic");
    auto count=word(); Va_cg_fast d;
    std::ofstream result;
    if(argc==3){result.open(argv[2],std::ios::binary);uint32_t magic=0x4f554732;result.write(reinterpret_cast<char*>(&magic),4);result.write(reinterpret_cast<char*>(&count),4);}
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
        auto native=word(),stages=word(),nr=word(),nw=word();uint64_t beginning=ticks;
        wait([&](){return d.cfg_ready;},50,"cfg ready");
        d.cfg_fft=fft;d.cfg_fmt=fmt;d.cfg_logn=ln;d.cfg_hmin=hm;
        d.cfg_inverse=inv;d.cfg_ntrugen=native;d.cfg_q=q;d.cfg_qinv=qi;d.cfg_valid=1;tick();d.cfg_valid=0;
        if(d.error)throw std::runtime_error("valid cfg rejected");
        for(unsigned s=0;s<stages;++s){
            d.desc_mask=word();d.desc_root_base=word();d.desc_root_mask=word();d.desc_gap=word();
            d.desc_stage=s;d.desc_we=1;tick();
        }d.desc_we=0;
        std::vector<std::vector<uint32_t>> roots(16,std::vector<uint32_t>(nr));
        for(auto &lane:roots)for(auto &x:lane)x=word();
        unsigned root_writes=0;
        for(unsigned a=0;a<nr;++a){
            std::map<uint32_t,uint16_t> groups;
            for(unsigned b=0;b<16;++b)groups[roots[b][a]]|=1u<<b;
            for(auto item:groups){d.root_dest=item.second;d.root_addr=a;d.root_data=item.first;d.root_we=1;tick();++root_writes;}
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
        unsigned sent=0,received=0,lines=(nw+3)/4,read_timeout=0;
        std::vector<uint32_t> actual(nw);
        while(received<lines){
            d.read_valid=sent<lines;d.read_line=sent;
            bool accepted=d.read_valid&&d.read_ready;tick();
            if(accepted)++sent;
            if(d.read_rsp_valid){
                for(unsigned j=0;j<4&&4*received+j<nw;++j)actual[4*received+j]=d.read_data[j];
                for(unsigned j=0;j<4&&4*received+j<nw;++j)if(d.read_data[j]!=z[4*received+j]){
                    if(errs<4)std::cout<<"MISMATCH case="<<c<<" word="<<4*received+j<<" got="<<std::hex<<d.read_data[j]<<" expected="<<z[4*received+j]<<std::dec<<std::endl;
                    ++errs;
                }
                ++received;
            }
            if(++read_timeout>20000)throw std::runtime_error("burst read timeout");
        }
        d.read_valid=0;tick();
        if(result){result.write(reinterpret_cast<char*>(&nw),4);result.write(reinterpret_cast<char*>(actual.data()),4*nw);}
        errors+=errs;
        std::cout<<"CASE "<<c<<" native="<<native<<" fft="<<fft<<" fmt="<<fmt<<" logn="<<ln<<" hmin="<<hm<<" inverse="<<inv
                 <<" q="<<q<<" errors="<<errs<<" cycles="<<cycles<<" root_writes="<<root_writes<<" all_host_cycles="<<(ticks-beginning)/2<<std::endl;
        if(errs)break;
    }
    std::cout<<"TOTAL cases="<<count<<" errors="<<errors<<(errors?" FAIL":" PASS")<<std::endl;
    d.final();return errors?1:0;
}
