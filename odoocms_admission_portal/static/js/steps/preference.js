function clearShiftSelect() {
    var sel = document.getElementById('shift_choice');
    if (!sel) return;
    sel.innerHTML = '<option value="">Select Shift</option>';
}

function hideShiftContainer() {
    var cont = document.getElementById('shift_container');
    if (cont) cont.style.display = 'none';
}

function showShiftContainer() {
    var cont = document.getElementById('shift_container');
    if (cont) cont.style.display = '';
}

function loadShiftsForProgram(programId) {
    debugger;
    var savedShift = $('#saved_shift_value').val() || ""; 

    clearShiftSelect();

    if (!programId) {
        if (savedShift) {
            var sel = document.getElementById('shift_choice');
            var opt = document.createElement('option');
            opt.value = savedShift;
            opt.text = savedShift.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            opt.selected = true;
            sel.appendChild(opt);
        }
        return;
    }

    fetch('/program/' + programId + '/enabled_shifts', {
        method: 'GET',
        credentials: 'include'
    })
    .then(res => res.json())
    .then(function (data) {
        var sel = document.getElementById('shift_choice');
        clearShiftSelect();

        if (data && data.success && data.shifts.length) {
            data.shifts.forEach(function (s) {
                var opt = document.createElement('option');
                opt.value = s.value;
                opt.text = s.label;
                sel.appendChild(opt);
            });

            if (savedShift) sel.value = savedShift;
            showShiftContainer();
        } else {
            // No shifts available from backend
            if (savedShift) {
                // Call backend to remove saved shift for this applicant
                $.ajax({
                    url: '/remove/saved_shift/',   // Adjust to your actual endpoint
                    type: 'POST',
                    data: { shift_value: savedShift, program_id: programId },
                    success: function(resp) {
                        console.log('Saved shift removed on backend', resp);
                        $('#saved_shift_value').val(''); // clear the saved shift locally
                    },
                    error: function(err) {
                        console.error('Failed to remove saved shift', err);
                    }
                });
            }
            hideShiftContainer();
        }
    })
    .catch(function () {
        if (savedShift) {
            var sel = document.getElementById('shift_choice');
            var opt = document.createElement('option');
            opt.value = savedShift;
            opt.text = savedShift.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            opt.selected = true;
            sel.appendChild(opt);
            showShiftContainer();
        } else {
            hideShiftContainer();
        }
    });
}


// ---------- HELPER: GET FIRST PREFERENCE ----------
function getFirstPreferenceLi() {
    let firstLi = $('#sortable_program_list').find('li.program_count').first();
    if (firstLi.length) return firstLi;

    let fallbackLi = $('#prefer_div_already').find('li.program_count').first();
    if (fallbackLi.length) return fallbackLi;

    return null;
}

function initTestCenterNoteHandler() {
    debugger;
    const select = document.getElementById('test_center_id');
    const noteDiv = document.getElementById('test_center_note');
  
    if (!select || !noteDiv) return;
  
    select.addEventListener('change', function () {
      const selectedOption = this.options[this.selectedIndex];
      const note = selectedOption.getAttribute('data-note');
  
      noteDiv.textContent = note && note.trim() !== '' ? "Note: " + note : '';
    });
    select.dispatchEvent(new Event('change'));
  }
  document.addEventListener('DOMContentLoaded', initTestCenterNoteHandler);


  function updatePreTestState() {
    debugger;
    let count = 1;
    let listItems = $('#sortable_program_list').find('li');

    listItems.each(function (index, element) {
        $(element).find('.count_preference').text(count);
        count += 1;
    });

    let firstItem = listItems.first();
    if (!firstItem.length) {
        $('#pretest_div').hide();
        $('#pretest_check').prop('disabled', false).prop('checked', false);
        $('#checked_prestest').parent().hide();
        $('#pre_test_marks_input').hide();
        $('#pre_test_marks').removeAttr('required').val('');
        return;
    }

    let preTestName = firstItem.attr('pretest_name');
    let isCompulsory = firstItem.attr('compulsory') === 'true';
    let ids = firstItem.attr('pretest_id').split(",");
    let names = preTestName.split(",");

    if (preTestName !== 'no_pretest') {
        $('#pretest_div').show();
        let selectElem = $('#pretest_div').find('select');
        selectElem.empty();
        names.forEach((name, index) => {
            selectElem.append(`<option value="${ids[index]}">${name}</option>`);
        });

        if (isCompulsory) {
            $('#pretest_check').prop('disabled', true).prop('checked', true);
            $('#checked_prestest').parent().show();
            $('#pre_test_marks_input').show();
            $('#pre_test_marks').attr('required', '1');
        } else {
            $('#pretest_check').prop('disabled', false).prop('checked', false);
            $('#checked_prestest').parent().hide();
            $('#pre_test_marks_input').hide();
            $('#pre_test_marks').removeAttr('required').val('');
        }
    } else {
        $('#pretest_div').hide();
        $('#pretest_check').prop('disabled', false).prop('checked', false);
        $('#checked_prestest').parent().hide();
        $('#pre_test_marks_input').hide();
        $('#pre_test_marks').removeAttr('required').val('');
    }
}


