// Deterministic simulation and exact endpoint controls. MIT.
module mac_tb;
 reg clk=0,reset=1,enable=0;
 reg signed [3:0] a=0,b=0;
 wire signed [31:0] acc32;
 wire signed [19:0] acc20;
 wire signed [12:0] acc13;
 reg signed [31:0] gold;
 reg [31:0] rng=32'hc2002026;
 integer row,col;
 mac_register #(.W(32)) m32(clk,reset,enable,a,b,acc32);
 mac_register #(.W(20)) m20(clk,reset,enable,a,b,acc20);
 mac_register #(.W(13)) m13(clk,reset,enable,a,b,acc13);
 always #5 clk=~clk;
 function [31:0] advance;
  input [31:0] x;
  reg [31:0] y;
  begin y=x^(x<<13);y=y^(y>>17);advance=y^(y<<5);end
 endfunction
 initial begin
  for(row=0;row<64;row=row+1) begin
   @(negedge clk);reset=1;enable=0;gold=0;
   @(posedge clk);#1;
   for(col=0;col<4096;col=col+1) begin
    @(negedge clk);reset=0;enable=1;
    if(row==0)begin a=-8;b=-8;end
    else if(row==1)begin a=-8;b=7;end
    else if(row==2)begin a=7;b=7;end
    else if(row==3)begin a=7;b=-8;end
    else begin rng=advance(rng);a=rng[3:0];rng=advance(rng);b=rng[3:0];end
    gold=gold+$signed(a)*$signed(b);
    @(posedge clk);#1;
    if(acc32!==gold || {{12{acc20[19]}},acc20}!==gold || acc13!==gold[12:0]) begin
     $display("STOP RTL_MAC_MISMATCH row=%0d col=%0d",row,col);$fatal(1);
    end
   end
   if(acc32[12:9]!==acc13[12:9])begin $display("STOP RTL_BUCKET_MISMATCH");$fatal(1);end
  end
  $display("RTL_SIMULATION_PASS rows=64 terms_per_row=4096 accumulation_checks=262144");$finish;
 end
endmodule
