
module baud_generator #(
    parameter SYSTEM_FREQUENCY = 50_000_000,
    parameter SAMPLING_RATE = 16
) (
    input clk,
    input reset_n,
    input [2:0] baud_sl_i,
    output logic tick_tx,
    output logic tick_rx
);

    logic [31:0] BIT_PERIOD_TX, BIT_PERIOD_RX;
    logic [31:0] counter_tx, counter_rx;
    logic [2:0] baud_sl_prev;
    logic baud_changed;

    // logic [31:0] baud_rate;

    logic [31:0] BIT_PERIOD_TX_LUT [0:7];
    logic [31:0] BIT_PERIOD_RX_LUT [0:7];

    initial begin
        BIT_PERIOD_TX_LUT[0] = SYSTEM_FREQUENCY / 4800;
        BIT_PERIOD_TX_LUT[1] = SYSTEM_FREQUENCY / 9600;
        BIT_PERIOD_TX_LUT[2] = SYSTEM_FREQUENCY / 14400;
        BIT_PERIOD_TX_LUT[3] = SYSTEM_FREQUENCY / 19200;
        BIT_PERIOD_TX_LUT[4] = SYSTEM_FREQUENCY / 38400;
        BIT_PERIOD_TX_LUT[5] = SYSTEM_FREQUENCY / 57600;
        BIT_PERIOD_TX_LUT[6] = SYSTEM_FREQUENCY / 115200;
        BIT_PERIOD_TX_LUT[7] = SYSTEM_FREQUENCY / 230400;


        BIT_PERIOD_RX_LUT[0] = SYSTEM_FREQUENCY / (16 *4800);
        BIT_PERIOD_RX_LUT[1] = SYSTEM_FREQUENCY / (16 *9600);
        BIT_PERIOD_RX_LUT[2] = SYSTEM_FREQUENCY / (16 *14400);
        BIT_PERIOD_RX_LUT[3] = SYSTEM_FREQUENCY / (16 *19200);
        BIT_PERIOD_RX_LUT[4] = SYSTEM_FREQUENCY / (16 *38400);
        BIT_PERIOD_RX_LUT[5] = SYSTEM_FREQUENCY / (16 *57600);
        BIT_PERIOD_RX_LUT[6] = SYSTEM_FREQUENCY / (16 *115200);
        BIT_PERIOD_RX_LUT[7] = SYSTEM_FREQUENCY / (16 *230400);
    end

    // Detect baud rate change
    always_ff @(posedge clk) begin
        if (!reset_n) begin
            baud_sl_prev <= 0;
            baud_changed <= 0;
        end else begin
            baud_changed <= (baud_sl_i != baud_sl_prev);
            baud_sl_prev <= baud_sl_i;
        end
    end
    always_ff @(posedge clk) begin : proc_
        if(~reset_n) begin
            BIT_PERIOD_TX <= BIT_PERIOD_TX_LUT[6];
            BIT_PERIOD_RX <= BIT_PERIOD_RX_LUT[6];
        end else if(baud_changed) begin
            BIT_PERIOD_TX <= BIT_PERIOD_TX_LUT[baud_sl_i];
            BIT_PERIOD_RX <= BIT_PERIOD_RX_LUT[baud_sl_i];
        end
    end

    // TX Counter
    always_ff @(posedge clk) begin
        if (~reset_n ) begin
            counter_tx <= 0;
            tick_tx <= 0;
        end else if(baud_changed) begin
         counter_tx <= 0;
            tick_tx <= 0;
        end else begin
            if (counter_tx == BIT_PERIOD_TX - 1) begin
                counter_tx <= 0;
                tick_tx <= 1;
            end else begin
                counter_tx <= counter_tx + 1;
                tick_tx <= 0;
            end
        end
    end

    // RX Counter
    always_ff @(posedge clk) begin
        if (!reset_n || baud_changed) begin
            counter_rx <= 0;
            tick_rx <= 0;
        end else begin
            if (counter_rx == BIT_PERIOD_RX - 1) begin
                counter_rx <= 0;
                tick_rx <= 1;
            end else begin
                counter_rx <= counter_rx + 1;
                tick_rx <= 0;
            end
        end
    end

endmodule
