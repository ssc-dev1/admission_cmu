/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// identity function for calling harmony imports with the correct context
/******/ 	__webpack_require__.i = function(value) { return value; };
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, {
/******/ 				configurable: false,
/******/ 				enumerable: true,
/******/ 				get: getter
/******/ 			});
/******/ 		}
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(__webpack_require__.s = 1);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


Object.defineProperty(exports, "__esModule", {
  value: true
});
var plugin = function plugin(editor) {

  // Config:
  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  var elementClassName = "tinymce-mathText";
  var mathMarkSymbol = "`";
  var targetFrame = void 0;

  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  editor.addButton('mathSymbols', {
    text: false,
    image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJ' + 'lYWR5ccllPAAAAQJJREFUeNpi/P//PwMlgImBQkCxASxgU5iwmmMBxCX4NP/79y+EBY+8PBCfAuIucr2gB8RHyA0DBSBWA+LzSIZtQcLR6AbsgOJ' + 'YKN8YiC8B8XcoHyS+Eoh9gPgakjq4AR5A3AbEBlC+FRAfRHJRKRDvBuJ4aMDvw+aFM0CsBcQiUPoMVFwSavsEIDYEYiMgvozNgG9AfA6Ic6D0N6j' + '4FKh3IqAaWYF4O65A3AvEXlAaBmRBzoYmeVOoAVLwLICUFxiBmA+Ir0K9wQvEgkBcBhW7Cg2DjUC8CKQWpJcRTDAywgwAuWgSNNCYoQHGAhVngqr' + '5C8S/gfgPUO8nxgHPjQABBgBsa0S64vNBPgAAAABJRU5ErkJggg==',
    tooltip: 'Math Symbols',
    onclick: function onclick() {
      openMathTextEditor(undefined, function (e) {
        // Insert content when the window form is submitted
        var value = e.data.title.trim();
        var element = tinymce.activeEditor.dom.create('span', { class: elementClassName }, getMathText(value));

        editor.selection.setNode(element);
      });
    }
  });

  editor.on("click", function (e) {
    if (e.target.className === elementClassName) {
      var element = e.target;
      var currentValue = element.innerHTML.substr(1, element.innerHTML.length - 2);
      openMathTextEditor(currentValue, function (e) {
        // Insert content when the window form is submitted
        var value = e.data.title.trim();
        element.innerHTML = getMathText(value);
      });
    }
  });

  // Functions:
  //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

  var openMathTextEditor = function openMathTextEditor(prevValue, submit) {
    prevValue = prevValue || "";

    // Open window
    editor.windowManager.open({
      title: 'mathSymbols plugin',
      width: 600,
      height: 300,
      body: [{
        type: 'container',
        html: '<p style="font-size: 14px">Use AsciiMath syntax: <a href="http://asciimath.org/#syntax" ' + 'target="_blank">http://asciimath.org/#syntax</a></p>'
      }, {
        type: 'textbox',
        name: 'title',
        label: 'Math content:',
        value: prevValue,
        onKeyUp: function onKeyUp(e) {
          var value = this.value().trim();

          if (value != prevValue) {
            UpdateMath(value, document.getElementById('MathTextOutput'));
            prevValue = value;
          }
        }
      }, {
        type: 'container',
        html: '<iframe id="MathTextOutput" style="height: 200px"></iframe>',
        height: 200
      }],
      onsubmit: function onsubmit(e) {
        var MathJax = target.contentWindow.MathJax;
        var frame = document.getElementById('tinymce_ifr');

        // Insert content when the window form is submitted
        submit(e);
      }
    });

    // Adding Iframe - render the Math Text preview section.
    var target = document.getElementById('MathTextOutput');
    targetFrame = target.contentWindow || target.contentDocument.document || target.contentDocument;

    targetFrame.document.open();
    var html = '<html><head>' + '<script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js?config=TeX-MML-AM_CHTML">' + '</script><style>html, body{font-size: 30px;} #MathJax_Message{font-size: 14px !important;}</style>' + '</head><div id="math">' + getMathText(prevValue) + '</div></html>';
    targetFrame.document.write(html);
    targetFrame.document.close();
  };

  // Update text and rerender the Math image.
  var UpdateMath = function UpdateMath(TeX, target) {
    var MathJax = target.contentWindow.MathJax;
    var mathWrapper = target.contentDocument.getElementById("math");

    mathWrapper.style.visibility = 'hidden';
    mathWrapper.innerHTML = '';

    var el = document.createElement("span");
    el.className = "math-text";
    el.innerText = mathMarkSymbol + TeX + mathMarkSymbol;

    mathWrapper.appendChild(el);

    MathJax.Hub.Queue(['Typeset', MathJax.Hub, el], function () {
      mathWrapper.style.visibility = 'visible';
    });
  };

  var getMathText = function getMathText(value) {
    return mathMarkSymbol + value + mathMarkSymbol;
  };
};

exports.default = plugin;

/***/ }),
/* 1 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


var _plugin = __webpack_require__(0);

var _plugin2 = _interopRequireDefault(_plugin);

function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

tinymce.PluginManager.add('mathSymbols', _plugin2.default);

/***/ })
/******/ ]);