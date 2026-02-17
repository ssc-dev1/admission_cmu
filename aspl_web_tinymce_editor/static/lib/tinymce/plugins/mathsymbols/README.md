# MathSymbols-TinyMCE-Plugin for Bower

This plugin using [MathJax](https://www.mathjax.org) libary for rendering math font.

This plugin compatible with TinyMce 4.

![MathSymbols TinyMCE Plugin - Visual demo](https://raw.githubusercontent.com/Axel186/mathsymbols-tinymce-plugin/master/demo.gif)

*Is better to check this project before use: http://www.imathas.com/editordemo/demo.html.*

## Install

### NPM:
```
npm install mathsymbols-tinymce-plugin --save
```

### Bower:
```
bower install mathsymbols-tinymce-plugin --save
```

### Download

* [Latest build](https://github.com/Axel186/mathsymbols-tinymce-plugin-bower/archive/master.zip)

## Usage

Configure your TinyMce init settings by adding `external_plugins` and usage of `mathSymbols`: 

```
  tinymce.init({
    selector: 'textarea',
    external_plugins: {'mathSymbols': '/your-path-to-plugin/mathsymbols-tinymce-plugin/plugin.min.js'}, // Add plugin to Tinymce
    toolbar: 'mathSymbols'
  });
```

With this plugin you able to add Math Symbols into your content, but you also have to add [MathJax](https://www.mathjax.org) to the website itself.

## Development

This repository contains only `dist` files, if you want to get the source, check: [mathsymbols-tinymce-plugin](https://github.com/Axel186/mathsymbols-tinymce-plugin).

## License - MIT
