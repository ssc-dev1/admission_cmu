function prepare_final_confirmation() {
    $('#final_confirmation_profile_pic').empty()
    $('#review_final').empty()
    $('#preference_testing').empty()
    $('#undertaking_div').empty()    
    $('.collapse_div').each(function (index, element) {
        index += 1
        element = $(element).find('.col-8').first().clone()
        if (index < $('.collapse_div').length - 1) {
            $('#final_confirmation_div').find('#review_final').append(element.html())
        }
    })
    $('#final_confirmation_div').find('#disciplicne_collapse').parent().remove()
    $('#final_confirmation_div').find('#preference_testing').append($('#admission_preference').find('.col-5').clone())
    $('#final_confirmation_div').find('#test_center_id').parent().find('label').removeAttr('style')
    $('#final_confirmation_profile_pic').append($('.circle_image').find('img').clone())
    $('#final_confirmation_profile_pic').find('img').css({ 'width': '250px', 'height': '250px', 'border-radius': '50%', 'border': ' 1px solid gray', })
    $('#final_confirmation_div').find('button').remove();
    
    if (!($('#final_confirmation_dropdpown').parents('div').hasClass('diable_header_tab'))) {
        if (($('#apply_final_application').length)) { } else {
            $('#agreement_terms').parent().show()
            apply_application_button = `<button  id='apply_final_application' onclick="apply_application()" style='border:None' class="btn btn-primary ml-1  mt-2 mb-5 px-5">Submit Application</button>`
            $('#apply_application_button_div').append(apply_application_button)
        }
    }
    $('#final_confirmation_div').find('a').remove();
    $('#final_confirmation_div').find('#required_document').show();
    $('#final_confirmation_div').find("input[type='file']").remove();
    $('#final_confirmation_div').find('#fee_voucher_form').remove();
    $('#final_confirmation_div').find('#fee_voucher_form_ucp').remove();
    $('#final_confirmation_div').find('#is_same_address').parent().remove();
    $('#final_confirmation_div').find('#document_upload_form').siblings('div').remove();
    $('#final_confirmation_div').find('#document_upload_form').find('img').parent().addClass('col-2');
    $('#final_confirmation_div').find('#document_upload_form').find('img').parent().removeClass('col-6');
    $('#final_confirmation_div').find('#education_table thead tr th').last().remove();
    $('#final_confirmation_div').css({ 'pointer-events': 'none', })
}

function apply_application() {
    let confirmAction = confirm("You Can Not Change Any Thing After Submit Application.");
    if (confirmAction) {
        $.get("/apply/application/",
            function (data, textStatus) {
                data = JSON.parse(data);
                if (data['status'] == 'noerror') {
                    $('#message_popup_text').text(data['msg'])
                    $('#toast_body_alert').text(data['msg'])
                    $('#toast_body_alert').css({ 'color': 'green' })
                    $('#alert_show_button').click()
                    // $('#message_popup').show()
                    $('#application_step').val(data['step_no'])
                    $('#application_state').val(data['application_state'])
                    prepare_next_step(data)
                    window.location.reload()
                } else {
                    $('#message_popup_text').text(data['msg'])
                    $('#toast_body_alert').text(data['msg'])
                    $('#toast_body_alert').css({ 'color': 'red' })
                    $('#alert_show_button').click()
                    $('#application_step').val(data['step_no'])
                    $('#application_state').val(data['application_state'])
                }
            },
        );
    }
}



$(document).ready(function () {


    $('#agreement_terms').parent().hide()
    $('#agreement_terms').on('change', function () {
        agreement = $('#agreement_terms').prop('checked')
        if (agreement == true) {
            $('#apply_application_button_div').show();
        } else {
            $('#apply_application_button_div').hide();

        }
    })

    prepare_final_confirmation();

    
});