"""Compare the changed adder to the frozen implementation, including carries."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_timing/addsub'

def extract(p):
    s=p.read_text();a=s.index('module tl_addsub #(')
    return s[a:s.index('endmodule',a)+len('endmodule')]

def main():
    B.mkdir(exist_ok=True)
    old=extract(ROOT/'experiments/a_cg_batch/rtl/tile_a.sv').replace('module tl_addsub','module reference_addsub',1)
    new=extract(HERE/'raw/rtl/tile_a.sv')
    tb=r'''
module tb;
reg [31:0] a,b,q;
reg ci,bi,split,plain;
wire [31:0] s,d,rs,rd;
wire co,bo,rco,rbo;
integer i,j,k,mode;reg [31:0] edges[0:7];
reg [15:0] ql,qh;
reference_addsub ref_u(.a(a),.b(b),.q(plain?32'd0:q),.ci(ci),.bi(bi),.split(split),.s(rs),.d(rd),.co(rco),.bo(rbo));
tl_addsub dut(.a(a),.b(b),.q(q),.ci(ci),.bi(bi),.split(split),.plain(plain),.s(s),.d(d),.co(co),.bo(bo));
task check;begin
 #1;
 if({s,d,co,bo}!=={rs,rd,rco,rbo})$fatal(1,"adder mismatch a=%h b=%h q=%h plain=%b split=%b ci=%b bi=%b",a,b,q,plain,split,ci,bi);
end endtask
initial begin
 edges[0]=0;edges[1]=1;edges[2]=32'h7fffffff;edges[3]=32'h80000000;
 edges[4]=32'hffffffff;edges[5]=32'hfffffffe;edges[6]=32'h0000ffff;edges[7]=32'hffff0000;
 plain=1;split=0;
 for(i=0;i<8;i=i+1)for(j=0;j<8;j=j+1)for(k=0;k<4;k=k+1)begin
  a=edges[i];b=edges[j];q=$urandom;ci=k&1;bi=(k>>1)&1;check;
 end
 for(i=0;i<100000;i=i+1)begin
  mode=i%3;plain=(mode==0);split=(mode==2);ci=0;bi=0;
  if(mode==0)begin a=$urandom;b=$urandom;q=$urandom;ci=$urandom&1;bi=$urandom&1;end
  else if(mode==1)begin q=($urandom&32'h7ffffffe)|1;if(q<3)q=3;a=$urandom%q;b=$urandom%q;end
  else begin
   ql=($urandom%32765)+3;qh=($urandom%32765)+3;q={qh,ql};
   a={16'($urandom%qh),16'($urandom%ql)};
   b={16'($urandom%qh),16'($urandom%ql)};
  end
  check;
 end
 $display("ADDSUB_EQUIVALENCE cases=100256 PASS");$finish;
end
endmodule
'''
    src=B/'equivalence.sv';src.write_text(old+'\n'+new+'\n'+tb)
    subprocess.run(['C:/iverilog/bin/iverilog.exe','-g2012','-s','tb','-o',str(B/'equivalence.vvp'),str(src)],check=True)
    p=subprocess.run(['C:/iverilog/bin/vvp.exe',str(B/'equivalence.vvp')],check=True,capture_output=True,text=True)
    (B/'result.log').write_text(p.stdout+p.stderr)
    assert 'ADDSUB_EQUIVALENCE cases=100256 PASS' in p.stdout
    print(p.stdout)

if __name__=='__main__':main()
