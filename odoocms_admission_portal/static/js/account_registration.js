
$(document).ready(function () {

    $('#email_same_error').hide();
    $('#signin_message').hide();


    $('#signup_form').on('submit', function (e) {
        e.preventDefault();
        var form_data = $('#signup_form').serializeArray();
        const formData = new FormData();
        $.each(form_data, function (key, input) {
            formData.append(input.name, input.value);
        });

        $.ajax({
            url: '/web/admission/signup',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)
                if (data['error'] == 'email_error') {
                    $('#email_same_error').show();
                    $('#email_same_error').text('Email Already Registerd')
                } else if (data['error'] == 'noerror') {
                    // window.location.reload();
                    $('#signin_switch').click()
                    $('#signin_message').show();
                    $('#signin_message').text('Login Details Sent By Email and Message');
                }else if (data['error'] == 'captcha_exp') {
                    // window.location.reload();
                    alert(data['error_detail'])
                    $('#email_same_error').show();
                    $('#email_same_error').text(data['error_detail'])
                    location.reload();
            }else if (data['error'] == 'validation_error') {
                    // window.location.reload();
                    alert(data['error_detail'])
                    $('#email_same_error').show();
                    $('#email_same_error').text(data['error_detail'])
                    location.reload();
                } else {
                    $('#signin_message').hide();
                    $('#email_same_error').hide();
                    // console.log(data['error'])
                }

            },
        });

    })

    $('#phone_signup_international').hide();
    $('#country_id_signup').parent().hide()

    $('#country_id_signup').on('change', function () {
        const selected_country = $('#country_id_signup option:selected').val()
        const phone_code = $('#country_id_signup option:selected').attr('phone_code')
        $('#phone_signup_international').val(phone_code)
        if (parseInt(selected_country) == 177) {
            $('#phone_signup').show()
            $('#phone_signup').attr('required', '1')
            $('#phone_signup_international').hide()
            $('#international_student').val('national')
            $('#country_id_signup').parent().hide()
            return false;
        }
        $('#phone_signup_international').show()
        $('#phone_signup').hide()
        $('#phone_signup').removeAttr('required')


    })
    $('#international_student').on('change', function () {
        const check_student = $('#international_student option:selected').val()
        if (check_student != '') {

            if (check_student == 'national') {
                $('#cnic').attr('required', '1')
                $('#cnic').show()
                $('#country_id_signup').parent().hide()
                $('#country_id_signup').removeAttr('required');
                $('#phone_signup_international').hide()
                $('#phone_signup').show()
                $('#phone_signup').attr('required', '1')




            } else {
                $('#phone_signup').removeAttr('required')
                $('#cnic').removeAttr('required')
                $('#cnic').hide();
                $('#phone_signup_international').show()
                $('#phone_signup').hide()
                $('#country_id_signup').parent().show();
                $('#country_id_signup').attr('required', '1');
                $('#country_id_signup').val('');
            }
        }
    })
    $('#signup_switch').on('click', function () {
        $('#signup_form').show();
        $('#signin_form').hide();
        $('#signup_switch').hide();
        $('#reset_switch').hide();
        $('#signin_switch').show();

    });
    $('#signin_switch').on('click', function () {
        $('#signup_form').hide();
        $('#signin_form').show();
        $('#signup_switch').show();
        $('#reset_switch').show();
        $('#signin_switch').hide();

    });
    $('#myTab').on('click', function () {
        if ($('#signup').is(":visible")) {
            $('#signup').hide()
            $('#signin').show()
        } else {
            $('#signup').show()
            $('#signin').hide()
        }
        $('#myTab li').each(function (index, element) {
            $(element).find('a').toggleClass('active', '');

        })
    })
});

