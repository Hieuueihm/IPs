// Standalone forms of the tile's 32-bit modular add/sub (s = a + b mod q, d = a - b mod q), for an area comparison
// (synth_addsub.tcl in this folder; result: as_cur 196 LUT, as_ser 198 LUT, as_tm 290 LUT + 130 FF). Same ports; ci / bi limb carries of mode 5, split = two 16-bit lanes (mode 6).

// Current: four chains (a + b, a + b - q, a - b, a - b + q) and two selects.
module as_cur (input [31:0] a, b, q, input ci, bi, split, output [31:0] s, d, output co, bo);
    wire [32:0] sum = {1'b0, a} + {1'b0, b} + {32'd0, ci};
    wire [16:0] sql = {1'b0, sum[15:0]} - {1'b0, q[15:0]};
    wire [17:0] sqh = {1'b0, sum[32:16]} - {2'b0, q[31:16]} - {17'd0, !split && sql[16]};
    wire [16:0] dfl = {1'b0, a[15:0]} - {1'b0, b[15:0]} - {16'd0, bi};
    wire [16:0] dfh = {1'b0, a[31:16]} - {1'b0, b[31:16]} - {16'd0, !split && dfl[16]};
    wire [16:0] dql = {1'b0, dfl[15:0]} + {1'b0, q[15:0]};
    wire [15:0] dqh = dfh[15:0] + q[31:16] + {15'd0, !split && dql[16]};
    wire        sl  = split ? sql[16] : sqh[17];
    wire        dl  = split ? dfl[16] : dfh[16];
    assign s = {sqh[17] ? sum[31:16] : sqh[15:0], sl ? sum[15:0] : sql[15:0]};
    assign d = {dfh[16] ? dqh : dfh[15:0], dl ? dql[15:0] : dfl[15:0]};
    assign co = sum[32];
    assign bo = dfh[16];
endmodule

// Serial correction: a + b, then a comparator (sum >= q), then one chain subtracts q or 0; a - b, then one chain adds
// q or 0 by the sign. No result select; deeper (three chains in series), which 5 ns allows.
module as_ser (input [31:0] a, b, q, input ci, bi, split, output [31:0] s, d, output co, bo);
    wire [32:0] sum = {1'b0, a} + {1'b0, b} + {32'd0, ci};
    wire        gel = sum[15:0] >= q[15:0];
    wire        geh = split ? (sum[32:16] >= {1'b0, q[31:16]}) : (sum >= {1'b0, q});
    wire [15:0] cql = (split ? gel : geh) ? q[15:0] : 16'd0;
    wire [15:0] cqh = geh ? q[31:16] : 16'd0;
    wire [16:0] sl  = {1'b0, sum[15:0]} - {1'b0, cql};
    wire [15:0] sh  = sum[31:16] - cqh - {15'd0, !split && sl[16]};
    wire [16:0] dfl = {1'b0, a[15:0]} - {1'b0, b[15:0]} - {16'd0, bi};
    wire [16:0] dfh = {1'b0, a[31:16]} - {1'b0, b[31:16]} - {16'd0, !split && dfl[16]};
    wire [15:0] aql = (split ? dfl[16] : dfh[16]) ? q[15:0] : 16'd0;
    wire [15:0] aqh = dfh[16] ? q[31:16] : 16'd0;
    wire [16:0] dl  = {1'b0, dfl[15:0]} + {1'b0, aql};
    wire [15:0] dh  = dfh[15:0] + aqh + {15'd0, !split && dl[16]};
    assign s = {sh, sl[15:0]};
    assign d = {dh, dl[15:0]};
    assign co = sum[32];
    assign bo = dfh[16];
endmodule

// Time-shared: two chains. Cycle 1: a + b, a - b (registered); cycle 2 (op = 1): the same chains compute sum - q and
// df + q from the registers; outputs registered after the select. Valid for one operation every two cycles or slower.
module as_tm (input clk, input op, input [31:0] a, b, q, input ci, bi, split, output reg [31:0] s, d, output co, bo);
    reg  [32:0] rs;
    reg  [32:0] rd;
    wire [31:0] xa = op ? rs[31:0] : a;
    wire [31:0] xb = op ? ~q : b;
    wire [32:0] c1 = {1'b0, xa} + {1'b0, xb} + {32'd0, op ? 1'b1 : ci};
    wire [31:0] ya = op ? rd[31:0] : a;
    wire [31:0] yb = op ? q : ~b;
    wire [32:0] c2 = {1'b0, ya} + {1'b0, yb} + {32'd0, op ? 1'b0 : !bi};
    always @(posedge clk) begin
        if (!op) begin rs <= c1; rd <= {~c2[32], c2[31:0]}; end
        else begin
            s <= (rs[32] || c1[32]) ? c1[31:0] : rs[31:0];
            d <= rd[32] ? c2[31:0] : rd[31:0];
        end
    end
    assign co = c1[32];
    assign bo = ~c2[32];
endmodule
