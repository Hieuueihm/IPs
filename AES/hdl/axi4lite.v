
module axi4lite #(
    parameter KEY_BITS = 128
) (
    input  wire        aclk,
    input  wire        aresetn,

    // AXI Write Address
    input  wire [7:0]  s_axi_awaddr,
    input  wire [2:0]  s_axi_awprot,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,

    // AXI Write Data
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,

    // AXI Write Response
    output reg  [1:0]  s_axi_bresp,
    output reg         s_axi_bvalid,
    input  wire        s_axi_bready,

    // AXI Read Address
    input  wire [7:0]  s_axi_araddr,
    input  wire [2:0]  s_axi_arprot,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,

    // AXI Read Data
    output reg  [31:0] s_axi_rdata,
    output reg  [1:0]  s_axi_rresp,
    output reg         s_axi_rvalid,
    input  wire        s_axi_rready
);

    // ========================================
    // Register Map
    // ========================================
    // 0x00 : CONTROL
    //        0x01 = START
    //        0x02 = LOAD_KEY
    //        0x04 = LOAD_IV
    //
    // 0x04 : CONFIG
    //        [1:0] = MODE
    //          00 = ECB
    //          01 = CBC
    //          10 = CTR
    //        [2] = DECRYPT
    //
    // 0x08 : STATUS
    //        [0] = BUSY
    //        [1] = KEY_READY
    //        [2] = DONE
    //
    // 0x10 - 0x2C : KEY[0:7]
    // 0x30 - 0x3C : IV[0:3]
    // 0x40 - 0x4C : DATA_IN[0:3]
    // 0x50 - 0x5C : DATA_OUT[0:3]

    reg [31:0] key_word [0:7];
    reg [31:0] iv_word  [0:3];
    reg [31:0] din_word [0:3];

    reg [2:0] config;
    reg done_sticky;
    reg key_loading;

    reg cmd_start;
    reg cmd_key_load;
    reg cmd_iv_load;

    

    wire [255:0] key_all = {
        key_word[0],
        key_word[1],
        key_word[2],
        key_word[3],
        key_word[4],
        key_word[5],
        key_word[6],
        key_word[7]
    };

    wire [127:0] iv_all = {
        iv_word[0], iv_word[1],
        iv_word[2], iv_word[3]
    };

    wire [127:0] din_all = {
        din_word[0], din_word[1],
        din_word[2], din_word[3]
    };

    wire [127:0] result;
    wire [127:0] unused_iv_out;

    wire core_busy;
    wire core_key_ready;
    wire core_done;

    wire status_busy =
        core_busy | key_loading |
        cmd_start | cmd_key_load | cmd_iv_load;

    wire status_key_ready =
        core_key_ready & !key_loading;

   

    aes_core #(
        .KEY_BITS(KEY_BITS)
    ) u_core (
        .clk       (aclk),
        .rst_n     (aresetn),

        .key_load  (cmd_key_load),
        .key_in    (key_all[255 -: KEY_BITS]),
        .key_ready (core_key_ready),

        .iv_load   (cmd_iv_load),
        .iv_in     (iv_all),
        .iv_out    (unused_iv_out),

        .mode      (config[1:0]),
        .decrypt   (config[2]),

        .start     (cmd_start),
        .data_in   (din_all),

        .data_out  (result),
        .busy      (core_busy),
        .done      (core_done)
    );

    // ========================================
    // AXI Write Channel
    // ========================================

    reg got_aw;
    reg got_w;

    reg [7:0]  awaddr_q;
    reg [31:0] wdata_q;
    reg [3:0]  wstrb_q;

    wire commit_write =
        got_aw && got_w && !s_axi_bvalid;

    assign s_axi_awready =
        !got_aw && !s_axi_bvalid;

    assign s_axi_wready =
        !got_w && !s_axi_bvalid;

    // ========================================
    // Byte Write Support
    // ========================================

    function [31:0] strobe_merge;
        input [31:0] old_value;
        input [31:0] new_value;
        input [3:0]  strobe;

        integer b;

        begin
            strobe_merge = old_value;

            for (b = 0; b < 4; b = b + 1) begin
                if (strobe[b])
                    strobe_merge[b*8 +: 8] =
                        new_value[b*8 +: 8];
            end
        end
    endfunction

    // ========================================
    // AXI Write Logic
    // ========================================

    integer i;

    always @(posedge aclk) begin
        if (!aresetn) begin
            got_aw <= 1'b0;
            got_w  <= 1'b0;

            awaddr_q <= 8'b0;
            wdata_q  <= 32'b0;
            wstrb_q  <= 4'b0;

            s_axi_bvalid <= 1'b0;
            s_axi_bresp  <= 2'b00;

            config      <= 3'b0;
            done_sticky <= 1'b0;
            key_loading <= 1'b0;

            cmd_start    <= 1'b0;
            cmd_key_load <= 1'b0;
            cmd_iv_load  <= 1'b0;

            for (i = 0; i < 8; i = i + 1)
                key_word[i] <= 32'b0;

            for (i = 0; i < 4; i = i + 1) begin
                iv_word[i]  <= 32'b0;
                din_word[i] <= 32'b0;
            end
        end
        else begin
            // Command pulses
            cmd_start    <= 1'b0;
            cmd_key_load <= 1'b0;
            cmd_iv_load  <= 1'b0;

            if (core_done)
                done_sticky <= 1'b1;

            if (key_loading &&
                core_key_ready &&
                !cmd_key_load)
                key_loading <= 1'b0;

            // Receive write address
            if (s_axi_awvalid && s_axi_awready) begin
                got_aw   <= 1'b1;
                awaddr_q <= s_axi_awaddr;
            end

            // Receive write data
            if (s_axi_wvalid && s_axi_wready) begin
                got_w   <= 1'b1;
                wdata_q <= s_axi_wdata;
                wstrb_q <= s_axi_wstrb;
            end

            // Write response handshake
            if (s_axi_bvalid && s_axi_bready)
                s_axi_bvalid <= 1'b0;

            // Write register
            if (commit_write) begin
                got_aw <= 1'b0;
                got_w  <= 1'b0;

                s_axi_bvalid <= 1'b1;
                s_axi_bresp  <= 2'b00;

                if (awaddr_q[1:0] != 2'b00) begin
                    s_axi_bresp <= 2'b10;
                end

                // CONTROL
                else if (awaddr_q == 8'h00) begin
                    if (wstrb_q[0]) begin
                        case (wdata_q[2:0])

                            3'b000: begin
                            end

                            // START
                            3'b001: begin
                                if (!status_busy &&
                                    status_key_ready &&
                                    config[1:0] != 2'b11) begin

                                    cmd_start <= 1'b1;
                                    done_sticky <= 1'b0;
                                end
                                else
                                    s_axi_bresp <= 2'b10;
                            end

                            // LOAD KEY
                            3'b010: begin
                                if (!status_busy) begin
                                    cmd_key_load <= 1'b1;
                                    key_loading  <= 1'b1;
                                    done_sticky  <= 1'b0;
                                end
                                else
                                    s_axi_bresp <= 2'b10;
                            end

                            // LOAD IV
                            3'b100: begin
                                if (!status_busy)
                                    cmd_iv_load <= 1'b1;
                                else
                                    s_axi_bresp <= 2'b10;
                            end

                            default:
                                s_axi_bresp <= 2'b10;

                        endcase
                    end
                end

                // CONFIG
                else if (awaddr_q == 8'h04) begin
                    if (wstrb_q[0])
                        config <= wdata_q[2:0];
                end

                // KEY
                else if (awaddr_q >= 8'h10 &&
                         awaddr_q <= 8'h2C) begin

                    key_word[
                        (awaddr_q - 8'h10) >> 2
                    ] <= strobe_merge(
                        key_word[
                            (awaddr_q - 8'h10) >> 2
                        ],
                        wdata_q,
                        wstrb_q
                    );
                end

                // IV
                else if (awaddr_q >= 8'h30 &&
                         awaddr_q <= 8'h3C) begin

                    iv_word[
                        (awaddr_q - 8'h30) >> 2
                    ] <= strobe_merge(
                        iv_word[
                            (awaddr_q - 8'h30) >> 2
                        ],
                        wdata_q,
                        wstrb_q
                    );
                end

                // DATA INPUT
                else if (awaddr_q >= 8'h40 &&
                         awaddr_q <= 8'h4C) begin

                    din_word[
                        (awaddr_q - 8'h40) >> 2
                    ] <= strobe_merge(
                        din_word[
                            (awaddr_q - 8'h40) >> 2
                        ],
                        wdata_q,
                        wstrb_q
                    );
                end

                else begin
                    s_axi_bresp <= 2'b10;
                end
            end
        end
    end

    // ========================================
    // AXI Read Channel
    // ========================================

    assign s_axi_arready = !s_axi_rvalid;

    always @(posedge aclk) begin
        if (!aresetn) begin
            s_axi_rdata  <= 32'b0;
            s_axi_rresp  <= 2'b00;
            s_axi_rvalid <= 1'b0;
        end
        else begin

            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;

            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp  <= 2'b00;
                s_axi_rdata  <= 32'b0;

                if (s_axi_araddr[1:0] != 2'b00)
                    s_axi_rresp <= 2'b10;

                // CONTROL
                else if (s_axi_araddr == 8'h00)
                    s_axi_rdata <= 32'b0;

                // CONFIG
                else if (s_axi_araddr == 8'h04)
                    s_axi_rdata <= {29'b0, config};

                // STATUS
                else if (s_axi_araddr == 8'h08)
                    s_axi_rdata <= {
                        29'b0,
                        done_sticky,
                        status_key_ready,
                        status_busy
                    };

                // IV
                else if (s_axi_araddr >= 8'h30 &&
                         s_axi_araddr <= 8'h3C)

                    s_axi_rdata <= iv_word[
                        (s_axi_araddr - 8'h30) >> 2
                    ];

                // DATA INPUT
                else if (s_axi_araddr >= 8'h40 &&
                         s_axi_araddr <= 8'h4C)

                    s_axi_rdata <= din_word[
                        (s_axi_araddr - 8'h40) >> 2
                    ];

                // DATA OUTPUT
                else if (s_axi_araddr >= 8'h50 &&
                         s_axi_araddr <= 8'h5C) begin

                    case (s_axi_araddr[3:2])
                        2'd0:
                            s_axi_rdata <= result[127:96];

                        2'd1:
                            s_axi_rdata <= result[95:64];

                        2'd2:
                            s_axi_rdata <= result[63:32];

                        2'd3:
                            s_axi_rdata <= result[31:0];
                    endcase
                end

                else
                    s_axi_rresp <= 2'b10;
            end
        end
    end

endmodule
