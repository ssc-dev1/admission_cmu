// delete education from table and from database
function delete_education(param, step_no) {
  data = { edu_id: $(param).attr("value"), step_no: step_no };
  
  //  data.append('step_no', step_no);
  let confirmAction = confirm("Are you sure to delete?");
  if (confirmAction) {
    $('#page_loader').show();
    $.post("/delete/education/", data, function (data, textStatus) {
      $('#page_loader').hide();
      location.reload();
      data = JSON.parse(data);
      if (data["status"] == "noerror") {
        if (
          $("#prefer_div_already").find("li").length >= 1 ||
          $("#sortable_program_list").find("li").length > 0
        ) {
          $("#sortable_program_list").find("li").remove();
          $("#prefer_div_already").find("li").remove();
          $("#view_offered_program_button").css({ "pointer-events": "" });
          $("#view_offered_program_button").removeAttr("disabled");
        }
        preferences_allowed = data["preferences_allowed"];
        $("#preference_allowed").val(preferences_allowed);
        if ($(".preference_input_no").length != preferences_allowed) {
          $(".preference_input_no").remove();
          if (preferences_allowed > 0) {
            for (var i = 0; i < preferences_allowed; i++) {
              input = `<input  class="form-control preference_input_no" type="text" placeholder='Preference No ${i + 1
                }'  />`;
              $("#prefer_div").append(input);
            }
          }
        }
      }
      $(param).parents("tr").remove();
      $("#add_education_form").find(`#degree_level option`).each(function (index, element) {
        $(element).removeAttr("disabled");
      });
      $("#education_table_body").find("tr").each(function (index, element) {
        

        //      $(".education_recs")[index].show();
        if ($("#education_table_body").find("tr").length - 1 == index) {
          $(".education_recs")[index].style.display = '';
          //$("#education_table_body").find("tr")[index].closest('tr').find('#education_delete').show();

        }
        
        degree_leveladded = $(element).attr("degree_level");
        $("#add_education_form").find(`#degree_level option:contains(${degree_leveladded})`).attr("disabled", "1");
      });
    });
  }
}
// this function is used when we add subject in education
function prepare_subject(param) {
  let selected = $(param).find("option:selected").val();
  if (selected != "") {
    $(param).parents(".subject_main_div").siblings(".subject_main_div").find("select").find(`option[value=${selected}]`).attr("disabled", "1");
  }
  var all_selected_option = [];
  selected_option = $(".subject_main_div").find("select").find("option:selected");
  $(selected_option).each(function (index, element) {
    if ($(element).val() != "") {
      all_selected_option.push(parseInt($(element).val()));
    }
  });
  all_option = $(".subject_main_div").find("select option");
  $(all_option).each(function (index, element) {
    element_value = parseInt($(element).val());
    if (element_value != "") {
      if (all_selected_option.includes(element_value)) {
      } else {
        $(".subject_main_div").find("select").find(`option[value=${element_value}]`).each(function (index, el) {
          $(el).removeAttr("disabled");
        });
      }
    }
  });
  value = $(param).val();
  $(param).parents("subject_main_div").attr("id", value);
}
function check_subject_marks(param) {
  // this function is used to check obtained_marks less then total marks of subject

  const obtained_marks = $(param).parents(".subject_main_div").find("input[name='subj_marks']").val();
  const total_marks = $(param).parents(".subject_main_div").find("input[name='subj_total_marks']").val();
  if (obtained_marks != "" && total_marks != "") {
    if (parseFloat(total_marks) < parseFloat(obtained_marks)) {
      $(param).parents(".subject_main_div").find("input[name='subj_marks']").val("");
    }
  }
}
function result_status_change() {
  $("#roll_number_last").parent("div").hide();
  $("#last_year_slip").parent("div").hide();
  $("#total_marks").siblings("span").text("Total Marks");
  $("#obtained_marks").siblings("span").text("Obtained Marks");
  if (
    $("#degree_id option:selected").text().trim() == "Intermediate" ||
    $("#degree_id option:selected").text().trim() == "intermediate"
  ) {
    if ($("#result_status").val() == "waiting") {
      $("#roll_number_last").parent("div").show();
      $("#last_year_slip").parent("div").show();
      $("#roll_number_last").siblings("span").text("Second Year Board Roll No.");
      $("#total_marks").siblings("span").text("First Year Total Marks");
      $("#obtained_marks").siblings("span").text("First Year Obtained Marks");
    } else {
      $("#roll_number_last").parent("div").hide();
      $("#last_year_slip").parent("div").hide();
      $("#total_marks").siblings("span").text("Total Marks");
      $("#obtained_marks").siblings("span").text("Obtained Marks");
    }
  }
  if (
    $("#degree_id option:selected").text().trim() == "DAE" ||
    $("#degree_id option:selected").text().trim() == "dae"
  ) {
    if ($("#result_status").val() == "waiting") {
      $("#roll_number_last").parent("div").show();
      $("#last_year_slip").parent("div").show();
      $("#roll_number_last").siblings("span").text("DAE Last Year Roll No.");
      $("#total_marks").siblings("span").text("Second Year Total Marks");
      $("#obtained_marks").siblings("span").text("Second Year Obtained Marks");
    } else {
      $("#roll_number_last").parent().hide();
      $("#last_year_slip").parent().hide();
      $("#total_marks").siblings("span").text("Total Marks");
      $("#obtained_marks").siblings("span").text("Obtained Marks");
    }
  }
  if (
    degree_name == "A-Level" || 
    degree_name == "alevel" ||
    degree_name == "a-level" ||
    degree_name == "ALEVEL" 
    // is_a_level == 'true'
  ) {
    if ($("#result_status").val() === "waiting") {
      $("#percentage").attr("disabled", "1");
      $("#percentage").attr("readonly", "1");
      $("#percentage").removeAttr("required");
  }}
}
function update_education(param) {

 
  academic_id = $(param).attr("value");
  degree_level = `<option value="${$(param).parents("tr").find("#degree_level_id").val()}" selected='1'>${$(param).parents("tr").find("#degree_level_id").val()}</option>`;
  degree = `<option value="${$(param).parents("tr").find("#degree_name").val()}" selected='1'>${$(param).parents("tr").find("#degree_name").attr("degree_name")}</option>`;
  year = $(param).parents("tr").find("#year_edu").val();
  total_marks = $(param).parents("tr").find("#tot_marks").val();
  obtained_marks = $(param).parents("tr").find("#obt_marks").val();
  total_cgpa = $(param).parents("tr").find("#tot_cgpa").val();
  obtained_cgpa = $(param).parents("tr").find("#obt_cgpa").val();
  roll_no = $(param).parents("tr").find("#roll_no_tab").val();
  institue_tb = $(param).parents("tr").find("#institute_tab").val();
  board_tb = $(param).parents("tr").find("#board_tab").val();
  specialization = `<option value="${$(param).parents("tr").find("#group_specialization_name").val()}" selected='1'>${$(param).parents("tr").find("#group_specialization_name").attr("group_specialization_name")}</option>`;

  $("#update_education_check").val(1);
  $("#degree_level").val($(param).parents("tr").find("#degree_level_id").val());
  $("#degree_level").trigger("change");
  $("#degree_level").attr("disabled", "1");
  $("#degree_id").append(degree);
  $("#degree_id").attr("disabled", "1");
  $("#year").val(year);
  $("#result_status").val(
    $(param).parents("tr").find("#result_status_update_").val()
  );
  $("#degree_level").trigger("change");
  $("#total_marks").val(total_marks);
  $("#obtained_marks").val(obtained_marks);
  $("#total_cgpa").val(total_cgpa);
  $("#obtained_cgpa").val(obtained_cgpa);
  $("#institute").val(institue_tb);
  $("#percentage").val(
    parseFloat((obtained_marks / total_marks) * 100).toFixed(2)
  );
  $("#roll_no").val(roll_no);
  $("#board").val(board_tb);

  degree_id = $("#degree_id").val();
  degree_name = $("#degree_id option:selected").text().trim();
  if (
    degree_name == "O-Level" ||
    degree_name == "olevel" ||
    degree_name == "o-level"
  ) {
    $("#result_status").parent().hide();
    $("#board").parent().parent().hide();
    $("#roll_no").parent().parent().hide();
    $("#olevel_calculator_btn").show();
    $("#alevel_calculator_btn").hide();
    $("#obtained_marks").attr("readonly", "1");
    $("#total_marks").attr("readonly", "1");
    return false;
  } else if (
    degree_name == "A-Level" ||
    degree_name == "alevel" ||
    degree_name == "a-level"
  ) {
    $("#result_status").parent().hide();
    $("#board").parent().parent().hide();
    $("#roll_no").parent().parent().hide();
    $("#olevel_calculator_btn").hide();
    $("#alevel_calculator_btn").show();
    $("#obtained_marks").attr("readonly", "1");
    $("#total_marks").attr("readonly", "1");
    return false;
  } else {
    $("#result_status").parent().show();
    $("#board,#specialization_id,#roll_no").parent().parent().show();
    $("#olevel_calculator_btn,#alevel_calculator_btn").hide();
    $("#obtained_marks,#total_marks").removeAttr("readonly");
  }

  degree_level_code = $("#degree_level option:selected").attr("code").toLowerCase().trim();
  if (degree_level_code == "ssc" || degree_level_code == "hssc") {
    var formData = new FormData();
    formData.append("degree_id", degree_id);
    $('#page_loader').show();
    $.ajax({
      url: "/degree/specializations/",
      type: "POST",
      dataType: "json",
      data: formData,
      contentType: false,
      processData: false,
      success: function (data) {
        $('#page_loader').hide();
        result_status_change();
        document.getElementById("add_education_form").reset();
        if (data.status == "noerror") {
          $("#specialization_id").empty();
          $("#specialization_id").append(
            "<option selected='1' value=''>Select Specializations </option>"
          );
          for (j = 0; j < data.specializations.length; j++) {
            selected_option = $(param).parents("tr").find("#group_specialization_name").val();
            if (data.specializations[j].id == parseInt(selected_option)) {
              $("#specialization_id").append(
                "<option selected='1' value=" +
                data.specializations[j].id +
                ">" +
                data.specializations[j].name +
                "</option>"
              );
            } else {
              $("#specialization_id").append(
                "<option value=" +
                data.specializations[j].id +
                ">" +
                data.specializations[j].name +
                "</option>"
              );
            }
          }
        } else {
          console.error(data);
        }
      },
    });
  } else {
    $("#specialization_id").parent().parent().hide();
  }

  degree_level_selected = $("#degree_level option:selected").attr("code").toLowerCase();

  if (degree_level_selected == "ssc") {
    $("#institute_university").parent().hide();
    $("#institute_college").parent().hide();
    $("#institute_school").parent().show();
    $("#institute_school").val(institue_tb);
    $("#cgpa_marks_radio_row").hide();
    $("#marks_div_row").show();
    $("#total_cgpa").parent().hide();
    $("#obtained_cgpa").parent().hide();
    $("#percentage_cgpa").parent().parent().hide();
  } else if (degree_level_selected == "hssc") {
    $("#institute_university").parent().hide();
    $("#institute_college").parent().show();
    $("#institute_college").val(institue_tb);
    $("#institute_school").parent().hide();
    $("#cgpa_marks_radio_row").hide();
    $("#marks_div_row").show();
    $("#total_cgpa").parent().hide();
    $("#obtained_cgpa").parent().hide();
    $("#percentage_cgpa").parent().parent().hide();
  } else {

    $("#institute_university").parent().show();
    $("#institute_university").val(institue_tb);
    $("#institute_college").parent().hide();
    $("#institute_school").parent().hide();
    $("#institute_school").parent().hide();
    $("#board").parent().hide();
    $("#roll_no").parent().hide();
    if (total_cgpa > 0) {
      $("#cgpa_marks_radio_row").show();
      $("#total_cgpa").parent().show();
      $("#obtained_cgpa").parent().show();
      $("#percentage_cgpa").parent().parent().hide();
      $("#marks_div_row").hide();
    } else {
      $("#cgpa_marks_radio_row").hide();
      $("#marks_div_row").show();
      $("#total_cgpa").parent().hide();
      $("#obtained_cgpa").parent().hide();
      $("#percentage_cgpa").parent().parent().hide();
    }
  }

  $("#subject_div").empty();
  if (
    $(param).parents("tr").find("#subject_marks_td").find("input").length > 0
  ) {
    $("#subject_div").append("<h3>Subjects Details</h3>");
    $("#subject_div").append("<hr/>");
    selection_div = `<select required='1' id='selected_subject'>${selection_subjects}</select>`;
    var selection_subjects =
      "'<option selected='1'  value=''>Select Subject</option>'";
    $(param).parents("tr").find("#subject_marks_td").find("input").each(function (index, element) {
      sub_name = $(element).attr("value");
      tot_marks = $(element).attr("total_marks");
      obt_marks = $(element).attr("obtained_marks");
      selection_subjects += `<option selected='1' value='${$(element).attr(
        "id"
      )}'> ${$(element).attr("value")}</option>`;

      str = `<div  class='subject_main_div row' id ='${element.id}'>
            <div id='select_marks_div' class="col-md-2 mt-2 px-0">
            <select onchange='prepare_subject(this)' required='1' class='form-control' name='selected_subject' id='selected_subject'>${selection_subjects}</select>
            </div>
            <div class="col-lg-4 mt-1">
            <input onchange='check_subject_marks(this)' maxlength='4' class="form-control subj_marks validate_number" onkeypress="return (event.charCode >= 48 && event.charCode <= 57) || (event.charCode == 13)" placeholder='Obtained Marks' required='1' type="text" value='${tot_marks}' name="subj_marks" id="${element.name}_marks" />
            </div>
            <div class="col-lg-5 mt-1">
            <input class="form-control subject_total_marks validate_number" maxlength='4' onchange='check_subject_marks(this)' onkeypress="return (event.charCode >= 48 && event.charCode <= 57) || (event.charCode == 13)" placeholder='Total  Marks' required='1' type="text" value='${obt_marks}' name="subj_total_marks" id="${element.name}_total_marks" />
            </div>
            </div>
            `;
      $("#subject_div").append(str);
      selection_subjects =
        "'<option selected='1'  value=''>Select Subject</option>'";
    });
  }
}

