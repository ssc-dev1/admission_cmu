// before submitting check and change color of required fields
function check_form_validation(params) {
    // this function is used for checking all the requied fields are valid and filled properly
    form = $(params).parent().find('form')
    var valid_form = true
    
    form_inputs = $(form).find('.form-control');
    $(form_inputs).each(function (index, element) {
        if ($(element).prop('required')) {
            if ($(element).is(":hidden")) {
                $(element).removeAttr('required');
            }
            if (!(element.checkValidity()) && $(element).is(":visible")) {
                $(element).css("border-bottom", "2px solid red");
                $(element).focus();
                valid_form = false;
                return false;
            }
            if ($(element).get(0).tagName == 'SELECT' && $(element).is(":visible")) {
                if ($(element).find(':selected').val() == '0' || $(element).find(':selected').val() == '') {
                    $(element).css("border-bottom", "2px solid red");
                    $(element).focus();
                    valid_form = false;
                    return false;
                }
            }
        }
    });
    if (valid_form == true) {
        $(form).find(':submit').click();
    }
}


// progress and header tab enable
function prepare_next_step(data) {
    $('#application_step').val(data['step_no'])
    $('#application_state').val(data['application_state'])
    $('.header_tab').each(function (index, element) {
        index += 1
        application_step = $('#application_step').val()
        application_state = $('#application_state').val()
        if (index <= application_step) {
            if (index < application_step) {
                if ($(element).hasClass('diable_header_tab')) {
                    $(element).removeClass('diable_header_tab')
                }
                if ($(element).children('a').last().children('i').hasClass('fa-angle-up')) {
                    $(element).click()
                }
            }
            if (index == application_step) {
                if ($(element).hasClass('diable_header_tab')) {
                    $(element).removeClass('diable_header_tab')
                }
                if ($(element).children('a').last().children('i').hasClass('fa-angle-down')) {
                    $(element).click()
                }
                var offset = $(element).offset()
                offset.top = 400;
                $('html, body').animate({
                    scrollTop: offset.top,
                }, 1000);
                return false
            }
        }
    })
    for (i = 0; i < data['step_no']; i++) {
        $('#progressbar li').eq(i).addClass("active");
    }
    $('#message_popup_text').text(data['msg'])
    $('#toast_body_alert').text(data['msg'])
    $('#toast_body_alert').css({ 'color': 'green' })
    $('#alert_show_button').click()
    $('#application_step').val(data['step_no'])
    $('#application_state').val(data['application_state'])
    // for final step
    if (!$('#final_confirmation_dropdpown').parents('div').hasClass('diable_header_tab')) {
        if ($('#application_state').val() == 'draft') {
            window.location.replace(window.location.href)
            return false
        }
    }
    $('#page_loader').hide()
}
$(":input").inputmask();

