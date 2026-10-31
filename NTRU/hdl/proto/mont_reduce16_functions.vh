// Include inside a module with integer parameter REDUCE_IMPL.
// T <= (q-1)^2, canonical operands, R=2^16. All implementations return [0,q).
// 0: original expression; 1: CSA for S; 2: exact high(m*q) decomposition.
function automatic [15:0] mont(input [31:0] t,input profile_bit);
    reg [27:0] te;
    reg [15:0] m,q,r;
    reg [29:0] me,mq,s,a,b,c,d,e,ss0,cc0,ss1,cc1,ss2,cc2;
    reg [14:0] u;
    reg [13:0] h0,high0,uc0;
    reg [5:0] l0;
    reg [17:0] low0;
    reg [11:0] h1,l1,high1,uc1;
    reg [19:0] low1;
    begin
        te=profile_bit ? {4'b0,t[23:0]} : t[27:0];
        q=profile_bit ? 16'd3329 : 16'd12289;
        // Common m generator, to isolate the S/high(mq) implementation.
        m=profile_bit ? (te[15:0]<<12)-(te[15:0]<<10)+(te[15:0]<<8)-te[15:0] :
                        (te[15:0]<<14)-(te[15:0]<<12)-te[15:0];
        me={14'b0,m};
        if(REDUCE_IMPL==2) begin
            h0={2'b0,m[15:4]}+({2'b0,m[15:4]}<<1);
            l0={2'b0,m[3:0]}+({2'b0,m[3:0]}<<1);
            low0={l0,12'b0}+{2'b0,m};
            high0=h0+{12'b0,low0[17:16]};
            uc0={2'b0,te[27:16]}+high0+(te[15:0]!=0);
            h1=({4'b0,m[15:8]}<<4)-({4'b0,m[15:8]}<<2)+{4'b0,m[15:8]};
            l1=({4'b0,m[7:0]}<<4)-({4'b0,m[7:0]}<<2)+{4'b0,m[7:0]};
            low1={l1,8'b0}+{4'b0,m};
            high1=h1+{8'b0,low1[19:16]};
            uc1=te[23:16]+high1+(te[15:0]!=0);
            u=profile_bit ? {3'b0,uc1} : {1'b0,uc0};
        end else begin
            if(REDUCE_IMPL==1) begin
                // Complement subtraction. Inject the +1 bias into a shift's
                // known-zero low bit; no additional hidden operand/adder.
                a={2'b0,te};
                b=(profile_bit ? me<<12 : me<<14)|30'd1;
                c=~(profile_bit ? me<<10 : me<<12);
                d=profile_bit ? me<<8 : me;
                e=me;
                ss0=a^b^c; cc0=((a&b)|(a&c)|(b&c))<<1;
                ss1=ss0^cc0^d; cc1=((ss0&cc0)|(ss0&d)|(cc0&d))<<1;
                ss2=ss1^cc1^e; cc2=((ss1&cc1)|(ss1&e)|(cc1&e))<<1;
                s=profile_bit ? ss2+cc2 : ss1+cc1;
            end else begin
                mq=profile_bit ? (me<<12)-(me<<10)+(me<<8)+me :
                                 (me<<14)-(me<<12)+me;
                s={2'b0,te}+mq;
            end
            u={1'b0,s[29:16]};
        end
        r=u>=q ? u-q : u;
        mont=profile_bit ? {4'b0,r[11:0]} : {2'b0,r[13:0]};
    end
endfunction