function add_preference(param) {
    debugger;
    $('#drag_message').show();
    if ($('#prefer_div_already').find('li').length >= 1) {
        $('#sortable_program_list').append($('#prefer_div_already').find('li'));
        $('#prefer_div_already').find('li').remove();
    }
    count = $('.program_count').length + 1
    let preferenceTestId = $(param).attr('pretest_id')
    let preTestName = `${$(param).attr('pretest_name')}`
    let isCompulsory = $(param).attr('compulsory') === 'true';

    item = `<li id = '${$(param).attr('id')}' pretest_id=${$(param).attr('pretest_id').split(",")} pretest_name='${preTestName}' compulsory='${isCompulsory}'  class='list-group-item d-flex justify-content-between align-items-start border program_count ' ><div><i class="fas fa-expand-arrows-alt mr-1"></i>${$(param).text()}</div><div ><span class='badge badge-primary badge-pill count_preference color_scheme_class'>${count}</span> <span onclick='delete_preference(this)' class='delete_preference'>  <i class="fas fa-trash-alt ml-1"></i></span></div></ > `
    var item_id = $(param).attr('id')
    $("#sortable_program_list li").each(function (index, element) {
        if ($(element).attr('id') == item_id) {
            item_id = false;
        }
    })
    if (item_id != false) {
        $('#sortable_program_list').append(item)
        $('.preference_input_no:visible').first().hide()
        if ($('#sortable_program_list').find('li').length >= $('#preference_allowed').val()) {
            $('#view_offered_program_button').click()
            $('#view_offered_program_button').css({ 'pointer-events': 'none' })
            $('#view_offered_program_button').attr('disabled', '1');
        }
    }
    if (preTestName != 'no_pretest' && $('#sortable_program_list').find('li').length < 2) {
        $('#pretest_div').show();
        var pretest_name =preTestName.split(",")
        $('#pretest_div').find('select').empty()
        $(pretest_name).each(function(index,el){
        ids=$(param).attr('pretest_id').split(",")
        option = `<option  value='${ids[index]}'>${el}</option>`
        $('#pretest_div').find('select').append(option)
        })
        if (isCompulsory) {
            $('#pretest_check').prop('disabled', true); 
            $('#pretest_check').prop('checked', true);
            $('#pre_test_marks').attr('requied', '1')
            $('#pre_test_marks_input').show();
            $('#checked_prestest').parent().show();
        } else {
            $('#pretest_check').prop('disabled', false); 
            $('#pretest_check').prop('checked', false); 
            $('#checked_prestest').parent().hide();
            $('#pre_test_marks').removeAttr('required')
            $('#pre_test_marks_input').hide();
            $('#pre_test_marks').val('')
        }    
    }
    if (preTestName == 'no_pretest' && $('#sortable_program_list').find('li').length < 2) {
        $('#pretest_div').hide();
    }
    $('#sortable_program_list').find('li').find('.count_preference').each(function (index, element) {
        index = index + 1
        $(element).text(index)
    })
    // updatePreTestState();
    var first_li = getFirstPreferenceLi();
    if (first_li) loadShiftsForProgram(first_li.attr('id'));
    else { clearShiftSelect(); hideShiftContainer(); }}

