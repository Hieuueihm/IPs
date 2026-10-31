// Measurement wrapper of ntt_bank_net: every input registered, as the RAM outputs and the controller's
// selects are registers in the core. The network's outputs are already registered.
module ntt_bank_net_top #(parameter integer TILES = 16, BANKS = 64, PBANKS = 8) (
    input  wire                     clk, en_i, lane32_i,
    input  wire [BANKS*16-1:0]      bank_rd_i,
    input  wire [PBANKS*96-1:0]     pack_rd_i,
    input  wire [TILES*6-1:0]       sel_x_i, sel_y_i,
    input  wire [TILES-1:0]         hold_x_i,
    input  wire [TILES*3-1:0]       sel_pb_i,
    input  wire [TILES*2-1:0]       sel_child_i,
    input  wire [TILES*64-1:0]      tile_z_i,
    input  wire [BANKS*5-1:0]       wsel_i,
    input  wire [BANKS-1:0]         wen_i,
    output wire [TILES*32-1:0]      op_x, op_y, op_w,
    output wire [BANKS*16-1:0]      bank_wd,
    output wire [BANKS-1:0]         bank_we
);
    reg                 en, lane32;
    reg [BANKS*16-1:0]  bank_rd;
    reg [PBANKS*96-1:0] pack_rd;
    reg [TILES*6-1:0]   sel_x, sel_y;
    reg [TILES-1:0]     hold_x;
    reg [TILES*3-1:0]   sel_pb;
    reg [TILES*2-1:0]   sel_child;
    reg [TILES*64-1:0]  tile_z;
    reg [BANKS*5-1:0]   wsel;
    reg [BANKS-1:0]     wen;
    always @(posedge clk) begin
        en <= en_i; lane32 <= lane32_i; bank_rd <= bank_rd_i; pack_rd <= pack_rd_i;
        sel_x <= sel_x_i; sel_y <= sel_y_i; hold_x <= hold_x_i; sel_pb <= sel_pb_i; sel_child <= sel_child_i;
        tile_z <= tile_z_i; wsel <= wsel_i; wen <= wen_i;
    end
    ntt_bank_net #(.TILES(TILES), .BANKS(BANKS), .PBANKS(PBANKS)) u_net (
        .clk(clk), .en(en), .lane32(lane32), .bank_rd(bank_rd), .pack_rd(pack_rd),
        .sel_x(sel_x), .sel_y(sel_y), .hold_x(hold_x), .sel_pb(sel_pb), .sel_child(sel_child),
        .op_x(op_x), .op_y(op_y), .op_w(op_w), .tile_z(tile_z), .wsel(wsel), .wen(wen),
        .bank_wd(bank_wd), .bank_we(bank_we));
endmodule
