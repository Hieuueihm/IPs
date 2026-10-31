// Autonomous functional kernel controller around the validated shared array.
// op: FFT=0 IFFT=1 CMUL=2 SPLIT=3 MERGE=4 NTT=5 INTT=6 TOMONT=7 MODMUL=8.
// Host writes A/B, starts once, then reads A (or C for SPLIT/MERGE) at DONE.
// SPLIT flattens f0||f1. FFT real/imag arrays use the exact R8 split layout.
// This baseline serializes complex butterflies; it does not claim peak FFT32/64 utilization.
module flex_kernel_engine(
    input clk,rst,pause,
    input [3:0] cfg_op,cfg_logn,input [1:0] cfg_width,input cfg_profile,
    input start_valid,output start_ready,
    input load_valid,output load_ready,input load_bank,
    input [9:0] load_address,input [127:0] load_data,
    input read_valid,output read_ready,input [9:0] read_address,
    output reg read_response_valid,output reg [127:0] read_data,
    output done_valid,input done_ready,output reg error,
    output reg [31:0] cycles
);
    localparam IDLE=0,FREAD=1,FWAIT=2,PREP=3,ISSUE=4,WAITP=5,
        COMBINE=6,FWRITE=7,ADVANCE=8,NREAD=9,NWAIT=10,NISSUE=11,
        NRESULT=12,NWRITE=13,NADVANCE=14,SREAD=15,SWAIT=16,SWRITE=17,
        COPYREAD=18,COPYWAIT=19,COPYWRITE=20,DONE=21;
    reg [4:0] state;
    reg [3:0] op,logn;reg [1:0] width;reg profile;
    reg [10:0] n,hn,qn,span,groups,group_no,offset,item;
    reg [2:0] fetch,issue,write_no;reg [3:0] levels,p;
    reg [4:0] warp;
    reg scalar;
    reg [15:0] factor;
    wire inverse=op==1||op==3||op==6;
    wire paired=levels>=2;
    wire [1:0] mode=scalar?0:(paired?1:2);
    wire active=!pause;
    assign start_ready=state==IDLE&&active;
    assign load_ready=state==IDLE&&!start_valid&&active;
    assign read_ready=state==DONE&&active;
    assign done_valid=state==DONE;
    wire is_ntt=(state==IDLE?cfg_op:op)>=5;
    wire [1:0] mem_width=state==IDLE?cfg_width:width;
    wire [2:0] limb_shift=is_ntt?0:mem_width==0?1:mem_width==1?2:3;
    reg [63:0] re[0:2],we[0:2];
    reg [447:0] ra[0:2],wa[0:2];
    reg [1023:0] wd[0:2];wire [1023:0] rd[0:2];
    genvar m;
    generate for(m=0;m<3;m=m+1)begin:store
        flex_banked_scratch ram(.clk(clk),.re(re[m]),.we(we[m]),.ra(ra[m]),.wa(wa[m]),.wd(wd[m]),.rd(rd[m]));
    end endgenerate
    function automatic integer bank(input integer x);
        bank=(x&63)^((x>>2)&48)^((x>>4)&48);
    endfunction
    function automatic integer column(input integer b);
        column=b<6?b:4+((b-4)&1);
    endfunction
    function automatic [127:0] norm(input [127:0] x);
        case(width)
        0:norm={{96{x[31]}},x[31:0]};
        1:norm={{64{x[63]}},x[63:0]};
        default:norm=x;
        endcase
    endfunction
    function automatic [127:0] add(input [127:0] a,b);add=norm(a+b);endfunction
    function automatic [127:0] sub(input [127:0] a,b);sub=norm(a-b);endfunction
    function automatic [127:0] div2e(input [127:0] x,input integer shift);
        reg signed [127:0] t;
        begin t=norm(x+((128'b1<<shift)>>1));div2e=norm(t>>>shift);end
    endfunction
    function automatic [127:0] root_quant(input [127:0] x);
        reg signed [127:0] t;
        begin
            if(width==0)begin t=x+128'h800000000000;root_quant=norm(t>>>48);end
            else if(width==1)begin t=x+128'h80000000;root_quant=norm(t>>>32);end
            else root_quant=x;
        end
    endfunction
    task automatic read_word(input integer store_id,index);
        integer l,a,b;
        begin for(l=0;l<8;l=l+1)if(l<(1<<limb_shift))begin
            a=(index<<limb_shift)+l;b=bank(a);re[store_id][b]=1;ra[store_id][b*7+:7]=a>>6;
        end end
    endtask
    task automatic write_word(input integer store_id,index,input [127:0] value);
        integer l,a,b;
        begin for(l=0;l<8;l=l+1)if(l<(1<<limb_shift))begin
            a=(index<<limb_shift)+l;b=bank(a);we[store_id][b]=1;
            wa[store_id][b*7+:7]=a>>6;wd[store_id][b*16+:16]=value[l*16+:16];
        end end
    endtask
    function automatic [127:0] get_word(input integer store_id,index);
        integer l,a;reg [127:0] value;
        begin value=0;for(l=0;l<8;l=l+1)if(l<(1<<limb_shift))begin
            a=(index<<limb_shift)+l;value[l*16+:16]=rd[store_id][bank(a)*16+:16];
        end get_word=is_ntt?value:norm(value);end
    endfunction
    // Combinational address expansion; loop bounds are compile-time constants.
    function automatic integer position(input integer lane);
        integer g,k,base,b,bit_no,seen,front,free_mask,upper,selected;
        begin
            k=lane&3;g=(warp<<4)+(lane>>2);base=0;bit_no=0;
            if(paired)begin
                for(b=0;b<10;b=b+1)if(b<logn&&b!=p&&b!=p+1)begin
                    base=base|(((g>>bit_no)&1)<<b);bit_no=bit_no+1;
                end
                position=base+(k<<p);
            end else begin
                g=(warp<<5)+((lane>>2)<<1)+(inverse?(k>>1):(k&1));
                upper=inverse?(k&1):(k>>1);seen=1<<column(p);free_mask=0;
                for(b=0;b<10;b=b+1)if(b<logn&&b!=p)begin
                    selected=column(b);
                    if((seen&(1<<selected))==0)begin
                        base=base|(((g>>bit_no)&1)<<b);bit_no=bit_no+1;
                        seen=seen|(1<<selected);free_mask=free_mask|(1<<b);
                    end
                end
                for(b=0;b<10;b=b+1)if(b<logn&&b!=p&&(free_mask&(1<<b))==0)begin
                    base=base|(((g>>bit_no)&1)<<b);bit_no=bit_no+1;
                end
                position=base+(upper<<p);
            end
        end
    endfunction
    function automatic [15:0] root_from_bundle(input integer g,input [47:0] bundle);
        root_from_bundle=g==1?bundle[15:0]:g[0]?bundle[47:32]:bundle[31:16];
    endfunction
    function automatic [15:0] normalization(input integer count,input bit small_q);
        integer v,q,j;
        begin q=small_q?3329:12289;v=small_q?2285:4091;
            for(j=0;j<10;j=j+1)if(j<count)v=(v+((v&1)?q:0))>>1;
            normalization=v;
        end
    endfunction
    reg [127:0] ar,ai,br,bi,keep_re,keep_im,mr,mi,rr,ri;
    reg [127:0] p0,p1,p2,tr,ti,scale_data;
    wire [127:0] rom_re,rom_im;
    reg fft_en;reg [9:0] fft_addr;
    reg [15:0] root_en;reg [79:0] root_addr;wire [767:0] root_data;
    flex_kernel_rom roots(.clk(clk),.fft_en(fft_en),.fft_addr(fft_addr),.fft_re(rom_re),.fft_im(rom_im),
        .ntt_en(root_en),.ntt_addr(root_addr),.profile(profile),.inverse(op==6),.ntt_data(root_data));
    reg [2047:0] array_data,saved_result;reg [1023:0] array_roots;
    reg [31:0] array_tag;reg array_valid,array_ntt,array_inverse,array_ready;
    wire array_in_ready,array_out_valid;wire [2047:0] array_result;wire [31:0] result_tag;
    flex_stream_banked arithmetic(.clk(clk),.rst(rst),.in_valid(array_valid),.ntt(array_ntt),
        .width(width),.ntt_mode(mode),.profile(profile),.inverse(array_inverse),.tag(array_tag),
        .data(array_data),.twiddle(array_roots),.in_ready(array_in_ready),.out_ready(array_ready),
        .out_valid(array_out_valid),.out_ntt(),.out_width(),.out_ntt_mode(),.out_profile(),
        .out_inverse(),.out_tag(result_tag),.result(array_result),.bank_write_mask());
    reg [2047:0] ntt_input;reg [1023:0] ntt_roots;
    reg [31:0] ntt_tag;
    integer src_store,src_index,dst_store,dst_index,root_index,idx,b,t,g,parent,g1;
    integer j,ii,word_index;reg [127:0] dst_value;
    reg [47:0] bundle;
    always @*begin
        src_store=0;src_index=0;dst_store=(op==3||op==4)?2:0;dst_index=0;dst_value=0;
        root_index=0;
        if(op==0||op==1)begin
            src_index=group_no*span+offset;
            if(fetch[1])src_index=src_index+(op==0?span>>1:span>>1);
            if(fetch[0])src_index=src_index+hn;
            root_index=groups+group_no;
        end else if(op==2)begin
            src_store=fetch[1]?1:0;src_index=item+(fetch[0]?hn:0);
        end else if(op==3)begin
            src_index=(item<<1)+(fetch[1]?1:0)+(fetch[0]?hn:0);root_index=item+hn;
        end else if(op==4)begin
            src_store=fetch[1]?1:0;src_index=item+(fetch[0]?qn:0);root_index=item+hn;
        end
        case(op)
        0,1:begin
            dst_index=group_no*span+offset+(write_no[1]?(span>>1):0)+(write_no[0]?hn:0);
            if(op==0)dst_value=write_no[1]?(write_no[0]?sub(keep_im,ti):sub(keep_re,tr)):
                                                 (write_no[0]?add(keep_im,ti):add(keep_re,tr));
            else dst_value=write_no[1]?(write_no[0]?ti:tr):(write_no[0]?keep_im:keep_re);
        end
        2:begin dst_index=item+(write_no[0]?hn:0);dst_value=write_no[0]?ti:tr;end
        3:begin
            dst_index=item+(write_no[1]?hn:0)+(write_no[0]?qn:0);
            dst_value=write_no[1]?div2e(write_no[0]?ti:tr,1):(write_no[0]?keep_im:keep_re);
        end
        4:begin
            dst_index=(item<<1)+(write_no[1]?1:0)+(write_no[0]?hn:0);
            dst_value=write_no[1]?(write_no[0]?sub(keep_im,ti):sub(keep_re,tr)):
                                      (write_no[0]?add(keep_im,ti):add(keep_re,tr));
        end
        endcase
        for(j=0;j<3;j=j+1)begin re[j]=0;we[j]=0;ra[j]=0;wa[j]=0;wd[j]=0;end
        fft_en=0;fft_addr=root_index;root_en=0;root_addr=0;
        array_valid=0;array_ntt=0;array_inverse=0;array_data=0;array_roots=0;array_tag=0;array_ready=0;
        if(active)begin
            if(load_valid&&load_ready)write_word(load_bank?1:0,load_address,load_data);
            if(read_valid&&read_ready)read_word((op==3||op==4)?2:0,read_address);
            case(state)
            FREAD:begin read_word(src_store,src_index);fft_en=fetch==0&&op!=2;end
            ISSUE:begin
                array_valid=1;array_tag=issue;
                array_data[127:0]=issue==0?mr:issue==1?mi:add(mr,mi);
                array_data[639:512]=issue==0?rr:issue==1?ri:add(rr,ri);
                // Narrow modes pack only one active lane, not sign-extension into other lanes.
                if(width==0)begin array_data[511:32]=0;array_data[1023:544]=0;end
                if(width==1)begin array_data[511:64]=0;array_data[1023:576]=0;end
            end
            WAITP:array_ready=1;
            FWRITE:write_word(dst_store,dst_index,dst_value);
            SREAD:read_word(0,item);
            SWRITE:write_word(0,item,div2e(scale_data,logn-1));
            COPYREAD:read_word(op==4?item:0,op==4?0:item);
            COPYWRITE:write_word(2,item,scale_data);
            NREAD:begin
                for(ii=0;ii<64;ii=ii+1)if(ii<n)begin
                    idx=scalar?(warp*64+ii):position(ii);b=bank(idx);
                    re[0][b]=1;ra[0][b*7+:7]=idx>>6;
                    if(scalar&&op==8)begin re[1][b]=1;ra[1][b*7+:7]=idx>>6;end
                end
                if(!scalar)for(t=0;t<16;t=t+1)if(t*4<n)begin
                    idx=position(t*4);g=(n>>(p+(paired?2:1)))+(idx>>(p+(paired?2:1)));
                    parent=paired?g:(g==1?1:g>>1);
                    root_en[parent&15]=1;root_addr[(parent&15)*5+:5]=parent>>4;
                end
            end
            NISSUE:begin
                array_valid=1;array_ntt=1;array_inverse=!scalar&&op==6;
                array_data=ntt_input;array_roots=ntt_roots;array_tag=ntt_tag;
            end
            NRESULT:array_ready=1;
            NWRITE:for(ii=0;ii<64;ii=ii+1)if(ii<n)begin
                idx=scalar?(warp*64+ii):position(ii);b=bank(idx);
                we[0][b]=1;wa[0][b*7+:7]=idx>>6;
                wd[0][b*16+:16]=scalar?saved_result[ii*32+:16]:saved_result[b*16+:16];
            end
            endcase
        end
    end
    reg read_pending;
    reg [9:0] read_index;
    always @(posedge clk)begin:sequential
        integer ii,b,word_index,t,idx,g,parent,g1;
        reg [47:0] bundle;
        if(rst)begin
            state<=IDLE;error<=0;read_pending<=0;read_response_valid<=0;cycles<=0;
            op<=0;logn<=0;width<=2;profile<=0;
            fetch<=0;issue<=0;write_no<=0;item<=0;warp<=0;scalar<=0;
            span<=0;groups<=0;group_no<=0;offset<=0;n<=0;hn<=0;qn<=0;levels<=0;p<=0;
        end else begin
            read_response_valid<=read_pending;
            read_pending<=read_valid&&read_ready;
            if(read_valid&&read_ready)read_index<=read_address;
            if(read_pending)read_data<=get_word((op==3||op==4)?2:0,read_index);
            if(state!=IDLE&&state!=DONE)cycles<=cycles+1;
            if(active)case(state)
            IDLE:if(start_valid)begin
                op<=cfg_op;logn<=cfg_logn;width<=cfg_width;profile<=cfg_profile;
                n<=11'b1<<cfg_logn;hn<=(11'b1<<cfg_logn)>>1;qn<=(11'b1<<cfg_logn)>>2;
                error<=0;cycles<=0;fetch<=0;issue<=0;write_no<=0;group_no<=0;offset<=0;item<=0;warp<=0;
                levels<=(cfg_profile&&cfg_logn==8)?7:cfg_logn;
                scalar<=cfg_op==7||cfg_op==8;
                if(cfg_op>8||cfg_logn>10||cfg_width>2||
                   ((cfg_op>=2&&cfg_op<=4)&&cfg_logn==0)||
                   (cfg_op>=5&&(cfg_logn<3||(cfg_profile&&cfg_logn>8))))begin error<=1;state<=DONE;end
                else if(cfg_op>=5)begin
                    factor<=cfg_profile?1353:10952;
                    p<=cfg_op==6?((cfg_profile&&cfg_logn==8)?1:0):cfg_logn-2;
                    state<=NREAD;
                end else if(cfg_logn<2&&(cfg_op==0||cfg_op==1))state<=DONE;
                else if(cfg_logn==1&&(cfg_op==3||cfg_op==4))state<=COPYREAD;
                else begin
                    span<=cfg_op==1?2:((11'b1<<cfg_logn)>>1);
                    groups<=cfg_op==1?((11'b1<<cfg_logn)>>1):2;
                    state<=FREAD;
                end
            end
            FREAD:state<=FWAIT;
            FWAIT:begin
                case(fetch)
                0:ar<=get_word(src_store,src_index);
                1:ai<=get_word(src_store,src_index);
                2:br<=get_word(src_store,src_index);
                3:bi<=get_word(src_store,src_index);
                endcase
                if(fetch==3)begin fetch<=0;state<=PREP;end else begin fetch<=fetch+1;state<=FREAD;end
            end
            PREP:begin
                keep_re<=ar;keep_im<=ai;
                rr<=root_quant(rom_re);ri<=root_quant(inverse?-rom_im:rom_im);
                if(op==1||op==3)begin
                    mr<=sub(ar,br);mi<=sub(ai,bi);
                    keep_re<=op==3?div2e(add(ar,br),1):add(ar,br);
                    keep_im<=op==3?div2e(add(ai,bi),1):add(ai,bi);
                end else if(op==2)begin mr<=ar;mi<=ai;rr<=br;ri<=bi;end
                else begin mr<=br;mi<=bi;end
                issue<=0;state<=ISSUE;
            end
            ISSUE:if(array_in_ready)begin
                if(issue==2)state<=WAITP;else issue<=issue+1;
            end
            WAITP:if(array_out_valid)begin
                case(result_tag[1:0])
                0:p0<=norm(array_result[127:0]);
                1:p1<=norm(array_result[127:0]);
                2:begin p2<=norm(array_result[127:0]);state<=COMBINE;end
                endcase
            end
            COMBINE:begin tr<=sub(p0,p1);ti<=sub(sub(p2,p0),p1);write_no<=0;state<=FWRITE;end
            FWRITE:if(write_no==(op==2?1:3))state<=ADVANCE;else write_no<=write_no+1;
            ADVANCE:begin
                state<=FREAD;fetch<=0;
                if(op==0||op==1)begin
                    if(offset+1<(span>>1))offset<=offset+1;
                    else begin
                        offset<=0;
                        if(group_no+1<(groups>>1))group_no<=group_no+1;
                        else begin
                            group_no<=0;
                            if((op==0&&span==2)||(op==1&&span==hn))begin
                                item<=0;state<=op==1?SREAD:DONE;
                            end else begin
                                span<=op==0?span>>1:span<<1;groups<=op==0?groups<<1:groups>>1;
                            end
                        end
                    end
                end else if(item+1<(op==2?hn:qn))item<=item+1;
                else state<=DONE;
            end
            SREAD:state<=SWAIT;
            SWAIT:begin scale_data<=get_word(0,item);state<=SWRITE;end
            SWRITE:if(item+1<n)begin item<=item+1;state<=SREAD;end else state<=DONE;
            COPYREAD:state<=COPYWAIT;
            COPYWAIT:begin scale_data<=get_word(op==4?item:0,op==4?0:item);state<=COPYWRITE;end
            COPYWRITE:if(item==0)begin item<=1;state<=COPYREAD;end else state<=DONE;
            NREAD:state<=NWAIT;
            NWAIT:begin
                ntt_input<=0;ntt_roots<=0;ntt_tag<=0;
                if(scalar)begin
                    for(ii=0;ii<64;ii=ii+1)if(ii<n)begin
                        word_index=warp*64+ii;b=bank(word_index);
                        ntt_input[ii*32+16+:16]<=rd[0][b*16+:16];
                        ntt_roots[ii*16+:16]<=op==8?rd[1][b*16+:16]:factor;
                    end
                end else begin
                    ntt_input[1023:0]<=rd[0];
                    ntt_tag<=(p<<28)|((bank(position(0))>>4)<<26)|(logn<<22);
                    for(t=0;t<16;t=t+1)if(t*4<n)begin
                        idx=position(t*4);g=(n>>(p+(paired?2:1)))+(idx>>(p+(paired?2:1)));
                        parent=paired?g:(g==1?1:g>>1);bundle=root_data[(parent&15)*48+:48];
                        if(paired)ntt_roots[t*48+:48]<=bundle;
                        else begin
                            g1=(n>>(p+1))+(position(t*4+(inverse?2:1))>>(p+1));
                            ntt_roots[t*32+:16]<=root_from_bundle(g,bundle);
                            ntt_roots[t*32+16+:16]<=root_from_bundle(g1,bundle);
                        end
                    end
                end
                state<=NISSUE;
            end
            NISSUE:if(array_in_ready)state<=NRESULT;
            NRESULT:if(array_out_valid)begin saved_result<=array_result;state<=NWRITE;end
            NWRITE:state<=NADVANCE;
            NADVANCE:begin
                if((warp+1)*64<n)begin warp<=warp+1;state<=NREAD;end
                else begin
                    warp<=0;
                    if(scalar)state<=DONE;
                    else if(levels<3)begin
                        if(op==6)begin scalar<=1;factor<=normalization((profile&&logn==8)?7:logn,profile);state<=NREAD;end
                        else state<=DONE;
                    end else begin
                        levels<=levels-2;
                        p<=op==6?p+2:(levels==3?p-1:p-2);
                        state<=NREAD;
                    end
                end
            end
            DONE:if(done_ready&&!read_pending&&!(read_valid&&read_ready))state<=IDLE;
            default:begin error<=1;state<=DONE;end
            endcase
        end
    end
endmodule
