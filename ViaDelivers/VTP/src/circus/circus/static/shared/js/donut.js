                       //active	  //late	//done
var myColor			= ["#7cbbff","#ff6c5b","#c5ff7f"];
var myData			= [0,0,0];

var backgroundColor	= '#333333';

var cx 				= 75;
var cy 				= 75;
var r1 				= 70;
var r2 				= 45;
var sw 				= 2;

function getTotal(data){
    var total = 0;
    for(i in data){
        total+=parseInt(data[i]);
    }
    return total;
}

function plotData(id, totalId, data, color, bg) {

    var canvas;
    var ctx;
    var lastend = 0;
    var myTotal = getTotal(data);

    document.getElementById(totalId).innerHTML = myTotal;

    canvas		= document.getElementById(id);
    ctx			= canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (var i = 0; i < data.length; i++) {

        sa = lastend + Math.PI*0.5;
        ea = lastend+ (Math.PI*2*(data[i]/myTotal)) + Math.PI*0.5;

        ctx.lineWidth = sw;
        ctx.strokeStyle = bg;

        ctx.fillStyle = color[i];
        ctx.beginPath();
        ctx.moveTo(cx,cy);
        ctx.arc(cx,cy,r1,sa,ea,false);
        ctx.lineTo(cx,cy);
        ctx.fill();
        ctx.stroke();

        lastend += Math.PI*2*(data[i]/myTotal);
    }

    //draw center
    ctx.fillStyle = bg;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r2, 0, 2*Math.PI, false);
    ctx.fill();
}