$(document).ready(function () {

    var color_scheme = $('#color_scheme').val()
    if ($('#application_step').val() == $('.header_tab').length) {
        $('.header_tab').last().click()
    }
    $('#close_popup_message').on('click', function () {
        $('#message_popup').hide();
    })
    $('.header_tab').each(function (index, element) {
        index += 1
        application_step = $('#application_step').val()
        if (index < application_step) {
            $(element).removeClass('diable_header_tab')
        }
        if (index == application_step) {
            $(element).removeClass('diable_header_tab')
            // $(element).click()
        }

        if (index > application_step) {
            return false;
        }
    })
    $('.header_tab').eq($('#application_step').val() - 1).click()
    // validate input that only enter keypress is character
    $('.validate_char').on('keypress', function (event) {
        return (event.charCode > 64 && event.charCode < 91) || (event.charCode > 96 && event.charCode < 123) || (event.charCode == 32)
    })
    $('.validate_number').on('keypress', function (event) {
        return (event.charCode >= 48 && event.charCode <= 57) || (event.charCode == 13) || (event.charCode == 46)
    })
    $('#program_transfer_request_form').on('submit', function (e) {
        e.preventDefault();
        // $('#ring1').show()

        var formData = new FormData();
        var form_data = $('#program_transfer_request_form').serializeArray();
        $.each(form_data, function (key, input) {
            formData.append(input.name, input.value);
        });
        formData.append('current_program', $('#current_selected_program').attr('program'))
        $('#page_loader').show()
        $.ajax({
            url: '/admission/application/save/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)

                prepare_next_step(data)
                // $('#page_loader').hide()

            },
            error: function (response) {
                data = JSON.parse(response)
                alert(data['msg'])
            }
        });
    })
    // merit
    $.get("/get/merit/",
        function (data, status) {
            data = JSON.parse(data)
            if (data['status'] == 'noerror') {
                merit_no = data['merit_no']
                score = data['score']
                aggregate = data['aggregate']
                $('#merit_no').val(merit_no)
                $('#merit_score').val(score)
                $('#merit_aggregate').val(aggregate)
            }

        },

    );
 
  
    $('.form-control').on('change', function () {
        $(this).css(`border-bottom ,2px solid ${color_scheme}`)
    })
    $('.collapse_div').each(function (index, element) {
        $(element).slideToggle('fast');
    });
    prepare_final_confirmation();

    listItems = $('#progressbar li')
  
    $('select').siblings('label').css({
        'top': '48px',
        'bottom': '-10px',
        'left': '18px',
        'font-size': '11px',
        'opacity': '0.7'
    })
    // floating label change css that is not required as its not handled by css
    $('.floating-label-norequired').siblings().each(function (index, el) {

        if ($(el).val() != '' || $(el).val().length > 0) {
            $(el).siblings('.floating-label-norequired').css({
                'top': '48px',
                'bottom': '-10px',
                'left': '18px',
                'font-size': '11px',
                'opacity': '0.7'
            })
        }
    })
    $('.floating-label-norequired').siblings('input').on('change', function () {
        var value = $(this).val();
        if (value.length > 0 || value.length != '') {
            $(this).siblings('.floating-label-norequired').css({
                'top': '48px',
                'bottom': '-10px',
                'left': '18px',
                'font-size': '11px',
                'opacity': '0.7'
            })
        }
        if (value.length < 1) {
            $(this).siblings('.floating-label-norequired').css({
                'position': 'absolute',
                'left': '25px',
                'top': '15px',
                // 'font-family': 'Verdana, Arial, Helvetica, sans-serif',
                'opacity': '0.2',
                'font-size': '13px',
                'transition': '0.2s ease all',
                'font-weight': '400',
                'pointer-events': 'none',
            })
        }
    });
    $('.form-control').each(function (index) {
        if ($(this).prop('required')) {
            $(this).css('border-bottom', `2px solid ${color_scheme}`)
        }
    })
    $('.form-control').on('keyup', function () {
        if ($(this).prop('required')) {
            $(this).css('border-bottom', `2px solid ${color_scheme}`)
        }
    })
    $('.form-control,select').each(function (index) {
        if ($(this).prop('required')) {
            $(this).css('border-bottom', `2px solid ${color_scheme}`)
        }
    })
    $('.form-control').on('change', function () {
        if ($(this).prop('required')) {
            $(this).css('border-bottom', `2px solid ${color_scheme}`)
        }
    })
    $(function () {
        $('#dashboard_button').children('div').css({ 'background-color': color_scheme })
        $('#application_update_alert').children('div').css({ 'background-color': color_scheme })
        $('button').css({ 'background-color': color_scheme });
        $('.toast-header').css({ 'background-color': color_scheme });
        $('#dashboard_button').css('cursor', 'pointer');
        $('#dashboard_button').on('click', function () {
            lca = '/admission/student/dashboard/';
            window.location.replace(lca)
        })

        $('#alert_show_button').on('click', function (e) {
            $('#application_update_alert').toast({
                delay: 4000,
            })
            $('#application_update_alert').toast('show')
        })

        $('#myToast').toast('show');
        $('#myToast').toast({
            autohide: false,
            delay: 10000,
        })
        $('#logout_toast').toast('show');
        $('#logout_toast').toast({
            autohide: false,
            delay: 10000,
        })

    })
    if ($('.diable_header_tab').length > 0) {
        last_tab = $('.header_tab:not(.diable_header_tab)').last().siblings('.collapse_div').attr('id')
        let pageBottom = document.querySelector("#" + last_tab)
        pageBottom.click()
        // pageBottom.scrollIntoView({})
    }
    $('#page_loader').hide()
});