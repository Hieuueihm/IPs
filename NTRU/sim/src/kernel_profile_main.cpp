#include "Vflex_kernel_profile.h"
#include "verilated.h"
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
using Word=std::array<uint32_t,4>;
static Vflex_kernel_profile* d;
static uint64_t ticks=0;
static uint32_t rng=0x51a62731;
static bool paused_run=false;
double sc_time_stamp(){return double(ticks);}
static Word parse(const std::string& s){Word v{};std::string x=std::string(32-s.size(),'0')+s;for(int i=0;i<4;i++)v[i]=std::stoul(x.substr(24-i*8,8),nullptr,16);return v;}
static void step(){
    d->clk=1;d->eval();d->clk=0;d->eval();ticks++;
    rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;
    d->pause=paused_run&&((rng&31)==0);d->eval();
}
template<class F>static void wait_for(F ready){for(int n=0;n<2000000;n++){d->eval();if(ready())return;step();}throw std::runtime_error("Timeout");}
int main(int argc,char** argv){
    Verilated::commandArgs(argc,argv);
    if(argc!=5){std::cerr<<"requests actual metrics pause(0/1)\n";return 2;}
    Vflex_kernel_profile model;d=&model;paused_run=std::string(argv[4])=="1";
    try{
        std::ifstream in(argv[1]);std::ofstream actual(argv[2]),stats(argv[3]);
        if(!in||!actual||!stats)throw std::runtime_error("Cannot open files");
        stats<<"id,op,width,logn,profile";for(int i=0;i<96;i++)stats<<",c"<<i;stats<<'\n';
        d->rst=1;d->load_valid=0;d->start_valid=0;d->read_valid=0;d->done_ready=0;step();step();d->rst=0;d->eval();
        int op,width,logn,profile,na,nb,ny,id=0;uint64_t words=0,cycles=0;
        while(in>>op>>width>>logn>>profile>>na>>nb>>ny){
            std::vector<Word>a(na),b(nb),expected(ny);std::string s;
            for(auto* v:{&a,&b,&expected})for(auto& x:*v){if(!(in>>s))throw std::runtime_error("Truncated vectors");x=parse(s);}
            d->cfg_op=op;d->cfg_width=width;d->cfg_logn=logn;d->cfg_profile=profile;d->eval();
            for(int bank=0;bank<2;bank++){
                auto& v=bank?b:a;
                for(unsigned i=0;i<v.size();i++){
                    d->load_bank=bank;d->load_address=i;for(int j=0;j<4;j++)d->load_data[j]=v[i][j];
                    d->load_valid=1;d->eval();wait_for([](){return d->load_ready;});step();
                }
            }
            d->load_valid=0;d->start_valid=1;d->eval();wait_for([](){return d->start_ready;});step();d->start_valid=0;d->eval();
            wait_for([](){return d->done_valid;});
            if(d->error||d->cycles!=d->metrics[0])throw std::runtime_error("DUT error/counter mismatch at "+std::to_string(id));
            stats<<id<<','<<op<<','<<width<<','<<logn<<','<<profile;
            for(int i=0;i<96;i++)stats<<','<<d->metrics[i];stats<<'\n';cycles+=d->cycles;
            actual<<id<<' '<<ny<<'\n';
            for(int i=0;i<ny;i++){
                d->read_address=i;d->read_valid=1;d->eval();wait_for([](){return d->read_ready;});step();d->read_valid=0;d->eval();
                wait_for([](){return d->read_response_valid;});Word x{};
                for(int j=0;j<4;j++)x[j]=d->read_data[j];
                if(x!=expected[i])throw std::runtime_error("Output mismatch id="+std::to_string(id)+" word="+std::to_string(i));
                actual<<std::hex<<std::setfill('0');for(int j=3;j>=0;j--)actual<<std::setw(8)<<x[j];actual<<std::dec<<'\n';words++;
            }
            d->done_ready=1;wait_for([](){return !d->pause;});step();wait_for([](){return d->start_ready;});d->done_ready=0;d->eval();id++;
            if(id%500==0)std::cerr<<"PASS "<<id<<"\n";
        }
        std::cout<<"{\"kernels\":"<<id<<",\"words\":"<<words<<",\"cycles\":"<<cycles<<",\"ticks\":"<<ticks<<",\"pause\":"<<paused_run<<"}\n";
        model.final();return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
