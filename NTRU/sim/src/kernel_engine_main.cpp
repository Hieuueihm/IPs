#include "Vflex_kernel_engine.h"
#include "verilated.h"
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>

using Word=std::array<uint32_t,4>;
static uint64_t ticks=0;
double sc_time_stamp(){return double(ticks);}
static uint32_t rng=0x51a62731;
static uint64_t pauses=0;
static Vflex_kernel_engine* dut;
static Word parse(const std::string& s){
    Word v{};std::string x=std::string(32-s.size(),'0')+s;
    for(int i=0;i<4;i++)v[i]=std::stoul(x.substr(24-i*8,8),nullptr,16);
    return v;
}
template<class T> static void put(T& port,const Word& v){for(int i=0;i<4;i++)port[i]=v[i];}
static Word get(){Word v;for(int i=0;i<4;i++)v[i]=dut->read_data[i];return v;}
static std::string hex(const Word& v){std::ostringstream s;s<<std::hex<<std::setfill('0');for(int i=3;i>=0;i--)s<<std::setw(8)<<v[i];return s.str();}
static void step(bool random_pause=true){
    dut->clk=1;dut->eval();dut->clk=0;dut->eval();ticks++;
    rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;
    dut->pause=random_pause&&((rng&31)==0);if(dut->pause)pauses++;
    dut->eval();
}
template<class F> static void wait_for(F ready){
    for(unsigned i=0;i<2000000;i++){dut->eval();if(ready())return;step();}
    throw std::runtime_error("Timeout waiting for engine");
}
static void reset(){dut->rst=1;dut->load_valid=0;dut->start_valid=0;dut->read_valid=0;dut->done_ready=0;step(false);step(false);dut->rst=0;dut->eval();}
int main(int argc,char** argv){
    Verilated::commandArgs(argc,argv);
    if(argc<3){std::cerr<<"usage: kernel_engine requests actual\n";return 2;}
    Vflex_kernel_engine model;dut=&model;
    try{
        reset();std::ifstream in(argv[1]);std::ofstream out(argv[2]);
        if(!in||!out)throw std::runtime_error("Cannot open vectors");
        unsigned id=0,words=0;int op,width,logn,profile,na,nb,ny;
        uint64_t core_cycles=0;
        while(in>>op>>width>>logn>>profile>>na>>nb>>ny){
            std::vector<Word>a(na),b(nb),expected(ny);std::string s;
            for(auto* v:{&a,&b,&expected})for(auto& w:*v){if(!(in>>s))throw std::runtime_error("Truncated request");w=parse(s);}
            dut->cfg_op=op;dut->cfg_width=width;dut->cfg_logn=logn;dut->cfg_profile=profile;dut->eval();
            for(int bank=0;bank<2;bank++){
                const auto& v=bank?b:a;
                for(unsigned i=0;i<v.size();i++){
                    dut->load_valid=1;dut->load_bank=bank;dut->load_address=i;put(dut->load_data,v[i]);dut->eval();
                    wait_for([](){return dut->load_ready;});step();
                }
            }
            dut->load_valid=0;dut->start_valid=1;dut->eval();wait_for([](){return dut->start_ready;});step();
            dut->start_valid=0;dut->eval();wait_for([](){return dut->done_valid;});
            if(dut->error)throw std::runtime_error("Unexpected configuration error at request "+std::to_string(id));
            core_cycles+=dut->cycles;
            // Random DONE stalls; completion must remain asserted and memory stable.
            for(int j=0;j<int(id%5);j++){step();if(!dut->done_valid)throw std::runtime_error("DONE not held");}
            out<<id<<' '<<ny<<'\n';
            for(int j=0;j<ny;j++){
                dut->read_address=j;dut->read_valid=1;dut->eval();wait_for([](){return dut->read_ready;});step();
                dut->read_valid=0;dut->eval();wait_for([](){return dut->read_response_valid;});
                Word actual=get();out<<hex(actual)<<'\n';words++;
                if(actual!=expected[j]){
                    std::cerr<<"Mismatch id="<<id<<" op="<<op<<" width="<<width<<" logn="<<logn<<" profile="<<profile<<" word="<<j<<" got="<<hex(actual)<<" expected="<<hex(expected[j])<<"\n";return 1;
                }
            }
            dut->done_ready=1;wait_for([](){return !dut->pause;});step();
            // A pending read response may defer completion for one cycle.
            wait_for([](){return dut->start_ready;});dut->done_ready=0;dut->eval();
            id++;if(id%200==0)std::cerr<<"PASS "<<id<<" kernels\n";
        }
        // Invalid command is rejected, then reset aborts a running transform.
        dut->cfg_op=15;dut->start_valid=1;wait_for([](){return dut->start_ready;});step();dut->start_valid=0;
        wait_for([](){return dut->done_valid;});if(!dut->error)throw std::runtime_error("Invalid op accepted");
        reset();dut->cfg_op=0;dut->cfg_logn=10;dut->cfg_width=2;dut->start_valid=1;step();dut->start_valid=0;
        for(int i=0;i<20;i++)step();reset();if(!dut->start_ready)throw std::runtime_error("Reset abort failed");
        std::cout<<"{\"kernels\":"<<id<<",\"words\":"<<words<<",\"ticks\":"<<ticks<<",\"core_cycles\":"<<core_cycles<<",\"pause_cycles\":"<<pauses<<",\"invalid_op_rejected\":true,\"reset_abort\":true}\n";
        model.final();return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 2;}
}
