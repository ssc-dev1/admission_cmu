$(document).ready(function () {

    if (parseInt($('#country_id option:selected').attr('value')) == 177) {
        $('#city_national_div').show()
        $('#city_foreign_div').hide()
    } else {
        $('#city_foreign_div').show()
        $('#city_national_div').hide()
    }
    $('#country_id').on('change', function () {
        if (parseInt($('#country_id option:selected').attr('value')) == 177) {
            $('#city_national_div').show()
            $('#city_foreign_div').hide()
        } else {
            $('#city_foreign_div').show()
            $('#city_national_div').hide()
        }
    })

    if (parseInt($('#per_country_id option:selected').attr('value')) == 177) {
        $('#city_national_perm_div').show()
        $('#city_foreign_perm_div').hide()
    } else {
        $('#city_foreign_perm_div').show()
        $('#city_national_perm_div').hide()
    }
    $('#per_country_id').on('change', function () {
        if (parseInt($('#per_country_id option:selected').attr('value')) == 177) {
            $('#city_national_perm_div').show()
            $('#city_foreign_perm_div').hide()
        } else {
            $('#city_foreign_perm_div').show()
            $('#city_national_perm_div').hide()
        }
    })
    $("#per_domicile").empty()
    $('#per_province').on('change', function () {
        province_id = $("#per_province").val()
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
                $("#per_domicile").empty();
                for (j = 0; j < data.domiciles.length; j++) {
                    $("#per_domicile").append(" <option value=" + data.domiciles[j].id + " > " + data.domiciles[j].name + "</option>");
                }
            }
        });
    })
    $('#is_same_address').on('change', function () {
        if ($('#is_same_address').prop('checked') == true) {
            $('#per_country_id').val($('#country_id').val());
            if ($('#country_id').val() == 177) {
                $('#per_city').val($('#city :selected').val());
            } else {
                $('#per_city_foreign').val($('#city_foreign').val());
            }
            $('#per_street').val($('#street').val());
            $('#per_street2').val($('#street2').val());
            $('#per_zip').val($('#zip').val());
        } else {
            $('#per_country').val('');
            $('#per_city_foreign').val('');
            $('#per_city').val('');
            $('#per_street').val('');
            $('#per_street2').val('');
            $('#per_zip').val('');
        }

        if ($('#country_id option:selected').attr('value') == 177) {
            $('#city_national_div').show()
            $('#city_foreign_div').hide()
        } else {
            $('#city_foreign_div').show()
            $('#city_national_div').hide()
        }

        if (parseInt($('#per_country_id option:selected').attr('value')) == 177) {
            $('#city_national_perm_div').show()
            $('#city_foreign_perm_div').hide()
        } else {
            $('#city_foreign_perm_div').show()
            $('#city_national_perm_div').hide()
        }
    })

    $('#contact_detail_form').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData();
        var form_data = $('#contact_detail_form').serializeArray();
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
                if (data['status'] == 'noerror') {
                    prepare_next_step(data);
                } else {
                    console.error(data['msg']);
                }
            },
            error: function (response) {
                console.error(response)
            }
        });
    })
});