function next_step_check() {


  var formData = new FormData();
  formData.append("step_no", $('#step_no_edu_1').val());
  formData.append("step_name", 'education_step_submit');
  $("#page_loader").show();
  $.ajax({
    url: "/next/education/step/",
    type: "POST",
    dataType: "json",
    data: formData,
    contentType: false,
    processData: false,
    success: function (data) {
      var education_criteria = data["education_criteria"];
      var preferences_allowed = data["preferences_allowed"];
      $("#page_loader").hide();
      if (data["status"] == "noerror") {
        document.getElementById("add_education_form").reset();
        $("#preference_allowed").val(data["preferences_allowed"]);
        $("")
        prepare_next_step(data);
      }
    },
  });

}
function add_education_check() {
  debugger;
  // this funciton is used to disabled degree level that is already added
  document.getElementById("update_education_check").value = 1;
  document.getElementById("add_education_form").reset();
  $("#degree_level").removeAttr("disabled");
  $("#degree_id").removeAttr("disabled");
  $("#add_education_form").find(`#degree_level option`).each(function (index, element) {
    $(element).removeAttr("disabled");
  });
  $("#education_table_body").find("tr").each(function (index, element) {
    debugger;
    degree_leveladded = $(element).attr("degree_level");
    // $("#add_education_form").find(`#degree_level option:find(${degree_leveladded})`).attr("disabled", "1");
    $("#add_education_form")
  .find("#degree_level option")
  .filter(function () {
    return $(this).text().trim() === degree_leveladded;
  })
  .attr("disabled", true);
  });
}

