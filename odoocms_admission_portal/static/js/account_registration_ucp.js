
$(document).ready(function () {
    $('#page_loader').hide()
    $('#msg_btn').on('click', function () {
        $('#msg_alert').alert('close')
      })

    $('#signup_form').on('submit', function (e) {
        e.preventDefault();
        var form_data = $('#signup_form').serializeArray();
        const formData = new FormData();
        $.each(form_data, function (key, input) {
            formData.append(input.name, input.value);
        });
        $('#page_loader').show()
        $('#signup_submit').attr('disabled','1');

        $.ajax({
            url: '/web/admission/signup',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,

            success: function (response) {
            $('#page_loader').hide()
        $('#signup_submit').removeAttr('disabled')

                data = JSON.parse(response)
                if (data['error'] == 'email_error') {
                    alert('Email Already Registered')
                    $('#email_same_error').show();
                    $('#email_same_error').text('Email Already Registerd')
                }
                 else if (data['error'] == 'cnic_error') {
                    // window.location.reload();
                    alert(data['error_detail'])
                    $('#email_same_error').show();
                    $('#email_same_error').text(data['error_detail'])

                }
                else if (data['error'] == 'captcha_exp') {
                    // window.location.reload();
                    alert(data['error_detail'])
                    $('#email_same_error').show();
                    $('#email_same_error').text(data['error_detail'])
                    location.reload();

                }else if (data['error'] == 'noerror') {
                    localStorage.setItem('signup', 'yes');
                    window.location.replace('/thankyou/signup')
                    // window.location.reload();
                    // $('#signup_switch').click()
                    // $('#msg_alert').show();
                    // $('#msg_alert_text').text('Login Details Sent By Email and Message');
                } else {
                    $('#signin_message').hide();
                    $('#email_same_error').hide();
                    // console.log(data['error'])
                }

            },
        });

    })

    $('#phone_signup_international').hide();
    $('#country_id_signup').parent().parent().hide()

    
    $('#international_student').on('change', function () {
        const check_student = $('#international_student option:selected').val()
        if (check_student != '') {

            if (check_student == 'national') {
                $('#cnic').attr('required', '1')
                $('#cnic').parent().parent().show()
                $('#country_id_signup').parent().parent().hide()
                $('#country_id_signup').removeAttr('required');
                $('#phone_signup_international').hide()
                $('#phone_signup').show()
                $('#phone_signup').attr('required', '1')
            } else {
                $('#phone_signup').removeAttr('required')
                $('#cnic').removeAttr('required')
                $('#cnic').parent().parent().hide();
                $('#phone_signup_international').show()
                $('#phone_signup').hide()
                $('#country_id_signup').parent().parent().show();
                $('#country_id_signup').attr('required', '1');
                $('#country_id_signup').val('');
            }
        }
    })
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
    $('#signup_div').hide();
    $('#signup_image').hide();
    $('#signin_div').show();
    $('#signup_switch').on('click', function () {
       
        $('#signup_image').hide();
        $('#signin_image').show();
        $('#signup_div').hide();
        $('#signin_div').show();
        $('#title_sign').text('Admission Sign-In')
        
    });
    
    $('#title_sign').text('Admission Sign-In')
    $('#signin_switch').on('click', function () {
        $('#signin_image').hide();
        $('#signup_image').show();
        $('#signin_div').hide();
        $('#signin_div').hide();
        $('#title_sign').text('Admission Sign-Up')
        $('#signup_div').show();
      

    });
   
});

