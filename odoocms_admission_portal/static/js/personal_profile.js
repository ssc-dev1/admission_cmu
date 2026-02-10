function onchange_province(){
    province_id = document.getElementById('province_id').value
    var formData = new FormData();
    formData.append('province_id', province_id)
    $.ajax({
        url: "/admission_online/province/change",
        type: "POST",
        dataType: "json",
        data: formData,
        contentType: false,
        processData:false,
        success: function(data){
            $("#domicile_id").empty();
            for(j=0; j< data.domiciles.length; j++){
                $("#domicile_id").append(" <option value="+data.domiciles[j].id+">" + data.domiciles[j].name + "</option>");
            }
        }
    });
}

function onchange_career(value){
    var formData = new FormData();
    formData.append('admission_career_id',value)
    $.ajax({
        url: "/admission_online/graduate/career/change",
        type: "POST",
        dataType: "json",
        data: formData,
        contentType: false,
        processData:false,
        success: function(data){
            window.location.reload();
        }
    });
}

function onchange_nationality() {
    if (document.getElementById('nationality').value == '177') {
        document.getElementById('domicile_id').style.display = 'block';
        document.getElementById('domicile_div').style.display = 'block';
        document.getElementById('province_div').style.display = 'block';
        document.getElementById('province_div_2').style.display = 'none';
    } else {
        document.getElementById('domicile_id').style.display = 'none';
        document.getElementById('domicile_div').style.display = 'none';
        document.getElementById('province_div').style.display = 'none';
        document.getElementById('province_div_2').style.display = 'block';
    }
}