$(document).ready(function () {
  // education details js
  $("#olevel_calculator_btn,#alevel_calculator_btn").hide();
  $("#total_cgpa,#obtained_cgpa,#roll_number_last,#last_year_slip").parent().hide();
  if ($("#education_table").find("tbody tr").length < 1) {
    $("#education_table").hide();
  }
  $("#result_status").on("change", function () {
    result_status_change();
  });

  $("#degree_level").on("change", function (e) {
    debugger;
    val = $(this).val();
    if ($("#degree_level").val() == "") {
      return false;
    }
    document.getElementById("add_education_form").reset();
    $("#degree_level").val(val);
    $("#subject_div").empty();
    $("#olevel_calculator_btn,#alevel_calculator_btn").hide();
    $("#percentage_cgpa").parent().parent().hide();
    $("#specialization_id").empty();
    $("#specialization_id").append(
      "<option selected='1' value=''>Select Specializations </option>"
    );

    if ($("#degree_level option:selected").attr("code").toLowerCase().trim() == "ssc" || $("#degree_level option:selected").attr("code").toLowerCase().trim() ==
      "hssc"
    ) {
      $("#specialization_id").parent().parent().show();
    } else {
      $("#specialization_id").parent().parent().hide();
    }

    degree_level_id = $("#degree_level").val();
    var formData = new FormData();
    $('#page_loader').show();
    formData.append("degree_id", degree_level_id);
    $.ajax({
      url: "/degree/level/degree/",
      type: "POST",
      dataType: "json",
      data: formData,
      contentType: false,
      processData: false,
      success: function (data) {
        $('#page_loader').hide();
        if (data.status == "noerror") {
          $("#degree_id").empty();
          $("#degree_id").append(
            " <option selected='1' value='0'+ >Select Degree </option>"
          );
          for (j = 0; j < data.degrees.length; j++) {
            $("#degree_id").append(
              " <option code=" +
              data.degrees[j].code +
              " value=" +
              data.degrees[j].id +
              " > " +
              data.degrees[j].name +
              "</option>"
            );
          }
          if (
            $("#degree_level option:selected").attr("code").trim().toLowerCase() == "ssc"
          ) {
            $("#result_status").val("complete");
            $("#result_status").attr("disabled",'1');
            $("#result_status").css({ "pointer-events": "none" });

            
          } else {
            
            $("#result_status").val("");
            $("#result_status").removeAttr('disabled');
            $("#result_status").css({ "pointer-events": "" });
          }

          if (
            $("#degree_level option:selected").attr("code").trim() == "UG-14" ||
            $("#degree_level option:selected").attr("code").trim() == "UG-16" ||
            $("#degree_level option:selected").attr("code").trim() == "GRAD-16" ||
            $("#degree_level option:selected").attr("code").trim() == "PG-16" ||
            $("#degree_level option:selected").attr("code").trim() == "GRAD-18"
          ) {
            $("#cgpa_marks_radio_row").show();
            $("#result_status").val("complete");
            $("#board").parent().hide();
            $("#roll_no").parent().hide();
            if ($("#degree_level option:selected").attr("code").trim() != "UG-16" || $("#degree_level option:selected").attr("code").trim() != "UG-14") {
              $("#result_status").css({ "pointer-events": "none" });
            }
            // $("#result_status").parent().show();
            if ($("input[name='marks_cgpa']:checked").val() != "marks") {
              $("#percentage_cgpa").parent().parent().hide();
              $("#institute_university").parent().show();
              $("#institute_college").parent().hide();
              $("#institute_school").parent().hide();
              $("#obtained_marks").parent().hide();
              $("#percentage").parent().hide();
              $("#total_marks").parent().hide();
              if (
                $("#degree_level option:selected").attr("code").trim() ==
                "GRAD-16"
              ) {
                $("#marks_radio").parent().hide();
              } else {
                $("#marks_radio").parent().show();
              }
              $("#total_cgpa").parent().show();
              $("#obtained_cgpa").parent().show();
              $("#percentage_cgpa").parent().parent().hide();
              // $('#percentage').show();
            } else {
              $("#percentage_cgpa").parent().parent().show();
              $("#institute_university").parent().show();
              $("#institute_college").parent().hide();
              $("#institute_school").parent().hide();
              $("#obtained_marks").parent().show();
              $("#percentage").parent().show();
              $("#total_marks").parent().show();
              $("#total_cgpa").parent().hide();
              $("#obtained_cgpa").parent().hide();
              $("#percentage_cgpa").parent().parent().show();
            }
          } else {
            if (
              $("#degree_level option:selected").attr("code").trim().toLowerCase() == "ssc"
            ) {
              $("#institute_school").parent().show();
              $("#institute_college").parent().hide();
              $("#institute_university").parent().hide();
              $("#board").parent().show();
            } else if (
              $("#degree_level option:selected").attr("code").trim().toLowerCase() == "hssc"
            ) {
              $("#institute_college").parent().show();
              $("#institute_school").parent().hide();
              $("#institute_university").parent().hide();
              $("#board").parent().show();
            } else {
              $("#institute_college").parent().hide();
              $("#institute_school").parent().hide();
              $("#board").parent().hide();
              $("#institute_university").parent().show();
            }
            $("#result_status").css({ "pointer-events": "" });
            $("#cgpa_marks_radio_row").hide();
            $("#total_cgpa,#obtained_cgpa").parent().hide();
            $("#obtained_marks,#total_marks,#roll_no,#percentage").parent().show();
          }
        }
      },
    });
  });



  // --------------ending degree level ------------//

  // if ($('#degree_level option:selected').attr('code').trim()=='UG-16' || $('#degree_level option:selected').attr('code').trim()=='GRAD-16'|| $('#degree_level option:selected').attr('code').trim()=='GRAD-18') {
  //     $('#cgpa_marks_radio_row').show()

  //     if ($("input[name='marks_cgpa']:checked").val() != 'marks') {
  //         $('#obtained_marks').parent().hide();
  //         $('#percentage').parent().hide();
  //         $('#total_marks').parent().hide();
  //         $('#total_cgpa').parent().show();
  //         $('#obtained_cgpa').parent().show();

  //     } else {
  //         $('#obtained_marks').parent().show();
  //         $('#percentage').parent().show();
  //         $('#total_marks').parent().show();
  //         $('#total_cgpa').parent().hide();
  //         $('#obtained_cgpa').parent().hide();

  //     }
  // }

  $('#institute_college').on('change',function(){
    console.log('working');

    if($('#institute_college option:selected').text().trim()=='other'){
      $("#institute_school").parent().show();

    }else{
      $("#institute_school").parent().hide();


    }
  })

  $("input[name='marks_cgpa']").on("change", function () {
    debugger;
    if ($(this).val() != "marks") {
      $("#percentage_cgpa").parent().parent().hide();
      $("#obtained_marks,#percentage,#total_marks").parent().hide();
      $("#total_cgpa,#obtained_cgpa").parent().show();
    } else {
      $("#obtained_marks,#total_marks,#percentage").parent().show();
      $("#percentage_cgpa").parent().parent().hide();
      $("#total_cgpa,#obtained_cgpa").parent().hide();
    }
  });
  $("#degree_id").on("change", function (e) {
    debugger;
    $("#obtained_marks,#total_marks,#percentage").val("");
    degree_id = $("#degree_id").val();
    degree_name = $("#degree_id option:selected").text().trim();

    if (
      degree_name == "O-Level" ||
      degree_name == "olevel" ||
      degree_name == "o-level" ||
      degree_name == "OLEVEL"
    ) {
      // $('#specialization_id').parent().parent().hide()
      $("#result_status").parent().hide();
      $("#board").parent().parent().hide();
      $("#roll_no").parent().parent().hide();
      $("#olevel_calculator_btn").show();
      $("#alevel_calculator_btn").hide();
      $("#obtained_marks").attr("readonly", "1");
      $("#total_marks").attr("readonly", "1");
    } else if (
      degree_name == "A-Level" ||
      degree_name == "alevel" ||
      degree_name == "a-level" ||
      degree_name == "ALEVEL"
    ) {
      // $("#result_status").parent().hide();
      $("#result_status").parent().show();
      $("#board").parent().parent().hide();
      $("#roll_no").parent().parent().hide();
      $("#olevel_calculator_btn").hide();
      $("#alevel_calculator_btn").show();
      $("#obtained_marks").attr("readonly", "1");
      $("#total_marks").attr("readonly", "1");
    } else {
      $("#result_status").parent().show();
      $("#board").parent().parent().show();
      $("#roll_no").parent().parent().show();
      $("#olevel_calculator_btn").hide();
      $("#alevel_calculator_btn").hide();
      $("#obtained_marks").removeAttr("readonly");
      $("#total_marks").removeAttr("readonly");
    }

    if (
      $("#degree_level option:selected").attr("code").toLowerCase().trim() ==
      "ssc" ||
      $("#degree_level option:selected").attr("code").toLowerCase().trim() ==
      "hssc"
    ) {
      $("#specialization_id").parent().parent().show();
      var formData = new FormData();
      formData.append("degree_id", degree_id);
      $('#page_loader').show();
      $.ajax({
        url: "/degree/specializations/",
        type: "POST",
        dataType: "json",
        data: formData,
        contentType: false,
        processData: false,
        success: function (data) {
          $('#page_loader').hide();
          result_status_change();
          if (data.status == "noerror") {
            $("#specialization_id").empty();
            $("#specialization_id").append(
              "<option selected='1' value=''>Select Specializations </option>"
            );
            for (j = 0; j < data.specializations.length; j++) {
              $("#specialization_id").append(
                "<option value=" +
                data.specializations[j].id +
                ">" +
                data.specializations[j].name +
                "</option>"
              );
            }
          }
        },
      });
    } else {
      $("#specialization_id").parent().parent().hide();
    }
  });
  $("#specialization_id").on("change", function (e) {
    specialization_id = $("#specialization_id option:selected").val();
    if (specialization_id == "") {
      $("#subject_div").hide();
      $(".subject_div").empty();
      return false;
    }

    var formData = new FormData();
    formData.append("specialization_id", specialization_id);
    $('#page_loader').show();
    $.ajax({
      url: "/degree/specializations/subjects",
      type: "POST",
      dataType: "json",
      data: formData,
      contentType: false,
      processData: false,
      success: function (data) {
        $('#page_loader').hide();
        if (data.status == "noerror") {
          if (data.specializations_subject.length > 0) {
            selection_subjects =
              "'<option selected='1'  value=''>Select Subject</option>'";
            for (j = 0; j < data.specializations_subject.length; j++) {
              if (data.specializations_subject[j].name) {
                selection_subjects =
                  selection_subjects +
                  `<option value='${data.specializations_subject[j].id}'>${data.specializations_subject[j].name}</option>`;
              }
            }
            selection_div = `<select required='1' id='selected_subject'>${selection_subjects}</select>`;
            for (j = 0; j < 3; j++) {
              if (j == 0) {
                $("#subject_div").empty();
                $("#subject_div").append("<h3>Subjects Details</h3>");
                $("#subject_div").append("<hr/>");
              }
              if (data.specializations_subject[j].name) {
                str = `<div class='subject_main_div row' id = '${data.specializations_subject[j].id}' >
                            <div id='select_marks_div' class="col-md-2 mt-2 px-0">
                            <select onchange='prepare_subject(this)' required='1' class='form-control' name='selected_subject' id='selected_subject'>${selection_subjects}</select>
                            </div>
                            <div class="col-lg-4 mt-1">
                            <input onchange='check_subject_marks(this)' maxlength='4' class="form-control subj_marks validate_number" onkeypress="return (event.charCode >= 48 && event.charCode <= 57) || (event.charCode == 13)" placeholder='Obtained Marks' required='1' type="text" name="subj_marks" id="${data.specializations_subject[j].name}_marks" />
                            </div>
                            <div class="col-lg-5 mt-1">
                            <input class="form-control subject_total_marks validate_number" maxlength='4' onchange='check_subject_marks(this)' onkeypress="return (event.charCode >= 48 && event.charCode <= 57) || (event.charCode == 13)" placeholder='Total  Marks' required='1' type="text" name="subj_total_marks" id="${data.specializations_subject[j].name}_total_marks" />
                            </div>
                            </div>
                            `;
                $("#subject_div").append(str);
              }
            }
            $("#subject_div").append("<br/><hr class='mt-2' />");
            $("#subject_div").show();
          } else {
            $("#subject_div").hide();
            $("#subject_div").empty();
            return false;
          }
        }
      },
    });
  });

  $("#obtained_marks,#total_marks").on("change", function () {
    if ($("#obtained_marks").val() > 0) {
      if (
        parseFloat($("#obtained_marks").val()) >
        parseFloat($("#total_marks").val())
      ) {
        $("#obtained_marks").val("");
        $("#percentage").val("");
      } else {
        var percentage =
          (parseFloat($("#obtained_marks").val()) /
            parseFloat($("#total_marks").val())) *
          100;
        $("#percentage").val(percentage.toFixed(2));
      }
    }
  });
  $("#obtained_cgpa,#total_cgpa").on("change", function () {
    if ($("#obtained_cgpa").parent().val() > 0) {
      if (
        parseFloat($("#obtained_cgpa").parent().val()) >
        parseFloat($("#total_cgpa").parent().val())
      ) {
        $("#obtained_cgpa").parent().val("");
      }
    }
  });
  $("#obtained_marks_update,#total_marks_update").on("change", function () {
    if ($("#obtained_marks_update").val() > 0) {
      if (
        parseFloat($("#obtained_marks_update").val()) >
        parseFloat($("#total_marks_update").val())
      ) {
        $("#obtained_marks_update").val("");
        $("#percentage_update").val("");
      } else {
        var percentage =
          (parseFloat($("#obtained_marks_update").val()) /
            parseFloat($("#total_marks_update").val())) *
          100;
        $("#percentage_update").val(Math.round(percentage).toFixed(2));
      }
    }
  });
  $("#add_education_form").submit(function (e) {
    e.preventDefault();
    var marks_data = $("#subject_div").find(".subject_main_div");
    data = {};
    if ($("#subject_div").find(".subject_main_div").length > 1) {
      marks_data.each(function (index, element) {
        var subject_id = $(element).attr("id");
        marks = $(element).find("input");
        subject_data = {};
        $(marks).each(function (index, element) {
          subject_data[$(element).attr("name")] = $(element).val();
        });
        data[subject_id] = JSON.stringify(subject_data);
      });
    }

    var formData = new FormData();
    var degree_document = document.getElementById("degree_document");
    degree_file = degree_document.files[0];
    var last_year_slip_file = "";
    if ($("#last_year_slip").parent().is(":visible")) {
      var last_year_slip = document.getElementById("last_year_slip");
      last_year_slip_file = last_year_slip.files[0];
    }
    formData.append("last_year_slip_file", last_year_slip_file);
    formData.append("degree_file", degree_file);
    formData.append("update_education_check",1);
    formData.append("step_no", $("#step_no_edu").val());
    formData.append("step_name", $("#step_name_edu").val());
    formData.append("roll_number_last", $("#roll_number_last").val());
    formData.append("degree_level", $("#degree_level option:selected").val());
    formData.append("degree", $("#degree_id").val());
    formData.append("specialization", $("#specialization_id").val());
    formData.append("passing_year", $("#year").val());
    debugger;
    var instituteValue = $("#institute_school").val();
    if (
      $("#degree_level option:selected").attr("code").trim() == "UG-14" ||
      $("#degree_level option:selected").attr("code").trim() == "UG-16" ||
      $("#degree_level option:selected").attr("code").trim() == "GRAD-16" ||
      $("#degree_level option:selected").attr("code").trim() == "PG-16" ||
      $("#degree_level option:selected").attr("code").trim() == "GRAD-18"
    ) {
      if ($("input[name='marks_cgpa']:checked").val() == "marks") {
        formData.append("total_marks", $("#total_marks").val());
        formData.append("obtained_marks", $("#obtained_marks").val());
        formData.append("percentage", $("#percentage").val());
      } else {
        formData.append("obtained_cgpa", $("#obtained_cgpa").val());
        formData.append("total_cgpa", $("#total_cgpa").val());
      }
      formData.append("institute", $("#institute_university").val());
    } else {
      if (
        $("#degree_level option:selected").attr("code").trim().toLowerCase() ==
        "ssc"
      ) {

        formData.append("institute", $("#institute_school").val());
        
      } else if (
        $("#degree_level option:selected").attr("code").trim().toLowerCase() ==
        "hssc" 
      ) {
         if (instituteValue) {
          formData.append("institute", instituteValue);
        } else {
        formData.append("institute", $("#institute_college").val());
        }
      } else {
        formData.append("institute", $("#institute_university").val());
      }
      formData.append("board", $("#board").val());
      formData.append("roll_no", $("#roll_no").val());
      formData.append("total_marks", $("#total_marks").val());
      formData.append("obtained_marks", $("#obtained_marks").val());
      formData.append("percentage", $("#percentage").val());
    }

    formData.append("result_status", $("#result_status option:selected").val());
    if ($("#subject_div").find(".subject_main_div").length > 1) {
      formData.append("subject_marks", JSON.stringify(data));
    }
    
    $("#page_loader").show();
    $.ajax({
      url: "/admission/application/save/",
      type: "POST",
      dataType: "json",
      data: formData,
      contentType: false,
      processData: false,
      success: function (data) {
        $("#update_education_check").val(1);
        $("#degree_level").removeAttr("disabled");
        $("#degree_id").removeAttr("disabled");
        var education_criteria = data["education_criteria"];
        var preferences_allowed = data["preferences_allowed"];
        $("#page_loader").hide();
        debugger;
        if (data["status"] == "noerror") {
          document.getElementById("add_education_form").reset();
          $("#preference_allowed").val(data["preferences_allowed"]);
          $("#education_table_body").empty();
          $("#education_table").show();
          for (j = 0; j < data.academic_data.length; j++) {
            if (data.academic_data[j].specialization.length < 1) {
              data.academic_data[j].specialization = "--";
            }
            update_education_button = data.academic_data[j].state;
            update_button = `<a role='button' id='education_update' t-att-value='edu.id' data-toggle="modal" data-target="#addeducation" data-whatever="@mdo" type="button" class="btn btn-outline-primary color_scheme_class2 p-1" onclick="update_education(this)">
                        <i style='color: white;border:None' class="fa-regular fa-pen-to-square"></i>
                        </a>`;

            if ($("#application_state").val() == "draft") {
              if (data.academic_data.length >= 2) {
                $("#btn_save_next_edu").show();
              }
              else {
                $("#btn_save_next_edu").hide();
              }

              
              if (data.academic_data.length - 1 == j) {
                action = `<div class="row"><div class="col-4 mx-1">${update_button}</div><div class="col-4"><a role='button' style="display: ''" id='education_delete' value='${data.academic_data[j].id}' type="button" class="btn education_recs btn-outline-primary color_scheme_class2 p-1" onclick="delete_education(this)"><i style="border:None;color:white; " class="fa-solid fa-trash"></i></a></div>`;
              }
              else {
                action = `<div class="row"><div class="col-4 mx-1">${update_button}</div><div class="col-4"><a role='button' style="display: none;" id='education_delete' value='${data.academic_data[j].id}' type="button" class="btn education_recs btn-outline-primary color_scheme_class2 p-1" onclick="delete_education(this)"><i style="border:None;color:white; " class="fa-solid fa-trash"></i></a></div>`;
              }
            } else if (
              $("#application_state").val() != "draft" &&
              update_education_button == "waiting"
            ) {
              action = `<div class="row"><div class="col-4 mx-1">${update_button}</div><div class="col-4"></div></div>`;
            } else {
              action = "";
            }
            marks_td = "";
            $.each(
              data.academic_data[j].subjects_marks,
              function (indexInArray, element) {
                marks_td += `<input type='hidden' id='${element.id}' value='${element.name}' total_marks='${element.total_marks}' obtained_marks='${element.obtained_marks}' />`;
              }
            );

            var row = `<tr degree_level='${data.academic_data[j].degree_level}' id='${data.academic_data[j].id}'>
                        <input type="hidden" id="degree_level_id" value='${data.academic_data[j].degree_level_id}' />
                        <input type="hidden" id="roll_no_tab" value='${data.academic_data[j].board_roll_no}' />
                        <input type="hidden" id="degree_name" degree_name='${data.academic_data[j].degree_name}' value='${data.academic_data[j].degree_name_id}' />
                        <input type="hidden" id="group_specialization_name" group_specialization_name='${data.academic_data[j].specialization}' value='${data.academic_data[j].specialization_id}' />
                        <input type="hidden" id="board_tab" value='${data.academic_data[j].board}' />
                        <input type="hidden" id="institute_tab" value='${data.academic_data[j].institue}' />
                        <input type="hidden" id="tot_marks" value='${data.academic_data[j].total_marks}' />
                        <input type="hidden" id="obt_marks" value='${data.academic_data[j].obtained_marks}' />
                        <input type="hidden" id="tot_cgpa" value='${data.academic_data[j].total_cgpa}' />
                        <input type="hidden" id="obt_cgpa" value='${data.academic_data[j].obtained_cgpa}' />
                        <input type="hidden" id="percentage_u" value='${data.academic_data[j].percentage}' />
                        <input type="hidden" id="year_edu" value='${data.academic_data[j].passing_year}' />
                        <input type="hidden" id="sec_year_roll_no" value='${data.academic_data[j].passing_year}' />
                        <input type="hidden" id="result_status_update_" value='${data.academic_data[j].state}' />
                        <td id='subject_marks_td' style='display:none' >${marks_td}</td>
                        <td class='col-auto'><input type='text' value="${data.academic_data[j].degree_name}" readonly='1' id='degree_val' class='form-control-plaintext col-auto'/></td>
                        <td class='col-auto'><input type='text' value="${data.academic_data[j].specialization}" readonly='1' class='form-control-plaintext col-auto'/></td>
                        <td class='col-auto'><input type='text' value="${data.academic_data[j].institue}" readonly='1' class='form-control-plaintext col-auto'/></td>
                        <td class='col-auto'><input type='text' value="${data.academic_data[j].percentage}" readonly='1' class='form-control-plaintext col-auto'/>
                        <td class='col-auto'><input type='text' value="${data.academic_data[j].state}" readonly='1' class='form-control-plaintext col-auto'/></td>
                        <td class='col-auto'><a href='/file/download/${data.academic_data[j].id}/applicant.academic.detail'><i class='fas fa-download'></i></a></td>
                        <td class='col-auto'>
                        ${action}</td>
                        </tr>`;
            $("#education_table_body").append(row);
          }

          $("#addeducation").modal("toggle");
          $("#update_education_check").val(1);
          $("#degree_level").removeAttr("disabled");
          $("#degree_id").removeAttr("disabled");
          if ($("#education_table_body").find("tr").length > 1) {
            if (education_criteria == "yes") {
              if ($(".preference_input_no").length != preferences_allowed) {
                $(".preference_input_no").remove();
                if (preferences_allowed > 0) {
                  for (var i = 0; i < preferences_allowed; i++) {
                    input = `<input  class="form-control preference_input_no" type="text" placeholder='Preference No ${i + 1
                      }'  />`;
                    $("#prefer_div").append(input);
                  }
                }
              }
              //prepare_next_step(data);
            }
          }
        } else {
          $("#addeducation").modal("toggle");
          $("#update_education_check").val(1);
          $("#degree_level").removeAttr("disabled");
          $("#degree_id").removeAttr("disabled");
          $("#message_popup_text").css({ color: "red" });
          $("#message_popup_text").text(data["msg"]);
          $("#toast_body_alert").text(data["msg"]);
          $("#toast_body_alert").css({ color: "red" });
          $("#alert_show_button").click();
        }
        location.reload();
      },
    });

  });
  /*$("#education_step_submit_form").submit(function (e) {
    e.preventDefault();

    var formData = new FormData();

    $("#page_loader").show();
    $.ajax({
      url: "/next/education/step/",
      type: "POST",
      dataType: "json",
      data: formData,
      contentType: false,
      processData: false,
      success: function (data) {
        var education_criteria = data["education_criteria"];
        var preferences_allowed = data["preferences_allowed"];
        $("#page_loader").hide();
        if (data["status"] == "noerror") {
          document.getElementById("add_education_form").reset();
          $("#preference_allowed").val(data["preferences_allowed"]);

              prepare_next_step(data);
            }
      },
    });
  });*/
  $("#calculate_olevel").on("submit", function (e) {
    e.preventDefault();
    var subject_marks = 0;
    var count_sub_o = 0;
    $("#calculate_olevel").find("select option:selected").each(function (index, element) {
      index = index + 1;
      if (index < 9) {
        if ($(element).val() != "") {
          count_sub_o += 1;
          subject_marks += parseInt($(element).val());
        }
      }
    });
    total_marks = 8 * 100;
    obtained_marks = subject_marks;
    percentage = ((obtained_marks / total_marks) * 100).toFixed(1);
    $("#addeducation").find("#total_marks").val(total_marks);
    $("#addeducation").find("#obtained_marks").val(obtained_marks);
    $("#addeducation").find("#percentage").val(percentage);
    $("#addeducation").find("#result_status").val("complete");
    $("#olevel_calculator").modal("toggle");
    document.getElementById("calculate_olevel").reset();
    return false;
  });
  $("#calculate_alevel").on("submit", function (e) {
    e.preventDefault();
    var subject_marks = 0;
    var count_sub_a = 0;
    $("#calculate_alevel").find("select option:selected").each(function (index, element) {
      index = index + 1;
      if (index < 4) {
        if ($(element).val() != "") {
          count_sub_a += 1;
          subject_marks += parseInt($(element).val());
        }
      }
    });
    total_marks = 3 * 100;
    obtained_marks = subject_marks;
    percentage = ((obtained_marks / total_marks) * 100).toFixed(1);
    $("#addeducation").find("#total_marks").val(total_marks);
    $("#addeducation").find("#obtained_marks").val(obtained_marks);
    $("#addeducation").find("#percentage").val(percentage);
    // $("#addeducation").find("#result_status").val();
    $("#alevel_calculator").modal("toggle");
    document.getElementById("calculate_alevel").reset();
    return false;
  });
});
