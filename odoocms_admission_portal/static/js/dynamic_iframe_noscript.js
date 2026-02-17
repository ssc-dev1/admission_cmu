(function (w, d) {
    debugger;
    var code;
    var url = window.location.href;
    if (url.includes('cust')) {
        code = 'GTM-T8GBWCR';
    } else if (url.includes('ubas')) {  
        code = 'GTM-PGB6WJT5';
    } else if (url.includes('maju')) {
        code = 'GTM-TZQ96ZB';
    } else if (url.includes('localhost')) {
    code = 'GTM-PGB6WJT5';
    }

    var noscript = d.createElement('noscript');
    var iframe = d.createElement('iframe');
    iframe.src = 'https://www.googletagmanager.com/ns.html?id=' + code;
    iframe.height = 0;
    iframe.width = 0;
    iframe.style.display = 'none';
    iframe.style.visibility = 'hidden';
    noscript.appendChild(iframe);
    d.body.appendChild(noscript);
})(window, document);