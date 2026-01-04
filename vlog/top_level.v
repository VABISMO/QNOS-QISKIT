`timescale 1ns / 1ps
module uart_rx #(
    parameter CLKS_PER_BIT = 868 // 100MHz / 115200 ≈ 868
) (
    input i_Clock,
    input i_Rx_Serial,
    output o_Rx_DV,
    output [7:0] o_Rx_Byte
);
    localparam s_IDLE = 3'b000;
    localparam s_RX_START_BIT = 3'b001;
    localparam s_RX_DATA_BITS = 3'b010;
    localparam s_RX_STOP_BIT = 3'b011;
    localparam s_CLEANUP = 3'b100;
    reg r_Rx_Data_R;
    reg r_Rx_Data;
    reg [9:0] r_Clock_Count;
    reg [2:0] r_Bit_Index;
    reg [7:0] r_Rx_Byte;
    reg r_Rx_DV;
    reg [2:0] r_SM_Main;
    initial begin
        r_Rx_Data_R = 1'b1;
        r_Rx_Data = 1'b1;
        r_Clock_Count = 0;
        r_Bit_Index = 0;
        r_Rx_Byte = 0;
        r_Rx_DV = 0;
        r_SM_Main = 0;
    end
    always @(posedge i_Clock) begin
        r_Rx_Data_R <= i_Rx_Serial;
        r_Rx_Data <= r_Rx_Data_R;
    end
    always @(posedge i_Clock) begin
        case (r_SM_Main)
            s_IDLE : begin
                r_Rx_DV <= 1'b0;
                r_Clock_Count <= 0;
                r_Bit_Index <= 0;
                if (r_Rx_Data == 1'b0)
                    r_SM_Main <= s_RX_START_BIT;
                else
                    r_SM_Main <= s_IDLE;
            end
            s_RX_START_BIT : begin
                if (r_Clock_Count == (CLKS_PER_BIT-1)/2) begin
                    if (r_Rx_Data == 1'b0) begin
                        r_Clock_Count <= 0;
                        r_SM_Main <= s_RX_DATA_BITS;
                    end else
                        r_SM_Main <= s_IDLE;
                end else begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_RX_START_BIT;
                end
            end
            s_RX_DATA_BITS : begin
                if (r_Clock_Count < CLKS_PER_BIT-1) begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_RX_DATA_BITS;
                end else begin
                    r_Clock_Count <= 0;
                    r_Rx_Byte[r_Bit_Index] <= r_Rx_Data;
                    if (r_Bit_Index < 7) begin
                        r_Bit_Index <= r_Bit_Index + 1;
                        r_SM_Main <= s_RX_DATA_BITS;
                    end else begin
                        r_Bit_Index <= 0;
                        r_SM_Main <= s_RX_STOP_BIT;
                    end
                end
            end
            s_RX_STOP_BIT : begin
                if (r_Clock_Count < CLKS_PER_BIT-1) begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_RX_STOP_BIT;
                end else begin
                    r_Rx_DV <= 1'b1;
                    r_Clock_Count <= 0;
                    r_SM_Main <= s_CLEANUP;
                end
            end
            s_CLEANUP : begin
                r_SM_Main <= s_IDLE;
                r_Rx_DV <= 0;
            end
            default :
                r_SM_Main <= s_IDLE;
        endcase
    end
    assign o_Rx_DV = r_Rx_DV;
    assign o_Rx_Byte = r_Rx_Byte;
endmodule

module uart_tx #(
    parameter CLKS_PER_BIT = 868 // 100MHz / 115200 ≈ 868
) (
    input i_Clock,
    input i_Tx_DV,
    input [7:0] i_Tx_Byte,
    output o_Tx_Active,
    output reg o_Tx_Serial,
    output o_Tx_Done
);
    localparam s_IDLE = 3'b000;
    localparam s_TX_START_BIT = 3'b001;
    localparam s_TX_DATA_BITS = 3'b010;
    localparam s_TX_STOP_BIT = 3'b011;
    localparam s_CLEANUP = 3'b100;
    reg [2:0] r_SM_Main;
    reg [9:0] r_Clock_Count;
    reg [2:0] r_Bit_Index;
    reg [7:0] r_Tx_Data;
    reg r_Tx_Done;
    reg r_Tx_Active;
    initial begin
        r_SM_Main = 0;
        r_Clock_Count = 0;
        r_Bit_Index = 0;
        r_Tx_Data = 0;
        r_Tx_Done = 0;
        r_Tx_Active = 0;
    end
    always @(posedge i_Clock) begin
        case (r_SM_Main)
            s_IDLE : begin
                o_Tx_Serial <= 1'b1; // Drive Line High for Idle
                r_Tx_Done <= 1'b0;
                r_Clock_Count <= 0;
                r_Bit_Index <= 0;
                if (i_Tx_DV == 1'b1) begin
                    r_Tx_Active <= 1'b1;
                    r_Tx_Data <= i_Tx_Byte;
                    r_SM_Main <= s_TX_START_BIT;
                end else
                    r_SM_Main <= s_IDLE;
            end
            s_TX_START_BIT : begin
                o_Tx_Serial <= 1'b0;
                if (r_Clock_Count < CLKS_PER_BIT-1) begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_TX_START_BIT;
                end else begin
                    r_Clock_Count <= 0;
                    r_SM_Main <= s_TX_DATA_BITS;
                end
            end
            s_TX_DATA_BITS : begin
                o_Tx_Serial <= r_Tx_Data[r_Bit_Index];
                if (r_Clock_Count < CLKS_PER_BIT-1) begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_TX_DATA_BITS;
                end else begin
                    r_Clock_Count <= 0;
                    if (r_Bit_Index < 7) begin
                        r_Bit_Index <= r_Bit_Index + 1;
                        r_SM_Main <= s_TX_DATA_BITS;
                    end else begin
                        r_Bit_Index <= 0;
                        r_SM_Main <= s_TX_STOP_BIT;
                    end
                end
            end
            s_TX_STOP_BIT : begin
                o_Tx_Serial <= 1'b1;
                if (r_Clock_Count < CLKS_PER_BIT-1) begin
                    r_Clock_Count <= r_Clock_Count + 1;
                    r_SM_Main <= s_TX_STOP_BIT;
                end else begin
                    r_Tx_Done <= 1'b1;
                    r_Clock_Count <= 0;
                    r_SM_Main <= s_CLEANUP;
                    r_Tx_Active <= 1'b0;
                end
            end
            s_CLEANUP : begin
                r_Tx_Done <= 1'b0;
                r_SM_Main <= s_IDLE;
            end
            default :
                r_SM_Main <= s_IDLE;
        endcase
    end
    assign o_Tx_Active = r_Tx_Active;
    assign o_Tx_Done = r_Tx_Done;
endmodule

module sccb_master #(
    parameter CLK_DIV = 250 // For 100kHz from 25MHz
) (
    input clk,
    input reset,
    inout scl,
    inout sda,
    input start,
    input read_mode, // 1 for read
    input [7:0] addr,
    input [7:0] subaddr,
    input [7:0] data_in,
    output [7:0] data_out,
    output ready,
    output error
);
    localparam S_IDLE = 0, S_START = 1, S_ADDR_W = 2, S_ACK1 = 3, S_SUBADDR = 4, S_ACK2 = 5, S_DATA_W = 6, S_ACK3 = 7, S_STOP = 8,
               S_START2 = 9, S_ADDR_R = 10, S_ACK4 = 11, S_DATA_R = 12, S_NACK = 13;
    reg [3:0] state;
    reg [7:0] bit_cnt;
    reg sda_out;
    reg scl_out;
    reg ready_reg;
    reg error_reg;
    reg [7:0] data_r;
    reg [15:0] divider;
    initial begin
        state = S_IDLE;
        bit_cnt = 0;
        sda_out = 1;
        scl_out = 1;
        ready_reg = 1;
        error_reg = 0;
        data_r = 0;
        divider = 0;
    end
    assign ready = ready_reg;
    assign error = error_reg;
    assign data_out = data_r;
    assign sda = (sda_out) ? 1'bz : 0;
    assign scl = (scl_out) ? 1'bz : 0;
    always @(posedge clk) begin
        if (reset) begin
            state <= S_IDLE;
            ready_reg <= 1;
            error_reg <= 0;
        end else begin
            divider <= divider + 1;
            if (divider == CLK_DIV) begin
                divider <= 0;
                case (state)
                    S_IDLE: if (start) begin
                        state <= S_START;
                        ready_reg <= 0;
                        sda_out <= 0;
                        scl_out <= 1;
                    end
                    S_START: begin
                        scl_out <= 0;
                        bit_cnt <= 8;
                        state <= S_ADDR_W;
                    end
                    S_ADDR_W: begin
                        if (bit_cnt > 0) begin
                            sda_out <= (addr >> (bit_cnt - 1)) & 1; // Write addr 0x42
                            scl_out <= 1;
                            bit_cnt <= bit_cnt - 1;
                        end else begin
                            sda_out <= 1;
                            scl_out <= 1;
                            state <= S_ACK1;
                        end
                    end
                    S_ACK1: begin
                        scl_out <= 0;
                        if (sda == 0) state <= S_SUBADDR;
                        else begin
                            error_reg <= 1;
                            state <= S_STOP;
                        end
                    end
                    S_SUBADDR: begin
                        if (bit_cnt > 0) begin
                            sda_out <= (subaddr >> (bit_cnt - 1)) & 1;
                            scl_out <= 1;
                            bit_cnt <= bit_cnt - 1;
                        end else begin
                            sda_out <= 1;
                            scl_out <= 1;
                            state <= S_ACK2;
                        end
                    end
                    S_ACK2: begin
                        scl_out <= 0;
                        if (sda == 0) state <= read_mode ? S_START2 : S_DATA_W;
                        else begin
                            error_reg <= 1;
                            state <= S_STOP;
                        end
                    end
                    S_DATA_W: begin
                        if (bit_cnt > 0) begin
                            sda_out <= (data_in >> (bit_cnt - 1)) & 1;
                            scl_out <= 1;
                            bit_cnt <= bit_cnt - 1;
                        end else begin
                            sda_out <= 1;
                            scl_out <= 1;
                            state <= S_ACK3;
                        end
                    end
                    S_ACK3: begin
                        scl_out <= 0;
                        if (sda == 0) state <= S_STOP;
                        else error_reg <= 1;
                    end
                    S_START2: begin
                        sda_out <= 0;
                        scl_out <= 1;
                        bit_cnt <= 8;
                        state <= S_ADDR_R;
                    end
                    S_ADDR_R: begin
                        if (bit_cnt > 0) begin
                            sda_out <= ((addr | 1) >> (bit_cnt - 1)) & 1; // Read addr 0x43
                            scl_out <= 1;
                            bit_cnt <= bit_cnt - 1;
                        end else begin
                            sda_out <= 1;
                            scl_out <= 1;
                            state <= S_ACK4;
                        end
                    end
                    S_ACK4: begin
                        scl_out <= 0;
                        if (sda == 0) state <= S_DATA_R;
                        else begin
                            error_reg <= 1;
                            state <= S_STOP;
                        end
                    end
                    S_DATA_R: begin
                        if (bit_cnt > 0) begin
                            scl_out <= 1;
                            data_r[bit_cnt - 1] <= sda;
                            bit_cnt <= bit_cnt - 1;
                        end else begin
                            scl_out <= 1;
                            sda_out <= 1; // NACK
                            state <= S_NACK;
                        end
                    end
                    S_NACK: begin
                        scl_out <= 0;
                        state <= S_STOP;
                    end
                    S_STOP: begin
                        sda_out <= 0;
                        scl_out <= 1;
                        sda_out <= 1;
                        state <= S_IDLE;
                        ready_reg <= 1;
                    end
                endcase
            end
        end
    end
endmodule

module ov7670_config_rom (
    input [7:0] addr,
    output reg [15:0] dout
);
    always @(*) begin
        case(addr)
            0: dout <= 16'h1280; // COM7 - Reset
            1: dout <= 16'h1280; // COM7 - Reset again
            2: dout <= 16'h1101; // CLKRC
            3: dout <= 16'h1204; // COM7 - RGB
            4: dout <= 16'h3A04; // TSLB
            5: dout <= 16'h4000; // COM15
            6: dout <= 16'h8C00; // RGB444
            7: dout <= 16'h3E19; // COM14
            8: dout <= 16'h7211; // DSP_CTRL3
            9: dout <= 16'h733F; // DSP_CTRL4
            10: dout <= 16'h1404; // SCALING_XSC
            11: dout <= 16'h158D; // SCALING_YSC
            12: dout <= 16'h3D00; // SCALING_DCWCTR
            13: dout <= 16'h3C00; // SCALING_PCLK_DIV
            14: dout <= 16'h1700; // HSTART
            15: dout <= 16'h1801; // HSTOP
            16: dout <= 16'h3202; // HREF
            17: dout <= 16'h1903; // VSTART
            18: dout <= 16'h1A7B; // VSTOP
            19: dout <= 16'h030A; // VREF
            20: dout <= 16'h0C00; // COM3
            21: dout <= 16'h3E00; // COM14
            22: dout <= 16'h7000; // DSP_CTRL1
            23: dout <= 16'h7100; // DSP_CTRL2
            24: dout <= 16'hFF_FF; // End
            default: dout <= 16'hFF_FF;
        endcase
    end
endmodule

module ov7670_ctrl (
    input clk,
    input reset,
    inout scl,
    inout sda,
    output xclk,
    input pclk,
    input vsync,
    input href,
    input [7:0] d,
    output [16:0] bram_addr,
    output [7:0] bram_data,
    input capture_start,
    output reg capture_done,
    output buf_sel_out
);
    reg [7:0] sccb_addr;
    reg [7:0] sccb_data;
    reg sccb_start;
    wire sccb_ready;
    wire sccb_error;
    initial begin
        sccb_addr = 0;
        sccb_data = 0;
        sccb_start = 0;
    end

    sccb_master sccb_inst (
        .clk(clk),
        .reset(reset),
        .scl(scl),
        .sda(sda),
        .start(sccb_start),
        .read_mode(1'b0), // Write for config
        .addr(8'h42),
        .subaddr(sccb_addr),
        .data_in(sccb_data),
        .data_out(),
        .ready(sccb_ready),
        .error(sccb_error)
    );

    reg [7:0] rom_addr;
    wire [15:0] rom_dout;
    initial rom_addr = 0;
    ov7670_config_rom rom_inst (.addr(rom_addr), .dout(rom_dout));
    reg config_done;
    initial config_done = 0;
    always @(posedge clk) begin
        if (reset) begin
            rom_addr <= 0;
            config_done <= 0;
            sccb_start <= 0;
        end else if (!config_done && sccb_ready) begin
            if (rom_dout != 16'hFF_FF) begin
                sccb_addr <= rom_dout[15:8];
                sccb_data <= rom_dout[7:0];
                sccb_start <= 1;
                rom_addr <= rom_addr + 1;
            end else config_done <= 1;
        end else sccb_start <= 0;
    end

    // Capture logic with double buffer
    reg [16:0] addr;
    reg byte_one;
    reg [7:0] byte_high;
    reg capturing;
    initial begin
        addr = 0;
        byte_one = 1;
        byte_high = 0;
        capturing = 0;
    end
    assign bram_addr = addr;
    assign bram_data = (byte_high + d) / 2; // Grayscale
    reg buf_sel_reg;
    initial buf_sel_reg = 0;
    assign buf_sel_out = buf_sel_reg;
    always @(posedge pclk) begin
        if (reset) begin
            capturing <= 0;
            addr <= 0;
            byte_one <= 1;
            buf_sel_reg <= 0;
        end else if (capture_start) begin
            capturing <= 1;
            addr <= 0;
            byte_one <= 1;
            buf_sel_reg <= ~buf_sel_reg; // Toggle buffer
        end else if (capturing) begin
            if (vsync == 1) begin
                capturing <= 0;
                capture_done <= 1;
            end else if (href == 1) begin
                if (byte_one) begin
                    byte_high <= d;
                    byte_one <= 0;
                end else begin
                    addr <= addr + 1;
                    byte_one <= 1;
                end
            end
        end
    end
endmodule

module top_level (
    input clk_100mhz, // System clock
    input reset,
    input rx, // UART RX
    output tx, // UART TX
    output [7:0] laser_rows, // Row enables
    output [7:0] laser_cols, // Column selects
    inout scl, sda, // OV7670 SCCB
    output xclk, // 24MHz to OV7670
    input pclk, vsync, href,
    input [7:0] d, // Camera data
    output [3:0] spi_pins, // SPI to ADF4351 (LE, CLK, DATA, MUXOUT)
    output refclk_out // To ADF4351 REF_IN
);
// UART instance
wire [7:0] uart_data;
wire uart_valid;
wire uart_tx_done;
reg uart_tx_dv;
wire uart_tx_active;
reg [7:0] uart_data_out;
initial begin
    uart_tx_dv = 0;
end

uart_rx uart_rx_inst (
    .i_Clock(clk_100mhz),
    .i_Rx_Serial(rx),
    .o_Rx_DV(uart_valid),
    .o_Rx_Byte(uart_data)
);

uart_tx uart_tx_inst (
    .i_Clock(clk_100mhz),
    .i_Tx_DV(uart_tx_dv),
    .i_Tx_Byte(uart_data_out),
    .o_Tx_Active(uart_tx_active),
    .o_Tx_Serial(tx),
    .o_Tx_Done(uart_tx_done)
);

// Command buffer
reg [7:0] cmd_buffer [0:63]; // Max 64 bytes per command
reg [6:0] buf_idx;
reg command_ready;
initial begin
    buf_idx = 0;
    command_ready = 0;
end
always @(posedge clk_100mhz) begin
    if (reset) begin
        buf_idx <= 0;
        command_ready <= 0;
    end else if (uart_valid) begin
        cmd_buffer[buf_idx] <= uart_data;
        if (uart_data == 8'h0A) begin // '\n'
            command_ready <= 1;
            buf_idx <= 0;
        end else buf_idx <= buf_idx + 1;
    end
end

// FSM for processing commands
localparam S_IDLE = 0;
localparam S_PARSE = 1;
localparam S_EXEC_FIRE = 2;
localparam S_EXEC_PULSE = 3;
localparam S_EXEC_CAPTURE_FRAME = 4;
localparam S_EXEC_CAPTURE_DARK = 5;
localparam S_SEND_IMAGE = 6;
reg [3:0] fsm_state;
initial fsm_state = S_IDLE;

// Parsed parameters
reg [7:0] parsed_row;
reg [7:0] parsed_col;
reg [31:0] parsed_duration_ms;
reg [31:0] parsed_qubit; // For simple qubit int
reg [31:0] parsed_freq_ghz;
reg [31:0] parsed_amp;
reg [31:0] parsed_duration_ns;
reg [31:0] parsed_phase;
initial begin
    parsed_row = 0;
    parsed_col = 0;
    parsed_duration_ms = 0;
    parsed_qubit = 0;
    parsed_freq_ghz = 0;
    parsed_amp = 0;
    parsed_duration_ns = 0;
    parsed_phase = 0;
end

// Dynamic parser
localparam P_CMD = 0, P_ARG1 = 1, P_ARG2 = 2, P_ARG3 = 3, P_ARG4 = 4, P_ARG5 = 5;
reg [3:0] parse_state;
initial parse_state = P_CMD;
reg [6:0] parse_idx;
initial parse_idx = 0;
reg [7:0] cmd_str [0:15]; // Command string buffer
reg [3:0] cmd_len;
initial cmd_len = 0;
reg [31:0] num;
initial num = 0;
reg parsing_num;
initial parsing_num = 0;
reg num_negative;
initial num_negative = 0;

// Parse number task
task parse_number;
    input [6:0] start;
    output [31:0] value;
    reg [6:0] i;
    reg is_float;
    reg [31:0] frac;
    reg frac_div;
    begin
        value = 0;
        i = start;
        is_float = 0;
        frac = 0;
        frac_div = 1;
        if (cmd_buffer[i] == "-") begin
            num_negative = 1;
            i = i + 1;
        end
        while (i < 64 && ((cmd_buffer[i] >= "0" && cmd_buffer[i] <= "9") || cmd_buffer[i] == ".")) begin
            if (cmd_buffer[i] == ".") is_float = 1;
            else if (is_float) begin
                frac = frac * 10 + (cmd_buffer[i] - "0");
                frac_div = frac_div * 10;
            end else value = value * 10 + (cmd_buffer[i] - "0");
            i = i + 1;
        end
        value = value + (frac / frac_div);  // Approximate float as int
        if (num_negative) value = -value;
        parse_idx = i;
    end
endtask

always @(posedge clk_100mhz) begin
    if (reset) begin
        fsm_state <= S_IDLE;
        parse_state <= P_CMD;
        parse_idx <= 0;
        cmd_len <= 0;
        num_negative <= 0;
    end else case (fsm_state)
        S_IDLE: if (command_ready) begin
            command_ready <= 0;
            parse_state <= P_CMD;
            parse_idx <= 0;
            fsm_state <= S_PARSE;
        end
        S_PARSE: begin
            if (parse_idx >= 64 || cmd_buffer[parse_idx] == "\n") begin
                fsm_state <= S_IDLE;
            end else if (cmd_buffer[parse_idx] == " ") begin
                if (parse_state == P_CMD) begin
                    // Determine command
                    if (cmd_len == 10 && cmd_str[0] == "F" && cmd_str[1] == "I" && cmd_str[2] == "R" && cmd_str[3] == "E" && cmd_str[4] == "_" && cmd_str[5] == "L" && cmd_str[6] == "A" && cmd_str[7] == "S" && cmd_str[8] == "E" && cmd_str[9] == "R") begin
                        parse_state <= P_ARG1;
                    end else if (cmd_len == 11 && cmd_str[0] == "A" && cmd_str[1] == "P" && cmd_str[2] == "P" && cmd_str[3] == "L" && cmd_str[4] == "Y" && cmd_str[5] == "_" && cmd_str[6] == "P" && cmd_str[7] == "U" && cmd_str[8] == "L" && cmd_str[9] == "S" && cmd_str[10] == "E") begin
                        parse_state <= P_ARG1;
                    end else if (cmd_len == 13 && cmd_str[0] == "C" && cmd_str[1] == "A" && cmd_str[2] == "P" && cmd_str[3] == "T" && cmd_str[4] == "U" && cmd_str[5] == "R" && cmd_str[6] == "E" && cmd_str[7] == "_" && cmd_str[8] == "F" && cmd_str[9] == "R" && cmd_str[10] == "A" && cmd_str[11] == "M" && cmd_str[12] == "E") begin
                        fsm_state <= S_EXEC_CAPTURE_FRAME;
                    end else if (cmd_len == 12 && cmd_str[0] == "C" && cmd_str[1] == "A" && cmd_str[2] == "P" && cmd_str[3] == "T" && cmd_str[4] == "U" && cmd_str[5] == "R" && cmd_str[6] == "E" && cmd_str[7] == "_" && cmd_str[8] == "D" && cmd_str[9] == "A" && cmd_str[10] == "R" && cmd_str[11] == "K") begin
                        fsm_state <= S_EXEC_CAPTURE_DARK;
                    end else begin
                        uart_data_out <= "E"; uart_tx_dv <= 1;  // ERR
                        fsm_state <= S_IDLE;
                    end
                    cmd_len <= 0;
                end else begin
                    // Next arg
                    parse_state <= parse_state + 1;
                end
                parse_idx <= parse_idx + 1;
            end else begin
                if (parse_state == P_CMD) begin
                    cmd_str[cmd_len] <= cmd_buffer[parse_idx];
                    cmd_len <= cmd_len + 1;
                end else begin
                    case (parse_state)
                        P_ARG1: parse_number(parse_idx, parsed_row);  // For FIRE row or qubit
                        P_ARG2: parse_number(parse_idx, parsed_col);  // col or freq
                        P_ARG3: parse_number(parse_idx, parsed_duration_ms);  // duration or amp
                        P_ARG4: parse_number(parse_idx, parsed_duration_ns);
                        P_ARG5: parse_number(parse_idx, parsed_phase);
                    endcase
                    if (parse_state == P_ARG3 && cmd_len == 10) fsm_state <= S_EXEC_FIRE;
                    if (parse_state == P_ARG5 && cmd_len == 11) fsm_state <= S_EXEC_PULSE;
                end
                parse_idx <= parse_idx + 1;
            end
        end
        S_EXEC_FIRE: begin
            laser_rows_reg <= 1 << parsed_row;
            laser_cols_reg <= ~(1 << parsed_col);  // Invert for sink
            laser_timer <= parsed_duration_ms * 100_000; // ms at 100MHz
            fsm_state <= S_IDLE;
            uart_data_out <= "O"; uart_tx_dv <= 1;  // OK
        end
        S_EXEC_PULSE: begin
            // Send to SPI, assuming qubit as int
            spi_reg <= {parsed_qubit[7:0], parsed_freq_ghz[7:0], parsed_amp[7:0], parsed_duration_ns[7:0], parsed_phase[7:0]}; // Adjust format
            spi_start <= 1;
            fsm_state <= S_IDLE;
            uart_data_out <= "O"; uart_tx_dv <= 1;
        end
        S_EXEC_CAPTURE_FRAME: begin
            capture_start <= 1;
            fsm_state <= S_SEND_IMAGE;
        end
        S_EXEC_CAPTURE_DARK: begin
            capture_start <= 1; // Assume same
            fsm_state <= S_SEND_IMAGE;
        end
        S_SEND_IMAGE: begin
            if (capture_done) begin
                if (uart_tx_done && !uart_tx_dv) begin
                    uart_data_out <= buf_sel_out ? bram_mem_b[send_addr] : bram_mem_a[send_addr];
                    uart_tx_dv <= 1;
                    if (send_addr < 640*480 - 1) send_addr <= send_addr + 1;
                    else begin
                        send_addr <= 0;
                        fsm_state <= S_IDLE;
                    end
                end else uart_tx_dv <= 0;
            end
        end
        default: fsm_state <= S_IDLE;
    endcase
end

// Laser control
reg [7:0] laser_rows_reg;
reg [7:0] laser_cols_reg;
initial begin
    laser_rows_reg = 0;
    laser_cols_reg = 0;
end
assign laser_rows = laser_rows_reg;
assign laser_cols = laser_cols_reg;

// Timer for laser duration
reg [31:0] laser_timer;
initial laser_timer = 0;
always @(posedge clk_100mhz) begin
    if (reset) begin
        laser_rows_reg <= 0;
        laser_cols_reg <= 0;
        laser_timer <= 0;
    end else if (laser_timer > 0) begin
        laser_timer <= laser_timer - 1;
        if (laser_timer == 1) begin
            laser_rows_reg <= 0;
            laser_cols_reg <= 0;
        end
    end
end

// OV7670 instance
wire [16:0] bram_addr;
wire [7:0] bram_data;
wire capture_done;
reg capture_start;
initial capture_start = 0;
reg [16:0] send_addr;
initial send_addr = 0;
wire buf_sel_out;

ov7670_ctrl ov_inst (
    .clk(clk_100mhz),
    .reset(reset),
    .scl(scl),
    .sda(sda),
    .xclk(xclk),
    .pclk(pclk),
    .vsync(vsync),
    .href(href),
    .d(d),
    .bram_addr(bram_addr),
    .bram_data(bram_data),
    .capture_start(capture_start),
    .capture_done(capture_done),
    .buf_sel_out(buf_sel_out)
);

// Double BRAM
reg [7:0] bram_mem_a [0:640*480-1];
reg [7:0] bram_mem_b [0:640*480-1];
always @(posedge pclk) begin
    if (!buf_sel_out) bram_mem_a[bram_addr] <= bram_data;
    else bram_mem_b[bram_addr] <= bram_data;
end

// ADF4351 SPI
reg spi_start;
initial spi_start = 0;
reg [31:0] spi_reg;
initial spi_reg = 0;
reg [5:0] spi_bit;
initial spi_bit = 31;
reg [2:0] spi_state;
initial spi_state = 0;
reg spi_le;
initial spi_le = 1;
reg spi_clk;
initial spi_clk = 0;
reg spi_data;
initial spi_data = 0;
wire spi_muxout = spi_pins[3];
assign spi_pins[0] = spi_le;
assign spi_pins[1] = spi_clk;
assign spi_pins[2] = spi_data;
reg [2:0] reg_idx;
initial reg_idx = 5;
always @(posedge clk_100mhz) begin
    if (reset) begin
        spi_state <= 0;
        spi_le <= 1;
        reg_idx <= 5;
    end else if (spi_start) begin
        // Compute ADF4351 registers based on freq etc. (datasheet)
        case (reg_idx)
            5: spi_reg <= 32'h00000005; // R5 example
            4: spi_reg <= 32'h00000004;
            3: spi_reg <= 32'h00000003;
            2: spi_reg <= 32'h00000002;
            1: spi_reg <= 32'h00000001;
            0: spi_reg <= 32'h00000000;
        endcase
        spi_le <= 0;
        spi_bit <= 31;
        spi_state <= 1;
        spi_start <= 0;
    end else if (spi_state == 1) begin
        spi_data <= spi_reg[spi_bit];
        spi_clk <= 1;
        spi_state <= 2;
    end else if (spi_state == 2) begin
        spi_clk <= 0;
        if (spi_bit == 0) begin
            spi_le <= 1;
            if (reg_idx == 0) spi_state <= 3; // Wait lock
            else begin
                reg_idx <= reg_idx - 1;
                spi_state <= 1; // Next reg
            end
        end else begin
            spi_bit <= spi_bit - 1;
            spi_state <= 1;
        end
    end else if (spi_state == 3) begin
        if (spi_muxout) spi_state <= 0; // Locked
        else if (spi_timer == 100000) begin // Timeout
            spi_state <= 0;
            // Error
        end
    end
end
reg [31:0] spi_timer;
initial spi_timer = 0;
always @(posedge clk_100mhz) if (spi_state == 3) spi_timer <= spi_timer + 1; else spi_timer <= 0;

// REFCLK: 25MHz
reg [1:0] div;
initial div = 0;
always @(posedge clk_100mhz) if (reset) div <= 0; else div <= div + 1;
assign refclk_out = div[1];
assign xclk = div[1];

endmodule
