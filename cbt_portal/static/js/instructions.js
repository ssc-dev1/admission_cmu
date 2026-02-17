$(document).ready(function(){
var interval = setInterval(function() {
                   function parseTime(s) {
                        var part = s.match(/(\d+):(\d+)(?: )?(am|pm)?/i);
                        var hh = parseInt(part[1], 10);
                        var mm = parseInt(part[2], 10);
                        var ap = part[3] ? part[3].toUpperCase() : null;
                        if (ap === "AM") {
                            if (hh == 12) {
                                hh = 0;
                            }
                        }
                        if (ap === "PM") {
                            if (hh != 12) {
                                hh += 12;
                            }
                        }
                        var currentYearMonthDay = new Date();
                        return new Date(currentYearMonthDay.getFullYear(),currentYearMonthDay.getMonth(),currentYearMonthDay.getDate(),hh,mm);
                    }
                    var timer = parseTime($("#timer").val());
                    var currentTime = new Date();
                    if(timer < currentTime)
                    {
                     //console.log("start Test");
                     document.getElementById('paper_start').style.display = 'block';
                     document.getElementById('paper_start_time').style.display = 'none';
                    }
                    else
                    {
                    console.log("Dont Start Test");
                     document.getElementById('paper_start').style.display = 'none';
                     document.getElementById('paper_start_time').style.display = 'block';
                    }
                    }, 1000);
                      window.addEventListener('contextmenu', function (e) {
                      e.preventDefault();
                    }, false);
                });