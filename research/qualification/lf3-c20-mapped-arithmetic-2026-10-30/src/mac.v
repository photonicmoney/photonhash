// Exact int4 MAC datapath study. MIT. No memory system or hash integration.
module mac_comb #(parameter W=32)(input signed [3:0] a,b,
 input signed [W-1:0] acc, output signed [W-1:0] next_acc);
 wire signed [7:0] product = a*b;
 assign next_acc = acc + {{(W-8){product[7]}},product};
endmodule
module mac_register #(parameter W=32)(input clk,reset,enable,
 input signed [3:0] a,b,output reg signed [W-1:0] acc);
 wire signed [W-1:0] next_acc;
 mac_comb #(.W(W)) add(a,b,acc,next_acc);
 always @(posedge clk) begin
  if(reset) acc <= {W{1'b0}};
  else if(enable) acc <= next_acc;
 end
endmodule
module equiv(input signed [3:0] a,b,input signed [19:0] acc,
 output mismatch);
 wire signed [19:0] full;
 wire signed [12:0] residue;
 mac_comb #(.W(20)) wide(a,b,acc,full);
 mac_comb #(.W(13)) narrow(a,b,acc[12:0],residue);
 assign mismatch = |(full[12:0]^residue);
endmodule
