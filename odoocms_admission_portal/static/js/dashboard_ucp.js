$(document).ready(function () {
    $('#logout_button_dashboard').on('click', function () {
        let confirmAction = confirm("Are you sure to Logout?");
        if (confirmAction) {
            lca = '/web/session/logout?redirect=/web/signin/';
            window.location.replace(lca)
        }
    })

    $('#password,#password2').on('keyup', function(){
            if ($('#password').val()==$('#password2').val() ){
                    $('#change_pass_form').removeAttr('disabled');
            }else{
                $('#change_pass_form').attr('disabled', '1');;
            }
    })  

    $('#change_password_form').on('submit', function(){
        pass=$('#change_password_form').find('#password').val()
        pass2=$('#change_password_form').find('#password2').val()
        data={
            'password':pass,
            'password2':pass2,
        }
        if(pass==pass2 ){
            $.post("/change/password", data,
            function (data, textStatus) {
                data=JSON.parse(data);
                if (data.status=='noerror'){
                    alert(data.msg);
                    window.location.replace('/web/signin')
                }else{
                    console.error(data.msg);
                }
                
            },
            
            );
        }
        
    });


    $('#pretest_dashboard_div').hide()
    $('#program_transfer_to').on('change', function () {
        if ($('#program_transfer_to option:selected').attr('program_pretest') != 'no' && $('#program_transfer_to option:selected').attr('program_pretest') != undefined && $('#program_transfer_to option:selected').attr('program_pretest') != '') {
            $('#pretest_name_d').val($('#program_transfer_to option:selected').attr('program_pretest'))
            $('#pretest_name_d').attr('pretest_id', $('#program_transfer_to option:selected').attr('program_pretest_id'))
            $('#pretest_dashboard_div').show();

        } else {
            $('#pretest_dashboard_div').hide();
            $('#pretest_name_d').val('')
            $('#pretest_name_d').removeAttr('pretest_id');

        }
    })
    $('#program_transfer_request').on('click', function () {

        if ($('#pretest_dashboard_div').is(":visible")) {
            if ($('#pre_test_marks_d').val() == '' || $('#pre_test_marks_d').val() < 0) {
                alert('Please Input Valid Marks For Pre Test')
                return false;
            }
        }

        if ($('#pre_test_attachment_transfer').is(":visible")) {
            if ($('#pre_test_attachment_transfer').val() == '') {
                alert('Please Upload Result Card')
                return false;
            }
        }

        program_transfer_from = $('#program_transfer_from').attr('program')
        program_transfer_to = $('#program_transfer_to').val()

        if (program_transfer_from == '' || program_transfer_from == undefined) {
            alert('Please Fill Required Fields')
            return false
        }
        if (program_transfer_to == '' || program_transfer_to == undefined) {
            alert('Please Fill Required Fields')
            return false
        }
        var formData = new FormData();
        formData.append('program_transfer_from', program_transfer_from)
        formData.append('program_transfer_to', program_transfer_to)
        if ($('#pretest_dashboard_div').is(":visible")) {
            var image = document.getElementById('pre_test_attachment_transfer')
            pre_test_card = image.files[0];
            pretest_id = $('#pretest_name_d').attr('pretest_id')
            formData.append('pre_test_marks', $('#pre_test_marks_d').val())
            formData.append('pre_test_card', pre_test_card)
            formData.append('pretest_id', pretest_id)
        }
        $.ajax({
            url: '/program/transfer/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)
                if (data['status'] == 'noerror') {
                    alert('Request Submitted')
                    window.location.reload()
                }
                if (data['status'] == 'error') {
                    console.error(data['msg'])
                }
            },
            error: function (response) {
                data = JSON.parse(response)
                alert(data['msg'])
            }
        });

    })
});