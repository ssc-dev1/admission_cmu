// change profile image from backend as well as frontend
function profileImageUpdate(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function (e) {
            $('#profile_image_preview').attr('src', e.target.result);
        };
        reader.readAsDataURL(input.files[0]);
        formData = new FormData();
        var profile_image = document.getElementById('profile_image')
        image_file = profile_image.files[0];
        formData.append('image_file', image_file)
        $.ajax({
            url: '/profile/image/update/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)
                if (data['status'] == 'noerror') {
                    $('#profile_image_checked').attr('checked', true);
                }
                $('#message_popup_text').text(data['msg'])
                $('#toast_body_alert').text(data['msg'])
                $('#toast_body_alert').css({ 'color': 'green' })
                $('#alert_show_button').click();
            },
            error: function (response) {
                console.error(response)
            }
        });
    }
}


$(document).ready(function () {
    // Personal detail Form js
    $('#province2_div').hide();
    if ($('#domicile_id :selected').val() == '0') {
        $('#domicile_id').empty()
        $("#domicile_id").append(" <option value='0'+ >Select Domicile </option>");
    }
    $('#program_migration').on('change', function () {
        if ($('#program_migration').prop('checked') == true) {
            $('#migration_detail_div').show();
            $('#migration_detail_div').find("div").show();
            $('#migration_semester_div').show();
            $('#migration_last_obtained_cgpa_div').show();
            $('#migration_type').attr('required', '1')
            $('#last_studied_semester').attr('required', '1')
            $('#last_obtained_cgpa').attr('required', '1')
        } else {
        
            $('#migration_detail_div').hide();
            $('#migration_detail_div').find("div").hide();
            $('#migration_last_obtained_cgpa_div').hide();
            $('#migration_semester_div').hide();
            $('#migration_type').removeAttr('required')

            $('#last_studied_semester').removeAttr('required')
            $('#last_obtained_cgpa').removeAttr('required')
            $('#migration_university').removeAttr('required')
            $('#migration_registration_div').hide();
            $('#migration_university_div').hide();
            $('#migration_university').removeAttr('required')
            $('#current_registration_no').removeAttr('required');

        }
    })
    $('#migration_type').on('change', function () {
        if ($('#migration_type :selected').val() == 'other_university') {

            $('#migration_university_div').show();
            $('#migration_university_div').find("div").show();
            $('#migration_registration_div').hide();
            $('#current_registration_no').removeAttr('required');

            $('#migration_university').attr('required', '1')
            $('#last_studied_semester').attr('required', '1')
            $('#last_obtained_cgpa').attr('required', '1')

        } else {
            $('#migration_university_div').hide();
             $('#migration_university').removeAttr('required')
            $('#migration_registration_div').show();
             $('#current_registration_no').attr('required', '1')
            $('#last_studied_semester').attr('required', '1')
            $('#last_obtained_cgpa').attr('required', '1')


        }
    })
    $('#nationality').on('change', function () {
        if ($('#nationality :selected').val() == '0') {
            $('#province_div,#passport_div,#cnic_div,#province2_div,#domicile_div').hide();
        }
        if ($('#nationality :selected').val() == '177') {
            $('#province2_div,#passport_div').hide();
            $('#province_div,#domicile_div,#cnic_div').show();
        } else {
            $('#cnic_div,#domicile_div,#province_div').hide();
            $('#passport_div,#province2_div').show();
        }
    });
    if ($('#nationality :selected').val() == '177') {
        $('#province2_div,#passport_div').hide();
        $('#province_div,#cnic_div,#domicile_div').show();

    } else {
        $('#cnic_div,#domicile_div,#province_div').hide();
        $('#passport_div,#province2_div').show();
    }
    if ($('#nationality :selected').val() == '0') {
        $('#province_div,#passport_div,#cnic_div,#province2_div,#domicile_div').hide();
    }
    $('#province_id').on('change', function () {
        province_id = $("#province_id").val()
        var formData = new FormData();
        formData.append('province_id', province_id)
        $.ajax({
            url: "/province/domicile/",
            type: "POST",
            dataType: "json",
            data: formData,
            contentType: false,
            processData: false,
            success: function (data) {
                $("#domicile_id").empty();
                $("#domicile_id").append(" <option selected='1' value='0'+  >Select Domicile </option>");
                for (j = 0; j < data.domiciles.length; j++) {
                    $("#domicile_id").append(" <option value=" + data.domiciles[j].id + " > " + data.domiciles[j].name + "</option>");
                }
            }
        });
    })
    $('#personal_detail_form').on('submit', function (e) {
        e.preventDefault();

        //  if image not upload return error
        if (!$('#profile_image_checked').prop('checked')) {
            $('#message_popup_text').text('Please Update Profile Image!')
            $('#toast_body_alert').text('Please Update Profile Image!')
            $('#toast_body_alert').css({ 'color': 'red' })
            $('#alert_show_button').click()
            return false;
        }
        //  if dob not update return
        if ($('#personal_detail_form').find('#date_of_birth').val().length < 4) {
            $('#date_of_birth').css("border-bottom", "2px solid red")
            $('#date_of_birth').focus()
            return false
        }
        date_of_birth = $('#personal_detail_form').find('#date_of_birth').val()

        var formData = new FormData();
        var form_data = $('#personal_detail_form').serializeArray();
        $.each(form_data, function (key, input) {
            formData.append(input.name, input.value);
        });
        $('#page_loader').show()
        $.ajax({
            url: '/admission/application/save/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)
                if (data['status'] == 'noerror'){   
                    prepare_next_step(data)
                }else{
                    console.error(data['msg'])
                }
            },
        });
    })

    $(function () {

        $("#date_of_birth").datepicker({
            changeMonth: true,
            changeYear: true,
            yearRange: '1900:2050',
            maxDate: new Date($('#dob_min').val()),
            minDate: new Date($('#dob_max').val()),
            // dateFormat: 'yyyy-mm-dd',    
            onSelect: function (date) {
                $("#date_of_birth").attr('value', date)
            },
        })
    });


      // change the floating label of no required fields as those fields are not changed by default css
      $('#date_of_birth').on('change', function (e) {
        $('#date_of_birth').siblings().css({
            'top': '48px',
            'bottom': '-10px',
            'left': '18px',
            'font-size': '11px',
            'opacity': '0.7'
        })
    })
    $('#date_of_birth').siblings().css({
        'top': '48px',
        'bottom': '-10px',
        'left': '18px',
        'font-size': '11px',
        'opacity': '0.7'
    })

});