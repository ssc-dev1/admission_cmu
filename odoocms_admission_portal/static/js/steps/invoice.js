function prepare_admission_fee_voucher() {
    $.get("/prepare/admission/invoice/",
        function (data, textStatus) {
            data = JSON.parse(data);
            if (data['error'] == 'unavailable') {
                $('#message_popup_text').text('Preference Programs Seat Not Available!')
                $('#toast_body_alert').text(data['msg'])
                $('#toast_body_alert').css({ 'color': 'red' })
                $('#alert_show_button').click()
                $('#fee_voucher_form').parent().hide();
                $('#fee_voucher_challan').hide();
                $('#fee_button').show()
            } else {
                $('#fee_voucher_state').val(data['fee_voucher_state'])
                $('#father_name_voucher').text(data['father_name']);
                $('#student_name_voucher').text(data['student_name']);
                $('#voucher_cnic').text(data['cnic']);
                account_payable = data['account_payable'] + ' or ' + data['account_payable2']
                $('#account_payable').text(account_payable);
                acount_title = data['account_title'] + ' or ' + data['account_title']
                $('#account_title').text(acount_title);
                account_no = data['account_no'] + ' or ' + data['account_no2']
                $('#account_no').text(account_no);
                if (data['is_dual_nationality']) {
                    application_fee_international_row = `<tr><th>Application Processing Fee</th><td> ${data['registration_fee_international']}<span>$</span></td></tr><tr><th>Total</th><td>${data['total_fee']}<span> $</span></td></tr>`
                    amount_in_word = data['total_fee_word_international'] + ' $'
                    $('#invoice-report').prepend(application_fee_international_row)
                    $('#amount_in_words').text(amount_in_word)
                } else {
                    application_fee_row = `<tr><th>Application Processing Fee</th><td>${data['registration_fee']}<span>PKR</span></td></tr><tr><th>Total</th><td>${data['total_fee']}<span> PKR</span></td></tr>`
                    amount_in_word = data['total_fee_word'] + ' PKR'
                    $('#invoice-report').prepend(application_fee_row)
                    $('#amount_in_words').text(amount_in_word)
                }
            }

        },
    );
}
$(document).ready(function () {
    if ($('#fee_voucher_state').val() != 'no') {
        prepare_admission_fee_voucher()
        $('#fee_button').hide()
    }
    if ($('#fee_voucher_state').val() == 'no') {
        $('#fee_voucher_form').parent().hide();
        $('#fee_voucher_challan').hide();
        $('#fee_button').show()
    }

    // ucp
    if ($('#fee_voucher_state_ucp').val() != 'no') {
        $('#fee_button').hide()
    }
    if ($('#fee_voucher_state_ucp').val() == 'no') {
        $('#fee_voucher_form').parent().hide();
        $('#fee_button').show()
    }
    $('#fee_button').on('click', function (e) {
        prepare_admission_fee_voucher()
        $('#fee_voucher_form').parent().show();
        $('#fee_voucher_challan').show();
        $('#fee_button').hide()
    });
  
    $('#fee_voucher_form_ucp').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData();
        formData.append('voucher_number', $('#voucher_number').val());
        formData.append('voucher_date', $('#deposit_date').val());
        formData.append('step_name', 'fee_voucher');
        formData.append('step_no', $('#step_no_voucher').val());
        var image = document.getElementById('fee_voucher_image')
        voucher_image = image.files[0];
        formData.append('voucher_image', voucher_image)
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
            }
        });

    });
    $('#fee_voucher_skip').on('click', function (e) {
        e.preventDefault();
        var formData = new FormData();
        formData.append('step_skip', 'yes');
        formData.append('step_name', 'fee_voucher');
        formData.append('step_no', $(this).siblings('input').val());
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
            },
            error: function (response) {
                console.error(response);
            }
        });
    });
});