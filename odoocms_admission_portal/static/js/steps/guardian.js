$(document).ready(function () {
    // Guardina Detail Form
    $('#guardian_relation').on('change', function () {
        selected = $(this).val()
        if (selected == 'brother' || selected == 'father' || selected == 'uncle') {
            $('#guardian_profession').find('option').each(function (index, element) {
                $(element).css({ 'display': '' })
                if ($(element).attr('apply_on') == 'f') {
                    $(element).css({ 'display': 'none' })
                }
            })
        } else if (selected == 'other') {
            $('#guardian_profession').find('option').each(function (index, element) {
                $(element).css({ 'display': '' })
            })
        } else {
            $('#guardian_profession').find('option').each(function (index, element) {
                $(element).css({ 'display': '' })
                if ($(element).attr('apply_on') == 'm') {
                    $(element).css({ 'display': 'none' })
                }
            })
        }

        if ($(this).val() == 'mother') {
            $('#guardian_name').val($('#mother_name').val())
            $('#guardian_cnic').val($('#mother_cnic').val())
            $('#guardian_cell').val($('#mother_cell').val())
            $('#guardian_profession').val($('#mother_profession option:selected').val())
            $('#guardian_education').val($('#mother_education option:selected').val())
            $('#guardian_cnic,#guardian_name,#guardian_cell').css({ 'pointer-events': 'none', 'background-color': 'white' })
            $('#guardian_cnic,#guardian_name,#guardian_cell,#guardian_education,#guardian_profession').attr('tabindex', '-1')
            $('#guardian_profession,#guardian_education').css({ 'pointer-events': 'none', 'background-color': 'white' })
            $('#guardian_cnic,#guardian_name,#guardian_cell,#guardian_profession,#guardian_education').removeAttr('required')


        }
        else if ($(this).val() == 'father') {
            $('#guardian_cnic,#guardian_name,#guardian_cell,#guardian_profession,#guardian_education').removeAttr('required')
            $('#guardian_cnic,guardian_name,guardian_cell,guardian_education,guardian_profession').attr('tabindex', '-1')
            $('#guardian_cnic,#guardian_name,#guardian_cell').css({ 'pointer-events': 'none', 'background-color': 'white' })
            $('#guardian_profession,#guardian_education').css({ 'pointer-events': 'none', 'background-color': 'white' })
            $('#guardian_profession').val($('#father_profession option:selected').val())
            $('#guardian_education').val($('#father_education option:selected').val())
            $('#guardian_name').val($('#father_name').val())
            $('#guardian_cnic').val($('#father_cnic').val())
            $('#guardian_cell').val($('#father_cell').val())
        }
        else {
            $('#guardian_cnic,#guardian_name,#guardian_cell,#guardian_education,#guardian_profession').css({ 'required': '1' })
            $('#guardian_cnic,#guardian_name,#guardian_cell,#guardian_education,#guardian_profession').css({ 'pointer-events': '' })
            $('#guardian_education,#guardian_profession,#guardian_name,#guardian_cnic,#guardian_cell').removeAttr('tabindex')
            $('#guardian_name,#guardian_cnic,#guardian_cell,#guardian_profession,#guardian_education').val('')
        }

    })
    $('#guardian_detail_form').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData();
        var form_data = $('#guardian_detail_form').serializeArray();
        $.each(form_data, function (key, input) {
            formData.append(input.name, input.value);
        });
        $('#page_loader').show();
        $.ajax({
            url: '/admission/application/save/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
            $('#page_loader').hide();
                data = JSON.parse(response)
                prepare_next_step(data)
            },
            error: function (response) {
                data = JSON.parse(response)
                alert(data['msg'])
            }
        });

    })
    $('#mother_status').on('change', function () {
        if ($('#mother_status option:selected').val() == 'alive') {
            $('#mother_status_div').show();
            $('#mother_status_div').find("div").show();
            $('#mother_cnic').attr('required', '1')
        } else {
            $('#mother_cnic').removeAttr('required')
            $('#mother_status_div').hide();
        }
    })
    $('#father_status').on('change', function () {
        if ($('#father_status option:selected').val() == 'alive') {
            $('#father_status_div').show();
            $('#father_status_div').find("div").show();
            $('#father_cnic').attr('required', '1')
        } else {
            $('#father_status_div').hide();
            $('#father_cnic').removeAttr('required')

        }
    })
});