// change preference from backend
function delete_preference(param) {
    debugger;
    $(param).parents('li').remove()
    $('.preference_input_no').not(':visible').last().show()
    count = 1
    $('.program_count').each(function (index, element) {
        $(element).find('.count_preference').text(count);
        if ($('#sortable_program_list').find('li').length == 1) {
            if (count == 1) {
                let preferenceTestId = $(element).attr('pretest_id');
                let preTestName = `${$(element).attr('pretest_name')}`;
                let isCompulsory = $(element).attr('compulsory') == 'true';
            
                if (preTestName != 'no_pretest') {
                    $('#pretest_div').show();
                    var pretest_name = preTestName.split(",");
                    $('#pretest_div').find('select').empty();
            
                    let ids = $(element).attr('pretest_id').split(",");
                    $(pretest_name).each(function(index, el) {
                        let option = `<option value='${ids[index]}'>${el}</option>`;
                        $('#pretest_div').find('select').append(option);
                    });
            
                    if (isCompulsory) {
                        $('#pretest_check').prop('disabled', true);
                        $('#pretest_check').prop('checked', true);
                        $('#pre_test_marks').attr('required', '1');
                        $('#pre_test_marks_input').show();
                        $('#checked_prestest').parent().show();
                    } else {
                        $('#pretest_check').prop('disabled', false);
                        $('#pretest_check').prop('checked', false);
                        $('#checked_prestest').parent().hide();
                        $('#pre_test_marks').removeAttr('required');
                        $('#pre_test_marks_input').hide();
                        $('#pre_test_marks').val('');
                    }
            
                } else {
                    $('#pretest_div').hide();
                    $('#pretest_check').prop('disabled', false);
                    $('#pretest_check').prop('checked', false);
                    $('#checked_prestest').parent().hide();
                    $('#pre_test_marks').removeAttr('required');
                    $('#pre_test_marks_input').hide();
                    $('#pre_test_marks').val('');
                }
            }
        }
        count += 1
    })

    if ($('#sortable_program_list').find('li').length >= $('#preference_allowed').val()) {
        $('#view_offered_program_button').click()
        $('#view_offered_program_button').css({ 'pointer-events': 'none' })
        $('#view_offered_program_button').attr('disabled', '1');
    }
    if ($('#sortable_program_list').find('li').length < $('#preference_allowed').val()) {
        document.getElementById('view_offered_program_button').style.removeProperty('pointer-events')
        $('#view_offered_program_button').css({ 'pointer-events': '' })
        $('#view_offered_program_button').removeAttr('disabled');
    }
    if ($('#sortable_program_list').find('li').length < 1) {
        $('#pretest_div').hide();

    }
    updatePreTestState();
    var first_li = getFirstPreferenceLi();
    if (first_li) loadShiftsForProgram(first_li.attr('id'));
    else { clearShiftSelect(); hideShiftContainer(); }
}

