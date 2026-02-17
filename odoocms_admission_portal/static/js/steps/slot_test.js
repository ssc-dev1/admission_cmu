$(document).ready(function () {
    // testing center JS
    if ($('#test_center_skip').val() == 'yes') {
        $('#testing_center_update').text('Skip')
    }
    if ($('#test_center_skip').val() == 'no') {
        $('#testing_center_update').text('Update')
    }
    $('#test_center_id').on('change', function () {
        test_center_id = $("#test_center_id").val()
        var formData = new FormData();
        formData.append('test_center_id', test_center_id)
        $.ajax({
            url: "/test/slot/",
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            success: function (data) {
                data = JSON.parse(data)
                if (data['status'] == 'noerror') {
                    $("#test_center_slot").parent().show();

                    $("#test_center_slot").empty();
                    $("#test_center_slot").append(" <option selected='1' value='0'  >Select Test Center Slot </option>");
                    for (j = 0; j < data.slots_data.length; j++) {
                        $("#test_center_slot").append(" <option value=" + data.slots_data[j].id + " > " + data.slots_data[j].name + "</option>");
                    }
                    if (data.slots_data.length < 1) {

                        $("#test_center_slot").parent().hide();
                    }
                } else {
                    $("#test_center_slot").empty();
                    $("#test_center_slot").parents('div').hide();
                    $("#test_center_slot").append(" <option selected='1' disabled='1' value='0'+  >Select Test Center Slot </option>");
                }
            }
        });
    })
    $('#center_selection_form').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData();
        var form_data = $('#center_selection_form').serializeArray();
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
                prepare_next_step(data)
            },
            error: function (response) {
                console.error(response);
            }
        });
    })

});