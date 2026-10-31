// Measurement wrapper only: 16 tiles sharing one registered en, as the core drives them.
// Every tile has its own registered inputs and outputs, so Vivado cannot merge tiles. Compares
// EN_REG = 0 (the shared en register drives every datapath register of all 16 tiles) with
// EN_REG = 1 (each tile registers en once and fans it out locally).
module tile_array16_top #(parameter integer TREN_MANG = 3,
                          parameter integer EN_REG    = 0,
                          parameter integer IN_REG    = 0) (
    input  wire              clk, rst_i, en_i,
    input  wire [16-1:0]     cfg_we_i, cfg_slot_i, cfg_floor_i, cfg_halve_i,
    input  wire [16*32-1:0]  cfg_q_i, cfg_qinv_i,
    input  wire [16-1:0]     req_valid_i, req_dir_i, req_slot_i,
    input  wire [16*3-1:0]   req_mode_i,
    input  wire [16*2-1:0]   req_sign_i,
    input  wire [16*64-1:0]  req_data_i,
    input  wire [16*32-1:0]  req_root_i,
    input  wire [16*8-1:0]   req_tag_i,
    output reg  [16-1:0]     idle_o, req_ready_o, rsp_valid_o,
    output reg  [16*65-1:0]  rsp_data_o,
    output reg  [16*8-1:0]   rsp_tag_o
);
    reg rst, en;
    always @(posedge clk) begin rst <= rst_i; en <= en_i; end

    genvar t;
    generate for (t = 0; t < 16; t = t + 1) begin : g_tile
        reg         cfg_we, cfg_slot, cfg_floor, cfg_halve, req_valid, req_dir, req_slot;
        reg [31:0]  cfg_q, cfg_qinv, req_root;
        reg [2:0]   req_mode;
        reg [1:0]   req_sign;
        reg [63:0]  req_data;
        reg [7:0]   req_tag;
        wire        idle, req_ready, rsp_valid;
        wire [64:0] rsp_data;
        wire [7:0]  rsp_tag;
        always @(posedge clk) begin
            cfg_we <= cfg_we_i[t]; cfg_slot <= cfg_slot_i[t]; req_slot <= req_slot_i[t];
            cfg_floor <= cfg_floor_i[t];
            cfg_halve <= cfg_halve_i[t]; cfg_q <= cfg_q_i[32*t+:32]; cfg_qinv <= cfg_qinv_i[32*t+:32];
            req_valid <= req_valid_i[t]; req_dir <= req_dir_i[t]; req_mode <= req_mode_i[3*t+:3];
            req_sign <= req_sign_i[2*t+:2]; req_data <= req_data_i[64*t+:64]; req_root <= req_root_i[32*t+:32];
            req_tag <= req_tag_i[8*t+:8];
            idle_o[t] <= idle; req_ready_o[t] <= req_ready; rsp_valid_o[t] <= rsp_valid;
            rsp_data_o[65*t+:65] <= rsp_data; rsp_tag_o[8*t+:8] <= rsp_tag;
        end
        tile_thu #(.TREN_MANG(TREN_MANG), .IN_REG(IN_REG), .EN_REG(EN_REG)) u_tile (
            .clk(clk), .rst(rst), .en(en), .idle(idle),
            .cfg_we(cfg_we), .cfg_slot(cfg_slot), .cfg_q(cfg_q), .cfg_qinv(cfg_qinv),
            .cfg_floor(cfg_floor), .cfg_halve(cfg_halve),
            .req_valid(req_valid), .req_ready(req_ready), .req_mode(req_mode), .req_dir(req_dir), .req_slot(req_slot),
            .req_sign(req_sign), .req_data(req_data), .req_root(req_root), .req_tag(req_tag),
            .rsp_valid(rsp_valid), .rsp_data(rsp_data), .rsp_tag(rsp_tag));
    end endgenerate
endmodule
