
  (function (w, d, s, l, i) {
    debugger;
    var code;
    var url = window.location.href;
    if (url.includes('cust')) {
        code = 'GTM-T8GBWCR';
    } else if (url.includes('ubas')) {
        code = 'GTM-PGB6WJT5';
    } else if (url.includes('localhost')) {
        code = 'GTM-PGB6WJT5';
    } else if (url.includes('maju')) {
        code = 'GTM-TZQ96ZB';
    }
    i = code;
    w[l] = w[l] || [];
    w[l].push({
        'gtm.start': new Date().getTime(),
        event: 'gtm.js'
    });
    var f = d.getElementsByTagName(s)[0];
    var j = d.createElement(s);
    var dl = l !== 'dataLayer' ? '&l=' + l : '';
    j.async = true;
    j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
    f.parentNode.insertBefore(j, f);
})(window, document, 'script', 'dataLayer');

// var value = localStorage.getItem('signup');
//     if (value == 'yes') {
//         console.log('yes')
//     } else {
//         window.location.replace('/')
//     }

// (function (w, d, s, l, i) {
//     w[l] = w[l] || []; w[l].push({
//         'gtm.start':
//             new Date().getTime(), event: 'gtm.js'
//     }); var f = d.getElementsByTagName(s)[0],
//         j = d.createElement(s), dl = l != 'dataLayer' ? '&l=' + l : ''; j.async = true; j.src =
//             'https://www.googletagmanager.com/gtm.js?id=' + i + dl; f.parentNode.insertBefore(j, f);
// })(window, document, 'script', 'dataLayer', 'GTM-T8GBWCR');

// $(document).ready(function () {
//     localStorage.removeItem('signup');
// });