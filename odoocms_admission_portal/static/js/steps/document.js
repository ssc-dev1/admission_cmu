
// this function is used to show document preview
function image_preview_func(input) {
    // this function is used for displaying fee voucher
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function (e) {
            $(input).siblings('img').attr('src', e.target.result);
        };
        reader.readAsDataURL(input.files[0]);
    }
}

$(document).ready(function () { 
    // document uploaed js
    $('#document_upload_form').on('submit', function (e) {
        e.preventDefault();
        var formData = new FormData();
        if (document.getElementById('cnic_front') != null) {
            formData.append('cnic_file', document.getElementById('cnic_front').files[0])
        }
        if (document.getElementById('cnic_back') != null) {
            formData.append('cnic_back_file', document.getElementById('cnic_back').files[0])
        }
        if (document.getElementById('domicile_file') != null) {
            formData.append('domicile_file', document.getElementById('domicile_file').files[0])
        }
        if (document.getElementById('pass_port') != null) {
            formData.append('passport', document.getElementById('pass_port').files[0])
        }
        formData.append('step_name', 'document')
        formData.append('step_no', $('#step_no_document').val())
        $('#page_loader').show();
        $.ajax({
            url: '/admission/application/save/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (data) {
            $('#page_loader').hide();
                data = JSON.parse(data);
                prepare_next_step(data)
            },
            error: function (response) {
                console.error(response);
            }
        });
    })
});