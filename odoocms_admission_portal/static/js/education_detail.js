function onchange_inter_degree_level(){
    inter_degree_level = document.getElementById('inter_degree_level').value
    var formData = new FormData();
    formData.append('inter_degree_level',inter_degree_level);
    $.ajax({
        url: "/admission_online/inter_degree_level/change",
        type: "POST",
        dataType: "json",
        data: formData,
        contentType: false,
        processData: false,
        success: function(data){
            $("#inter_subjects").empty();
            if(data.subjects){
            for(j=0; j< data.subjects.length; j++){
                $("#inter_subjects").append(" <option value="+data.subjects[j].id+">" + data.subjects[j].name + "</option>");
            }
            }
            else
            {
            alert("Subjects Not Found!")
            }

        }
    });
}

//Matric Percentage
function onchange_matric_marks() {
    var matric_total_marks = document.getElementById('matric_total_marks').value;
    var matric_obtained_marks = document.getElementById('matric_obtained_marks').value;
    if (matric_total_marks != '' && matric_obtained_marks != '') {
        document.getElementById('matric_percentage').value = (matric_obtained_marks/matric_total_marks*100).toFixed(2);
    }
}

//Inter Percentage
function onchange_inter_marks() {
    var inter_total_marks = document.getElementById('inter_total_marks').value;
    var inter_obtained_marks = document.getElementById('inter_obtained_marks').value;
    if (inter_total_marks != '' && inter_obtained_marks != '') {
        document.getElementById('inter_percentage').value = (inter_obtained_marks/inter_total_marks*100).toFixed(2);
    }
}

//BS14 Percentage
function onchange_bs_14_marks() {
    var bs_14_total_marks = document.getElementById('bs_14_total_marks').value;
    var bs_14_obtained_marks = document.getElementById('bs_14_obtained_marks').value;
    if (bs_14_total_marks != '' && bs_14_obtained_marks != '') {
        document.getElementById('bs_14_percentage').value = (bs_14_obtained_marks/bs_14_total_marks*100).toFixed(2);
    }
}

//BS16 Percentage
function onchange_bs_16_marks() {
    var bs_16_total_marks = document.getElementById('bs_16_total_marks').value;
    var bs_16_obtained_marks = document.getElementById('bs_16_obtained_marks').value;
    if (bs_16_total_marks != '' && bs_16_obtained_marks != '') {
        document.getElementById('bs_16_percentage').value = (bs_16_obtained_marks/bs_16_total_marks*100).toFixed(2);
    }
}

//MS18 Percentage
function onchange_ms_18_marks() {
    var ms_18_total_marks = document.getElementById('ms_18_total_marks').value;
    var ms_18_obtained_marks = document.getElementById('ms_18_obtained_marks').value;
    if (ms_18_total_marks != '' && ms_18_obtained_marks != '') {
        document.getElementById('ms_18_percentage').value = (ms_18_obtained_marks/ms_18_total_marks*100).toFixed(2);
    }
}