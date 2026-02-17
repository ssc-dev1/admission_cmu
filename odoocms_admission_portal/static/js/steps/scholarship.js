// -------------------------------
// Need-Based Scholarship toggling
// -------------------------------
function toggleNeedBasedFields() {
    var checkbox = document.getElementById('need_based_scholarship_checkbox');
    var fieldsContainer = document.getElementById('need_based_fields_container');
    if (!checkbox || !fieldsContainer) return;

    var requiredFields = fieldsContainer.querySelectorAll('select, input[type="text"]');

    if (checkbox.checked) {
        fieldsContainer.style.display = 'block';
        requiredFields.forEach(function (field) {
            field.setAttribute('required', 'required');
        });
    } else {
        fieldsContainer.style.display = 'none';
        requiredFields.forEach(function (field) {
            field.removeAttribute('required');
            // Optional: clear values when hidden
            field.value = '';
        });
    }
}

// -------------------------------
// Document Ready
// -------------------------------
$(document).ready(function () {
    // Initial state (reflect server value rendered by t-att-checked)
    toggleNeedBasedFields();

    // Watch checkbox toggle
    $('#need_based_scholarship_checkbox').on('change', toggleNeedBasedFields);

    // Submit handler
    $('#scholarship_form').on('submit', function (e) {
        e.preventDefault();

        e.preventDefault();
        var formData = new FormData();

        // 1) Serialize form fields
        var form_array = $('#scholarship_form').serializeArray();

        // 1.a) Remove ANY accidental/legacy entries of the boolean
        // (handles cases where a hidden False input still exists in HTML)
        form_array = form_array.filter(function (item) {
            return item.name !== 'need_based_scholarship_applied';
        });

        // 1.b) Append all normal fields
        $.each(form_array, function (idx, input) {
            formData.append(input.name, input.value);
        });
        formData.append('step_name', 'document')
        formData.append('step_no', $('#step_no_document').val())
        console.log(formData)
        $('#page_loader').show()

        // 2) Append the SINGLE, authoritative boolean value
        var checkbox = document.getElementById('need_based_scholarship_checkbox');
        formData.append('need_based_scholarship_applied', (checkbox && checkbox.checked) ? 'True' : 'False');

        // 3) Optional file (if present)
        var pwwfInput = document.getElementById('pwwf_file');
        if (pwwfInput && pwwfInput.files && pwwfInput.files.length > 0) {
            formData.append('pwwf_file', pwwfInput.files[0]);
        }

        // 4) Meta
        formData.append('step_name', 'scholarship');
        formData.append('step_no', $('input[name="step_no"]').val());

        // 5) Submit
        $('#page_loader').show();
        $.ajax({
            url: '/admission/application/save/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                var data = JSON.parse(response);
                prepare_next_step(data);
            },
            error: function (response) {
                try {
                    var data = JSON.parse(response);
                    alert(data['msg'] || 'Error submitting form');
                } catch (e) {
                    alert('Error submitting form');
                }
            }
        });
    });


});

// -------------------------------
// PWWF helpers (unchanged)
// -------------------------------
var pwwfdescdoc = document.getElementById("pwwfdescdoc");
var pwwfdoc2 = document.getElementById("pwwfdoc2");
function pwwfdocument(param) {
    var pwwf_file = document.getElementById('pwwf_file');
    if (!pwwfdescdoc || !pwwfdoc2) return;
    if (param) {
        pwwfdescdoc.style.display = "block";
        pwwfdoc2.style.display = "block";
        if (pwwf_file) pwwf_file.setAttribute('required', 'required');
    } else {
        pwwfdescdoc.style.display = "none";
        pwwfdoc2.style.display = "none";
        if (pwwf_file) pwwf_file.removeAttribute('required');
    }
}
