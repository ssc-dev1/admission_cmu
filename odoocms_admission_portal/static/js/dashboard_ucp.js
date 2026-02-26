$(document).ready(function () {
    /* ===== Dashboard viewport scaling ===== */
    /* Renders at a fixed 1920×1200 design size and scales down proportionally */
    function updateDashboardScale() {
        var wrapper = document.querySelector('.dashboard_main_wrapper');
        if (!wrapper) return;
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var scale = Math.min(1, vw / 1920, vh / 1200);
        wrapper.style.setProperty('--dashboard-scale', scale);
    }
    updateDashboardScale();
    $(window).on('resize', updateDashboardScale);

    /* Fallback for browsers that don't support :has() selector */
    if (document.querySelector('.dashboard_main_wrapper')) {
        document.documentElement.classList.add('has-dashboard-wrapper');
        document.body.classList.add('has-dashboard-wrapper');
    }

    $('#logout_button_dashboard').on('click', function (e) {
        e.preventDefault();
        let confirmAction = confirm("Are you sure you want to logout?");
        if (confirmAction) {
            let redirectUrl = '/web/session/logout?redirect=/web/signin/';
            window.location.replace(redirectUrl);
        }
    });

    $('#password, #password2').on('keyup', function () {
        let password = $('#password').val();
        let password2 = $('#password2').val();

        if (password === password2 && password.length >= 6) {
            $('#change_pass_form').removeAttr('disabled');
        } else {
            $('#change_pass_form').attr('disabled', 'disabled');
        }
    });

    $('#change_password_form').on('submit', function (e) {
        e.preventDefault();

        let password = $('#change_password_form').find('#password').val();
        let password2 = $('#change_password_form').find('#password2').val();

        if (password !== password2) {
            alert('Passwords do not match');
            return false;
        }

        if (password.length < 6) {
            alert('Password must be at least 6 characters');
            return false;
        }

        let data = {
            'password': password,
            'password2': password2,
        };

        $.post("/change/password", data, function (response) {
            try {
                let data = JSON.parse(response);
                if (data.status === 'noerror') {
                    alert(data.msg);
                    window.location.replace('/web/signin');
                } else {
                    console.error('Error:', data.msg);
                    alert('Error: ' + data.msg);
                }
            } catch (e) {
                console.error('Invalid response:', response);
                alert('An error occurred');
            }
        }).fail(function (error) {
            console.error('Request failed:', error);
            alert('Request failed. Please try again.');
        });
    });

    $('#pretest_dashboard_div').hide();

    $('#program_transfer_to').on('change', function () {
        let selectedOption = $('#program_transfer_to option:selected');
        let programPretest = selectedOption.attr('program_pretest');
        let pretestId = selectedOption.attr('program_pretest_id');

        if (programPretest !== 'no' && programPretest !== undefined && programPretest !== '') {
            $('#pretest_name_d').val(programPretest);
            $('#pretest_name_d').attr('pretest_id', pretestId);
            $('#pretest_dashboard_div').show();
        } else {
            $('#pretest_dashboard_div').hide();
            $('#pretest_name_d').val('');
            $('#pretest_name_d').removeAttr('pretest_id');
        }
    });

    $('#program_transfer_request').on('click', function (e) {
        e.preventDefault();

        if ($('#pretest_dashboard_div').is(":visible")) {
            let preTestMarks = $('#pre_test_marks_d').val();
            if (preTestMarks === '' || isNaN(preTestMarks) || parseFloat(preTestMarks) < 0) {
                alert('Please enter valid marks for Pre Test');
                return false;
            }
        }

        if ($('#pre_test_attachment_transfer').is(":visible")) {
            if ($('#pre_test_attachment_transfer').val() === '') {
                alert('Please upload the Result Card');
                return false;
            }
        }

        let programTransferFrom = $('#program_transfer_from').attr('program');
        let programTransferTo = $('#program_transfer_to').val();

        if (!programTransferFrom || programTransferFrom === '' || programTransferFrom === undefined) {
            alert('Please select a program to transfer from');
            return false;
        }

        if (!programTransferTo || programTransferTo === '' || programTransferTo === undefined) {
            alert('Please select a program to transfer to');
            return false;
        }

        let formData = new FormData();
        formData.append('program_transfer_from', programTransferFrom);
        formData.append('program_transfer_to', programTransferTo);

        if ($('#pretest_dashboard_div').is(":visible")) {
            let preTestFile = document.getElementById('pre_test_attachment_transfer');
            if (preTestFile && preTestFile.files.length > 0) {
                formData.append('pre_test_card', preTestFile.files[0]);
            }
            formData.append('pre_test_marks', $('#pre_test_marks_d').val());
            formData.append('pretest_id', $('#pretest_name_d').attr('pretest_id'));
        }

        $.ajax({
            url: '/program/transfer/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                try {
                    let data = JSON.parse(response);
                    if (data.status === 'noerror') {
                        alert('Request submitted successfully');
                        window.location.reload();
                    } else if (data.status === 'error') {
                        console.error('Error:', data.msg);
                        alert('Error: ' + data.msg);
                    }
                } catch (e) {
                    console.error('Invalid response:', response);
                    alert('An error occurred');
                }
            },
            error: function (error) {
                try {
                    let data = JSON.parse(error.responseText);
                    console.error('Request error:', data.msg);
                    alert('Error: ' + data.msg);
                } catch (e) {
                    console.error('Request failed:', error);
                    alert('Request failed. Please try again.');
                }
            }
        });
    });
});
