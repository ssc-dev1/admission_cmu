$(document).ready(function () {
    /* $('body').bind('cut copy', function(e) {
                  e.preventDefault();
                });
            });*/



        $('.nextsection').hide();
   

    var timer2 = "";
    var minutes = "";
    var seconds = "";
    $.ajax({
        url: "/cbt/paper/currentState",
        type: "GET",
        dataType: "json",
        contentType: false,
        processData: false,
        success: function (data) {

            if (data.paper_state) {
                window.location.href = "/cbt/paper/finish/page";
            }
            if (data.time_remaining) {
                timer2 = data.time_remaining;
                var timer = timer2.split(':');
                minutes = parseInt(timer[0]),
                    seconds = parseInt(timer[1]);
            } else {
                var time = $("#duration").val();
                minutes = parseInt(time);
                seconds = 0;
            }
            $(function () {
                $(".paginate").paginga({
                    page: data.current_q ? parseInt(data.current_q) : 1
                });
            });
            $(".previous-step").text("Prev");
            $(".next-step").text("Next Section");
        },
        error: function (data) { }
    });
    jQuery(function () {
        jQuery(".countdown").html(minutes + ":" + seconds);
        var count = setInterval(function () {
            if (parseInt(minutes) < 0) {
                clearInterval(count);
            } else {
                jQuery(".countdown").html(minutes + ":" + seconds);
                if (seconds == 0) {
                    minutes--;
                    seconds = 60;
                    if (minutes == 0) {
                        window.location.href = "/cbt/paper/finish/page";
                    }
                }
                seconds--;
            }
        }, 1000);
    });
    var interval = setInterval(function () {
        timer2 = minutes + ':' + seconds;
        var formData = new FormData();
        formData.append('time', timer2);
        $.ajax({
            url: "/cbt/time/remaining",
            type: "POST",
            dataType: "json",
            data: formData,
            // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
            contentType: false,
            processData: false,
            success: function (data) { },
            error: function (data) { }
        });
    }, 1000 * 30 * 1);

    // on review and on finish test


    //    $(".pre").html("Next Section");
    //    $(".nex").html("Previous Section");
    window.addEventListener('contextmenu', function (e) {
        e.preventDefault();
    }, false);




    $('.lastPage,.nextPage,.previousPage,.firstPage').on('click', function() {

        // active_page = $(this).parent().find('.pageNumbers').find('a.active')
        // active_page_no = $(this).parent().find('.pageNumbers').find('a').index(active_page) +1
        // total_page = $(this).parent().find('.pageNumbers').find('a').length 
        // console.log(active_page_no);
        // console.log(total_page);
       

      })

});
function record_time() {

    timer5 = jQuery(".countdown").text();
    var formData = new FormData();
    formData.append('time', timer5);
    $.ajax({
        url: "/cbt/time/remaining",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            window.location.href = "/cbt/paper/review";
        },
        error: function (data) { }
    });
}
function record_time_rev() {

    timer5 = jQuery(".countdown").text();
    var formData = new FormData();
    formData.append('time', timer5);
    $.ajax({
        url: "/cbt/time/remaining",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            // window.location.href = "/cbt/paper";
        },
        error: function (data) { }
    });
}
function record_time_old() {

    timer5 = jQuery(".countdown").text();
    var formData = new FormData();
    formData.append('time', timer5);
    $.ajax({
        url: "/cbt/time/remaining",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            window.location.href = "/cbt/paper";
        },
        error: function (data) { }
    });
}
function rec_answer(question, subject, paper, answer_no, answer) {

    var formData = new FormData();
    var page = '';
    $("#" + subject + '_' + question).remove();
    $(".pageNumbers").children('a').each(function () {
        var element = $(this);
        var activeOrNot = $(this).prop('class');
        if (activeOrNot == 'active') {
            page = element[0].dataset.page;
            //            debugger;
            //            element.addClass("green");
        }
    });
    formData.append('question_id', question);
    formData.append('page', page);
    formData.append('subject_id', subject);
    formData.append('paper_id', paper);
    formData.append('answer', answer);
    formData.append('answer_no', answer_no);
    $.ajax({
        url: "/cbt/rec/answer",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            console.log(data.message);
            console.log(data.total_q);
            console.log(data.answered);
            jQuery("#total").html(data.total_q);
            jQuery("#answered").html(data.answered);
            jQuery("#unanswered").html(data.total_q - data.answered);
            jQuery("#total_finish_paper").html(data.total_q);
            jQuery("#total_answered_paper").html(data.answered);
            jQuery("#total_unanswered_paper").html(data.total_q - data.answered);
        },
        error: function (data) {
            console.log('error');
            console.log(data.message);
            alert("Network Issue");
        }
    });
}
function paper_finish(paper) {
    var formData = new FormData();
    formData.append('paper_id', paper);
    $.ajax({
        url: "/cbt/paper/finish",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            window.location.href = "/cbt/paper/finish/page";
        },
        error: function (data) {
            console.log(data.message)
        }
    });
}
function mark_review(question, subject, paper, state) {
    var formData = new FormData();
    formData.append('question_id', question);
    formData.append('subject_id', subject);
    formData.append('paper_id', paper);
    formData.append('mark', state.checked);
    $.ajax({
        url: "/cbt/rec/mark_review",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            //  console.log(data.message)
        },
        error: function (data) {
            console.log('error');
            console.log(data.message);

        }
    });
}
function review_marked_questions(paper) {
    var formData = new FormData();
    formData.append('paper_id', paper);
    $.ajax({
        url: "/cbt/rec/review/marked/questions",
        type: "POST",
        dataType: "json",
        data: formData,
        // beforeSend: function(){ showNotify('Please wait !','warning','top-right');},
        contentType: false,
        processData: false,
        success: function (data) {
            $("#mark_body").empty();
            for (var i = 0; i < data.mark_review_list.length; i++) {
                $("#mark_body").append("Q. ");
                $("#mark_body").append(data.mark_review_list[i].question);
                $("#mark_body").append("(" + data.mark_review_list[i].subject + ")");
                $("#mark_body").append("<br/>");
                console.log(data.mark_review_list[i].question);
                for (var j = 0; j < data.mark_review_list[i].options.length; j++) {
                    var rec_options = "<div id='view-radio-buttons'><p><label> <input class='with-gap' name='group3' type='radio' onchange='rec_answer()'/> </label></p><span></span></div>";
                    $("#mark_body").append(j + 1 + "." + rec_options);
                    $("#mark_body").append(data.mark_review_list[i].options[j].option);
                    $("#mark_body").append("<br/>");
                }
            }
        },
        error: function (data) {
            console.log('error');
            console.log(data.message);
        }
    });
}

