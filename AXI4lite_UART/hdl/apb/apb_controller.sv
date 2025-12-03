module apb_controller(
	input clk,
	input reset_n,
	input psel_i,
	input penable_i,
	input addr_err_i,
	output logic pready_o,
	output logic act_en_o,
	output logic pslverr_o


);
assign pslverr_o = addr_err_i & pready_o;
	typedef enum logic [1:0] {
    IDLE   = 2'b00,
    SETUP  = 2'b01,
    WAIT_ = 2'b10,
    ACCESS = 2'b11
  } state_e;

  state_e current_state, next_state;
  always_ff @(posedge clk) begin
    if (~reset_n) begin
      current_state <= IDLE;
    end else begin
      current_state <= next_state;
    end
  end
 
   always_comb begin
    next_state = IDLE;
    case (current_state)
      IDLE: begin
        if (psel_i & !penable_i) begin
          next_state = SETUP;
        end
      end

      SETUP: begin
      	if(~psel_i) next_state = IDLE;
      	else if(penable_i) next_state = WAIT_;
      	else next_state = SETUP;

      end
      WAIT_: begin
      	next_state = ACCESS;
      end
      ACCESS: begin
      	if(psel_i) begin
      		next_state = SETUP;
      	end else begin
      		next_state = IDLE;
      	end
      end
      default: next_state = IDLE;
    endcase
  end

  // OUTPUT
 always_comb begin
 	pready_o = 1'b0;
 	act_en_o = 1'b0;
    
    case (current_state)
      IDLE: begin
        
      end

      SETUP: begin
        
      end
      WAIT_: begin
      	act_en_o = 1'b1;
      end
      ACCESS: begin
      	pready_o = 1'b1;
        
      end

    endcase
  end






endmodule 