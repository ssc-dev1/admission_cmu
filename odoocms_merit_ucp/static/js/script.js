// /*!
// * Start Bootstrap - Clean Blog v6.0.9 (https://startbootstrap.com/theme/clean-blog)
// * Copyright 2013-2023 Start Bootstrap
// * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-clean-blog/blob/master/LICENSE)
// */
// window.addEventListener('DOMContentLoaded', () => {
//     let scrollPos = 0;
//     const mainNav = document.getElementById('mainNav');
//     const headerHeight = mainNav.clientHeight;
//     window.addEventListener('scroll', function() {
//         const currentTop = document.body.getBoundingClientRect().top * -1;
//         if ( currentTop < scrollPos) {
//             // Scrolling Up
//             if (currentTop > 0 && mainNav.classList.contains('is-fixed')) {
//                 mainNav.classList.add('is-visible');
//             } else {
//                 console.log(123);
//                 mainNav.classList.remove('is-visible', 'is-fixed');
//             }
//         } else {
//             // Scrolling Down
//             mainNav.classList.remove(['is-visible']);
//             if (currentTop > headerHeight && !mainNav.classList.contains('is-fixed')) {
//                 mainNav.classList.add('is-fixed');
//             }
//         }
//         scrollPos = currentTop;
//     });
// })

$(document).ready(function () {
    // $('#ref_input_id').parent().hide();
    // $('#select_merit_option').on('change',function(){
    //     if($('#select_merit_option option:selected').val()=='ref'){
    //         $('#list_option').parent().hide();
    //         $('#ref_input_id').parent().show();
    //     }else{
    //         $('#list_option').parent().show();
    //         $('#ref_input_id').parent().hide();

    //     }
        
    // })
    $('#submit_form').prop('disabled', true);

    $('.btn_tab').on('click',function(e){
        $(".btn_tab").removeClass('active');
        $(e.target).addClass('active');
        if($(e.target).attr('value')=='program'){
            $('#submit_form').prop('disabled', true);
            $('#merit_ref').hide();
            $('#merit_program').show();
            $('#merit_type').val('program')
        }else{
            $('#submit_form').prop('disabled', true);
            // $('#submit_form').at();
            $('#merit_program').hide();
            $('#merit_ref').show();
            $('#merit_type').val('ref')
        }
    })
    $('#merit_ref').on('keyup',function(){
        // const regex = /^UCP\d{4}$/i; 
        const regex = /^UCP\d{4,5}$/i;
        const inputValue = $('#merit_ref').val()
        const isValid = regex.test(inputValue);
        $('#submit_form').prop('disabled', !isValid);
        if(!isValid){
            $('#submit_form').css({
                'background-color':'red',
            })
            
            $('#submit_form').text('Invalid!')
        }else{
            $('#submit_form').text('Check Now')
            $('#submit_form').css({
                'background-color':'#1a336c',
            })
            
        }
        
    })
    $('#merit_program').on('change',function(){
        if($('#merit_program').val()==''){
            $('#submit_form').prop('disabled', true);
            $('#submit_form').css({
                'background-color':'red',
            })
            $('#submit_form').text('Invalid!')
        }else{
            
            $('#submit_form').text('Check Now')
            $('#submit_form').prop('disabled', false);
            $('#submit_form').css({
                'background-color':'#1a336c',
            })
        }

    })

    let table = new $('#merit_list_table').DataTable( {
        paging: false,
        order: [[5, 'asc']]
    } );

    
});

    if ( window.history.replaceState ) {
        window.history.replaceState( null, null, '/merit/page' )
    }