// Random equivalence of the parallel-correction add/sub with the previous one, inside the contract of each mode.
module tb_addsub;
    reg [31:0] a, b, q; reg ci, bi, split, plain;
    wire [31:0] s0, d0, s1, d1; wire co0, bo0, co1, bo1;
    tl_addsub     u_new (.a(a), .b(b), .q(q), .ci(ci), .bi(bi), .split(split), .plain(plain), .s(s1), .d(d1), .co(co1), .bo(bo1));
    tl_addsub_ref u_ref (.a(a), .b(b), .q(q), .ci(ci), .bi(bi), .split(split), .plain(plain), .s(s0), .d(d0), .co(co0), .bo(bo0));
    integer i, m, err, n;
    reg [15:0] ql, qh;
    function [31:0] below(input [31:0] lim); below = ({$random} % lim); endfunction
    initial begin
        err = 0; n = 0;
        for (m = 0; m < 3; m = m + 1)
            for (i = 0; i < 400000; i = i + 1) begin
                ci = 0; bi = 0; split = 0; plain = 0;
                case (m)
                0: begin                                    // modular, one 32-bit lane, odd q < 2^31
                    q = (i % 4 == 0) ? (32'h7fffffff - 2 * ({$random} % 64)) : (i % 4 == 1) ? (3 + 2 * ({$random} % 8)) : ({$random} & 32'h7fffffff) | 32'd1;
                    if (q < 3) q = 3;
                    a = (i % 7 == 0) ? q - 1 : (i % 7 == 1) ? 0 : below(q);
                    b = (i % 5 == 0) ? q - 1 : (i % 5 == 1) ? 0 : below(q);
                end
                1: begin                                    // packed: two lanes, odd q < 2^15, values below q
                    split = 1;
                    ql = (i % 3 == 0) ? 16'h7fff - 2 * ({$random} % 8) : (({$random} & 16'h7fff) | 16'd1); if (ql < 3) ql = 3;
                    qh = (i % 3 == 1) ? 16'h7fff - 2 * ({$random} % 8) : (({$random} & 16'h7fff) | 16'd1); if (qh < 3) qh = 3;
                    q = {qh, ql};
                    a[31:16] = below(qh); a[15:0] = below(ql);
                    b[31:16] = below(qh); b[15:0] = below(ql);
                    if (i % 11 == 0) a = {qh - 16'd1, ql - 16'd1};
                    if (i % 13 == 0) b = {qh - 16'd1, ql - 16'd1};
                end
                default: begin                              // plain (FFT): any values, limb carries
                    plain = 1; a = $random; b = $random; q = $random; ci = $random; bi = $random;
                    if (i % 9 == 0) a = 32'hffffffff; if (i % 10 == 0) b = 32'hffffffff;
                end
                endcase
                #1;
                n = n + 1;
                if (s0 !== s1 || d0 !== d1 || co0 !== co1 || bo0 !== bo1) begin
                    err = err + 1;
                    if (err < 10) $display("MISMATCH mode=%0d a=%h b=%h q=%h ci=%b bi=%b s %h/%h d %h/%h co %b/%b bo %b/%b",
                                           m, a, b, q, ci, bi, s0, s1, d0, d1, co0, co1, bo0, bo1);
                end
            end
        $display("ADDSUB_EQ cases=%0d errors=%0d %s", n, err, err ? "FAIL" : "PASS");
        $finish;
    end
endmodule
