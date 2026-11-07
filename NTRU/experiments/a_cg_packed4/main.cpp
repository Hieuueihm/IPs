#include "Va_cg_axil.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

static uint64_t ticks=0;
double sc_time_stamp(){return double(ticks);}
int main(int argc,char**argv){
    Verilated::commandArgs(argc,argv);
    if(argc!=2 && argc!=3)return 2;
    Va_cg_axil d;
    auto tick=[&](){d.aclk=0;d.eval();++ticks;d.aclk=1;d.eval();};
    auto idle=[&](){d.s_axi_awvalid=0;d.s_axi_wvalid=0;d.s_axi_bready=0;d.s_axi_arvalid=0;d.s_axi_rready=0;};
    d.aresetn=0;idle();d.s_axi_awprot=0;d.s_axi_arprot=0;d.s_axi_wstrb=15;
    for(int i=0;i<8;++i)tick();d.aresetn=1;for(int i=0;i<10;++i)tick();
    unsigned writes=0,reads=0;
    auto wr=[&](unsigned addr,uint32_t value,unsigned strobe=15,unsigned expected=0){
        unsigned id=writes++,agap=id%3,wgap=2-agap;bool aw=false,w=false;
        d.s_axi_awaddr=addr;d.s_axi_wdata=value;d.s_axi_wstrb=strobe;
        for(unsigned n=0;!aw||!w;++n){
            if(n>100)throw std::runtime_error("AXI write timeout");
            d.s_axi_awvalid=!aw&&n>=agap;d.s_axi_wvalid=!w&&n>=wgap;
            d.aclk=0;d.eval();bool af=d.s_axi_awvalid&&d.s_axi_awready,wf=d.s_axi_wvalid&&d.s_axi_wready;
            tick();aw|=af;w|=wf;
        }
        d.s_axi_awvalid=0;d.s_axi_wvalid=0;
        for(unsigned n=0;!d.s_axi_bvalid;++n){if(n>100)throw std::runtime_error("AXI B timeout");tick();}
        unsigned resp=d.s_axi_bresp;
        for(unsigned n=0;n<id%4;++n){tick();if(!d.s_axi_bvalid||d.s_axi_bresp!=resp)throw std::runtime_error("B changed under stall");}
        if(resp!=expected){std::cerr<<"WRITE "<<std::hex<<addr<<" value "<<value<<" resp "<<resp<<std::dec<<std::endl;throw std::runtime_error("AXI write rejected");}
        d.s_axi_bready=1;tick();d.s_axi_bready=0;
    };
    auto rd=[&](unsigned addr,unsigned expected=0){
        unsigned id=reads++;d.s_axi_araddr=addr;d.s_axi_arvalid=1;
        for(unsigned n=0;;++n){
            if(n>100)throw std::runtime_error("AXI AR timeout");
            d.aclk=0;d.eval();bool fire=d.s_axi_arready;tick();if(fire)break;
        }
        d.s_axi_arvalid=0;
        for(unsigned n=0;!d.s_axi_rvalid;++n){if(n>100)throw std::runtime_error("AXI R timeout");tick();}
        uint32_t data=d.s_axi_rdata;unsigned resp=d.s_axi_rresp;
        for(unsigned n=0;n<id%3;++n){tick();if(!d.s_axi_rvalid||d.s_axi_rresp!=resp||d.s_axi_rdata!=data)throw std::runtime_error("R changed under stall");}
        if(resp!=expected)throw std::runtime_error("AXI read rejected");
        d.s_axi_rready=1;tick();d.s_axi_rready=0;return data;
    };
    auto ready=[&](unsigned bit){for(unsigned n=0;;++n){auto s=rd(8);if((s&(1u<<bit)) && !(s&128))return;if(n>40000)throw std::runtime_error("core ready timeout");}};
    auto command=[&](unsigned cmd,unsigned bit=0){ready(bit);wr(4,cmd);};
    auto done=[&](){for(unsigned n=0;;++n){auto s=rd(8);if(s&16)return s;if(n>40000)throw std::runtime_error("kernel timeout");}};
    if(rd(0)!=0x41434731)throw std::runtime_error("ID");
    wr(0x14,0x12345678);wr(0x14,0xaabbccdd,5);if(rd(0x14)!=0x12bb56dd)throw std::runtime_error("WSTRB");
    wr(0xfff,0,15,2);rd(0xfff,2);wr(4,3,15,2);
    command(2);if(!(done()&32))throw std::runtime_error("unconfigured start did not report error");
    wr(4,128);for(int i=0;i<12;++i)tick();
    std::ifstream f(argv[1],std::ios::binary);
    auto word=[&](){uint32_t x;f.read(reinterpret_cast<char*>(&x),4);if(!f)throw std::runtime_error("short fixture");return x;};
    if(word()!=0x43474233)throw std::runtime_error("fixture magic");
    unsigned count=word();std::ofstream result;
    if(argc==3){result.open(argv[2],std::ios::binary);uint32_t h[]={0x4f554732,count};result.write(reinterpret_cast<char*>(h),8);}
    uint64_t errors=0;
    for(unsigned c=0;c<count;++c){
        unsigned fft=word(),fmt=word(),ln=word(),hm=word(),inv=word(),q=word(),qi=word();
        unsigned native=word(),packed=word(),jl=word(),stages=word(),nr=word(),nw=word();uint64_t beginning=ticks;
        ready(0);
        wr(0x10,fft|(inv<<1)|(native<<2)|(packed<<3)|(jl<<4)|(fmt<<7)|(hm<<9)|(ln<<11));
        wr(0x14,q);wr(0x18,qi);command(1);ready(0);if(rd(8)&32)throw std::runtime_error("valid configuration rejected");
        for(unsigned s=0;s<stages;++s){
            ready(0);wr(0x20,s);wr(0x24,word());wr(0x28,word());wr(0x2c,word());wr(0x30,word());command(16);
        }
        std::vector<std::vector<uint32_t>> roots(16,std::vector<uint32_t>(nr));for(auto&lane:roots)for(auto&v:lane)v=word();
        unsigned root_writes=0;
        for(unsigned a=0;a<nr;++a){
            std::map<uint32_t,uint16_t> groups;for(unsigned t=0;t<16;++t)groups[roots[t][a]]|=1u<<t;
            for(auto item:groups){ready(0);wr(0x34,item.second);wr(0x38,a);wr(0x3c,item.first);command(4);++root_writes;}
        }
        command(8);
        std::vector<uint32_t> input(nw),expected(nw),actual(nw);for(auto&v:input)v=word();for(auto&v:expected)v=word();
        for(unsigned l=0;l<(nw+3)/4;++l){
            ready(1);wr(0x40,l);for(unsigned j=0;j<4;++j)wr(0x50+4*j,4*l+j<nw?input[4*l+j]:0);command(32,1);
        }
        command(2);if(done()&32)throw std::runtime_error("kernel error");unsigned cycles=rd(0xc),errs=0;
        for(unsigned l=0;l<(nw+3)/4;++l){
            ready(2);wr(0x40,l);command(64,2);
            for(unsigned n=0;;++n){if(rd(8)&64)break;if(n>100)throw std::runtime_error("line response timeout");}
            for(unsigned j=0;j<4 && 4*l+j<nw;++j){
                auto v=rd(0x60+4*j);actual[4*l+j]=v;
                if(v!=expected[4*l+j]){if(errs<4)std::cout<<"MISMATCH case="<<c<<" word="<<4*l+j<<" got="<<std::hex<<v<<" expected="<<expected[4*l+j]<<std::dec<<std::endl;++errs;}
            }
        }
        if(result){result.write(reinterpret_cast<char*>(&nw),4);result.write(reinterpret_cast<char*>(actual.data()),4*nw);}
        errors+=errs;
        std::cout<<"CASE "<<c<<" packed="<<packed<<" jobs="<<(1u<<jl)<<" native="<<native<<" fft="<<fft<<" fmt="<<fmt<<" logn="<<ln<<" hmin="<<hm<<" inverse="<<inv<<" words="<<nw<<" q="<<q<<" errors="<<errs<<" cycles="<<cycles<<" root_writes="<<root_writes<<" all_host_cycles="<<ticks-beginning<<std::endl;
        if(errs)break;
    }
    std::cout<<"AXI_PROTOCOL decoupled_aw_w=1 b_stall=1 r_stall=1 wstrb=1 invalid_access=1 PASS"<<std::endl;
    std::cout<<"TOTAL cases="<<count<<" errors="<<errors<<(errors?" FAIL":" PASS")<<std::endl;
    d.final();return errors?1:0;
}