// change profile image from backend as well as frontend
function StatementOfPurpose(input) {
    if (input.files) {
        formData = new FormData();
        var statement_purpose = document.getElementById('statement_purpose')
        statement_purpose_file = statement_purpose.files[0];
        formData.append('statement_purpose', statement_purpose_file)
        $.ajax({
            url: '/statement/purpose/update/',
            type: 'POST',
            contentType: false,
            processData: false,
            data: formData,
            success: function (response) {
                data = JSON.parse(response)
                // if (data['status'] == 'noerror') {
                //     // $('#statement_purpose_file').attr('checked', true);
                // }
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

    $('body').click(function(event) {
        // Check if the clicked element is not a button
        if (!$(event.target).is('.list-group-item')) {

        }
    });
 
    $('#pretest_check').on('change', function () {
        if ($('#pretest_check').prop('checked')) {
            $('#pre_test_marks').attr('requied', '1')
            $('#pre_test_marks_input').show();
            $('#checked_prestest').parent().show();
        } else {
            $('#checked_prestest').parent().hide();
            $('#pre_test_marks').removeAttr('required')
            $('#pre_test_marks_input').hide();
            $('#pre_test_marks').val('')

        }
    })

    $('#view_offered_program_button').on('click', function () {
        $('#program_div').empty()
        $('#discipline_list').empty()
        $.get("/prepare/preference/",
            function (data, status) {
                debugger;
                data = JSON.parse(data)
                var preferencePreTest = data['pretest']
                if (data['status'] == 'noerror') {
                    program_offered = data['program_offered']
                    program_offered_items = ``
                    for (const program in program_offered) {
                        pretest_program = preferencePreTest[program];
                        let pretest_list = [];
                        let pretest_list_name = [];
                        let pretest_compulsory = [];
                        
                        if (Array.isArray(pretest_program)) {
                            pretest_program.forEach((test) => {
                                pretest_list.push(test.id);
                                pretest_list_name.push(test.name);
                                pretest_compulsory.push(test.compulsory);
                            });
                        
                            program_offered_items += `<li 
                                id='${program}' 
                                pretest_id='${pretest_list.join(",")}' 
                                pretest_name='${pretest_list_name.join(",")}' 
                                compulsory='${pretest_compulsory.includes(true)}' 
                                onclick='add_preference(this)' 
                                class="list-group-item">
                                    ${program_offered[program]}
                                </li>`;
                        } else {
                            program_offered_items += `<li 
                                id='${program}' 
                                pretest_id='${program}' 
                                pretest_name='no_pretest'  
                                onclick='add_preference(this)' 
                                class="list-group-item">
                                    ${program_offered[program]}
                                </li>`;
                        }
                    }
                    program_offered_div = `<div  class="col-8 ml-0 mt-3">
                    <ul class="list-group">
                      <li style='color:whitesmoke;pointer-events:none' class="list-group-item color_scheme_class">Add Program </li>
                      ${program_offered_items}
                    </ul>
                  </div>`
                    $('#program_div').append(program_offered_div)
                    $('#program_div').show();
                } else {
                    debugger
                    if (data['error']=='age_error'){

                        $('#message_popup_text').text('As Per Our Admission Age Criteria You Are Not Eligible To Any Program!')
                        $('#toast_body_alert').text('As Per Our Admission Age Criteria You Are Not Eligible To Any Program!')
                        $('#toast_body_alert').css({ 'color': 'red' })
                        $('#alert_show_button').click();

                    }else{
                        console.error(data['error'])
                    }
                }

            },
        );
    })


   
    
    // $('#request_prog_trans_header_tab').on('click', function () {
    //     $('#new_selected_program').empty()
    //     $('#new_selected_program').append(`<option selected='1' disabled='1' value=''>Select New Program</option>`)
    //     $('#sortable_program_list li').each(function (index, element) {
    //         value = $(element).attr('id')
    //         text = $(element).text()
    //         $('#new_selected_program').append(`<option value='${value}'>${text}</option>`)
    //     })
    // })
    $('#discipline_list').find('li').on('click', function (e) {
        elem = $('#program_div').find("[code='" + $(this).attr('code') + "']");
        $('#program_div div').hide()
        $(elem).show();
    })
    $('#preference_update').on('click', function (e) {
        if ($('#checked_prestest').val() != 1 && $('#pretest_check').prop('checked')) {
            $('#message_popup_text').text('Please Upload Pretest Result Card!')
            $('#toast_body_alert').text('Upload Result Card!')
            $('#toast_body_alert').css({ 'color': 'red' })
            $('#alert_show_button').click()
            return false
        }
        let shiftContainer = $('#shift_container');
        let shiftChoice = $('#shift_choice').val();
    
        if (shiftContainer.is(':visible')) {
            if (!shiftChoice || shiftChoice === "") {
                $('#message_popup_text').text('Please select a shift for your selected program!');
                $('#toast_body_alert').text('Shift selection required!');
                $('#toast_body_alert').css({ 'color': 'red' });
                $('#alert_show_button').click();
                return false;
            }
        }
        if ($('#sortable_program_list li').length < 1) {
            $('#message_popup_text').text('Please Select At Least One Preference!')
            $('#toast_body_alert').text('Select Preference!')
            $('#toast_body_alert').css({ 'color': 'red' })
            $('#alert_show_button').click()
            return false
        }
        if ($('#pretest_check').prop('checked') && $('#pre_test_marks').val() == '') {
            $('#message_popup_text').text('Please Enter Pre Test Marks!')
            $('#toast_body_alert').text('Enter Test Marks!')
            $('#toast_body_alert').css({ 'color': 'red' })
            $('#alert_show_button').click()
            return false
        }
        var formData = new FormData();
        step_preference_no = $('#step_preference_no').val()
        step_preference_name = $('#step_preference_name').val()
        if ($('#pretest_check').prop('checked')) {
            pre_test_marks = $('#pre_test_marks').val()
            pre_test_id = $('#pretest').val()
        } else {
            pre_test_marks = '';
            pre_test_id = '';

        }
        if ($('#test_center_div').is(':visible')) {
            test_center = $('#test_center_id').val()
        }else {
            test_center=1;
        }
        formData.append('pre_test_marks', pre_test_marks)
        formData.append('pre_test_id', pre_test_id)
        var pre_test_attachment_file = ''
        if ($('#pre_test_attachment').parent().is(":visible")) {
            var pre_test_attachment = document.getElementById('pre_test_attachment')
            pre_test_attachment_file = pre_test_attachment.files[0];
        }
        formData.append('pre_test_attachment', pre_test_attachment_file)
        formData.append('step_name', step_preference_name)
        formData.append('step_no', step_preference_no)
        formData.append('test_center_id',test_center)
        var selected_shift = $('#shift_choice').length ? $('#shift_choice').val() : '';
        formData.append('shift_choice', selected_shift || '');
        $('#sortable_program_list li').each(function (index, element) {
            preference = index + 1
            program_id = $(element).attr('id');
            formData.append(preference, program_id)
        });
        $('#page_loader').show()
        $.ajax({
            url: "/admission/application/save/",
            type: "POST",
            data: formData,
            contentType: false,
            processData: false,
            success: function (data) {
                data = JSON.parse(data);
                prepare_next_step(data)
            }
        })

    })
    $(function () {
        debugger;
        $("#sortable_program_list").sortable({
            update: function () {
                var count = 1
                $('.program_count').each(function (index, element) {
                    $(element).find('.count_preference').text(count);
                    if (count == 1) {
                        elem = $('#sortable_program_list').find('li').first()
                        let preferenceTestId = $(elem).attr('pretest_id')
                        let preTestName = `${$(elem).attr('pretest_name')}`
                        if (preTestName != 'no_pretest') {
                           $('#pretest_div').show();
        var pretest_name =preTestName.split(",")
        $('#pretest_div').find('select').empty()
        $(pretest_name).each(function(index,el){
        ids= $(elem).attr('pretest_id').split(",")
        option = `<option  value='${ids[index]}'>${el}</option>`
        $('#pretest_div').find('select').append(option)
        })
                        } else {
                            $('#pretest_div').hide();
                        }
                    }
                    count += 1
                })
                var first_li = getFirstPreferenceLi();
                if (first_li) {
                    loadShiftsForProgram(first_li.attr('id'));
                } else {
                    clearShiftSelect();
                    hideShiftContainer();
                }
            }
        });
    });

    var first_li = getFirstPreferenceLi();
    if (first_li) {
        loadShiftsForProgram(first_li.attr('id'));
    } else {
        clearShiftSelect();
        hideShiftContainer();
    }
});