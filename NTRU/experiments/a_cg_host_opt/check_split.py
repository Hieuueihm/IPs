"""Bit-exact carry/borrow comparison for both FFT adder implementations."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_host_opt/split_check'

def module(p,name):
    s=p.read_text();a=s.index('module '+name+' #(')
    return s[a:s.index('endmodule',a)+len('endmodule')]

def main():
    B.mkdir(exist_ok=True)
    old=module(ROOT/'experiments/a_cg_host_baseline/rtl/tile_a.sv','tl_addsub').replace('module tl_addsub','module reference_addsub',1)
    p=HERE/'prepare_split/rtl/tile_a.sv'
    shared=module(p,'tl_addsub');post=module(p,'fft_ct_addsub')
    assert shared==module(ROOT/'experiments/a_cg_timing/raw/rtl/tile_a.sv','tl_addsub')
    tb=r'''
module tb;
reg [31:0] a,b,q;reg ci,bi;
wire [31:0] rs,rd,gs,gd,fs,fd;
wire rco,rbo,gco,gbo,fco,fbo;
integer i,j,k;reg [31:0] edges[0:7];
reference_addsub ref_u(.a(a),.b(b),.q(32'd0),.ci(ci),.bi(bi),.split(1'b0),.s(rs),.d(rd),.co(rco),.bo(rbo));
tl_addsub gs_u(.a(a),.b(b),.q(q),.ci(ci),.bi(bi),.split(1'b0),.plain(1'b1),.s(gs),.d(gd),.co(gco),.bo(gbo));
fft_ct_addsub ct_u(.a(a),.b(b),.ci(ci),.bi(bi),.s(fs),.d(fd),.co(fco),.bo(fbo));
task check;begin
 #1;
 if({rs,rd,rco,rbo}!=={gs,gd,gco,gbo} || {rs,rd,rco,rbo}!=={fs,fd,fco,fbo})
  $fatal(1,"FFT raw/split mismatch a=%h b=%h ci=%b bi=%b",a,b,ci,bi);
end endtask
initial begin
 edges[0]=0;edges[1]=1;edges[2]=32'h7fffffff;edges[3]=32'h80000000;
 edges[4]=32'hffffffff;edges[5]=32'hfffffffe;edges[6]=32'h0000ffff;edges[7]=32'hffff0000;
 for(i=0;i<8;i=i+1)for(j=0;j<8;j=j+1)for(k=0;k<4;k=k+1)begin
  a=edges[i];b=edges[j];q=$urandom;ci=k&1;bi=(k>>1)&1;check;
 end
 for(i=0;i<100000;i=i+1)begin a=$urandom;b=$urandom;q=$urandom;ci=$urandom&1;bi=$urandom&1;check;end
 $display("FFT_SPLIT_EQUIVALENCE cases=100256 PASS");$finish;
end
endmodule
'''
    src=B/'check.sv';src.write_text(old+'\n'+shared+'\n'+post+'\n'+tb)
    subprocess.run(['C:/iverilog/bin/iverilog.exe','-g2012','-s','tb','-o',str(B/'check.vvp'),str(src)],check=True)
    out=subprocess.run(['C:/iverilog/bin/vvp.exe',str(B/'check.vvp')],check=True,capture_output=True,text=True)
    (B/'result.log').write_text(out.stdout+out.stderr)
    assert 'FFT_SPLIT_EQUIVALENCE cases=100256 PASS' in out.stdout
    print(out.stdout)

if __name__=='__main__':main()
