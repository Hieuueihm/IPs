// Measurement wrapper of the generated ntt_bank_net_s: every input registered, like ntt_bank_net_top.
module ntt_bank_net_s_top #(parameter integer TILES = 16, BANKS = 64, PBANKS = 8) (
    input  wire                     clk, en_i,
    input  wire [BANKS*16-1:0]      bank_rd_i,
    input  wire [PBANKS*96-1:0]     pack_rd_i,
    input  wire [TILES*3-1:0]       sel_xlo_i, sel_ylo_i,
    input  wire [TILES*3-1:0]       sel_xhi_i, sel_yhi_i,
    input  wire [TILES-1:0]         hold_x_i,
    input  wire [31:0]              root1_i,
    input  wire [TILES*5-1:0]       sel_root_i,
    input  wire [TILES*64-1:0]      tile_z_i,
    input  wire [BANKS*3-1:0]       wsel_i,
    input  wire [BANKS-1:0]         wen_i,
    output wire [TILES*32-1:0]      op_x, op_y, op_w,
    output wire [BANKS*16-1:0]      bank_wd,
    output wire [BANKS-1:0]         bank_we
);
    reg                 en;
    reg [BANKS*16-1:0]  bank_rd;
    reg [PBANKS*96-1:0] pack_rd;
    reg [TILES*3-1:0]   sel_xlo, sel_ylo;
    reg [TILES*3-1:0]   sel_xhi, sel_yhi;
    reg [TILES-1:0]     hold_x;
    reg [31:0]          root1;
    reg [TILES*5-1:0]   sel_root;
    reg [TILES*64-1:0]  tile_z;
    reg [BANKS*3-1:0]   wsel;
    reg [BANKS-1:0]     wen;
    always @(posedge clk) begin
        en <= en_i; bank_rd <= bank_rd_i; pack_rd <= pack_rd_i;
        sel_xlo <= sel_xlo_i; sel_ylo <= sel_ylo_i; sel_xhi <= sel_xhi_i; sel_yhi <= sel_yhi_i;
        hold_x <= hold_x_i; root1 <= root1_i; sel_root <= sel_root_i;
        tile_z <= tile_z_i; wsel <= wsel_i; wen <= wen_i;
    end
    ntt_bank_net_s #(.TILES(TILES), .BANKS(BANKS), .PBANKS(PBANKS)) u_net (
        .clk(clk), .en(en), .bank_rd(bank_rd), .pack_rd(pack_rd),
        .sel_xlo(sel_xlo), .sel_ylo(sel_ylo), .sel_xhi(sel_xhi), .sel_yhi(sel_yhi), .hold_x(hold_x),
        .root1(root1), .sel_root(sel_root), .op_x(op_x), .op_y(op_y), .op_w(op_w),
        .tile_z(tile_z), .wsel(wsel), .wen(wen), .bank_wd(bank_wd), .bank_we(bank_we));
endmodule
