$(function () {
    $('.droptrue').on('click', 'li', function () {
        $(this).toggleClass('selected');
    });

    $("ul.droptrue").sortable({
        connectWith: 'ul.droptrue',
        opacity: 0.6,
        revert: true,
        helper: function (e, item) {
            console.log('parent-helper');
            console.log(item);
            if(!item.hasClass('selected'))
               item.addClass('selected');
            var elements = $('.selected').not('.ui-sortable-placeholder').clone();
            var helper = $('<ul/>');
            item.siblings('.selected').addClass('hidden');
            return helper.append(elements);
        },
        start: function (e, ui) {
            var elements = ui.item.siblings('.selected.hidden').not('.ui-sortable-placeholder');
            ui.item.data('items', elements);
        },
        receive: function (e, ui) {
            ui.item.before(ui.item.data('items'));
        },
        stop: function (e, ui) {
            ui.item.siblings('.selected').removeClass('hidden');
            $('.selected').removeClass('selected');
        },
        update: function(){
            updatePostOrder();
            updateAdd();
        }
    });
   

    $("#sortable1, #sortable2, #sortable3").disableSelection();
    $("#sortable1, #sortable2, #sortable3").css('minHeight', $("#sortable1, #sortable2").height() + "px");
});



function updatePostOrder() {
    var arr = [];
    $("#sortable2 li").each(function () {
        arr.push($(this).attr('id'));
    });
    $('#postOrder').val(arr.join(','));
}


function updateAdd() {
    var arr = [];
    $("#sortable3 li").each(function () {
        arr.push($(this).attr('id'));
    });
    $('#add').val(arr.join(','));
}



*{
    font-family: Microsoft JhengHei;
    margin-left: 10px;
    background-color: #4472C4;
}
.listBlock {
    float: left;
}
#sortable1, #sortable2, #sortable3 {
    list-style-type: none;
    margin: 0;
    padding: 0;
    margin-right: 10px;
    background: #fff;
    padding: 5px;
    width: 250px;
/*     border: 1px solid black; */
    border-radius: 5px;
}
#sortable1 li, #sortable2 li, #sortable3 li {
    color:black;
    cursor: move;
    margin: 7px 17px;
    padding: 5px;
    font-size: 1.2em;
    width: 200px;
    background: none;
    background-color: #F07C65;
    border-radius: 5px;
   color: #fff
}
.selected {
    background:#e74 !important;
}
.hidden {
    display:none !important;
}
ul {
    list-style-type: none;
}
input {
   border-radius: 3px;
   border: 1px solid #fff;
   height: 30px;
}
.search{
   margin-top: 30px;
   margin-left: 25px;
   width: 200px;
   padding-left: 10px;
}

