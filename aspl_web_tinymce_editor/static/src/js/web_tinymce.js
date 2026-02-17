odoo.define('aspl_web_tinymce_editor.web_tinymce', function(require) {
    "use strict";

    var config = require('web.config');
    var is_tinymce = false;
    var transcoder = require('web_editor.convertInline');
	var FieldHtml = require('web_editor.field.html');
    var FieldHtml = FieldHtml.include({
	reset: function (record, event) {
		var self = this;
		this._reset(record, event);
		var value = this.value;
		if (this.nodeOptions.wrapper) {
			value = this._wrap(value);
		}
		value = this._textToHtml(value);
		if (!event || event.target !== this) {
			if (this.mode === 'edit') {
				if (is_tinymce) {
					for (var inst in tinyMCE.editors) {
						if (tinyMCE.editors[inst].getBody()) {
							var id = '#' + tinyMCE.editors[inst].id
//							if ($(id).data('id') == self.name) {
							tinyMCE.activeEditor.setContent(self.value);
//							}
						}
					}
				}
				else{
					this.wysiwyg.setValue(value);
				}

			} else {
				this.$content.html(value);
			}
		}
		return Promise.resolve();
	},

	_renderEdit: function() {
		var self = this;
		this._rpc({
                    model: 'ir.config_parameter',
                    method: 'get_param',
                    args: ['aspl_web_tinymce_editor.is_tinymce'],
                }, {
                    async: false
                }).then(function(res) {
                    if (res) {
                        is_tinymce = true
                    }
                })
        setTimeout(function(){
		if (is_tinymce) {
			var value = self._textToHtml(self.value);
			if (self.nodeOptions.wrapper) {
				value = self._wrap(value);
			}
			self.$target = $('<textarea>').val(value).hide();
			self.$target.appendTo(self.$el);

			var fieldNameAttachment = _.chain(self.recordData)
				.pairs()
				.find(function (value) {
					return _.isObject(value[1]) && value[1].model === "ir.attachment";
				})
				.first()
				.value();
			if (fieldNameAttachment) {
				self.fieldNameAttachment = fieldNameAttachment;
			}

			self.$el.find('textarea').attr("class", self.name);
			self.$el.find('textarea').attr("data-id", self.name);
			self.$target.val(self._textToHtml(self.value));
			self.$content = self.$el.find('textarea');
			self.$content.html(self._textToHtml(self.value));
			self.$editor = self.$content
			tinymce.remove;
			var $tinymce_ed = tinymce.init({
				selector: '.oe_form_field_html textarea',
				custom_ui_selector: '.' + self.name,
				height: 300,
				width: 'auto',
				resize: false,
				theme: 'modern',
				images_dataimg_filter: function(img) {
                            return img.hasAttribute('internal-blob');
                },
				plugins: [
					'advlist autolink link image imagetools lists colorpicker insertdatetime charmap print fullpage fullscreen preview hr media table emoticons imagetools code nonbreaking pagebreak searchreplace tabfocus textcolor textpattern wordcount autosave'
				],
				external_plugins: { formula: 'http://localhost:8069/aspl_web_tinymce_editor/static/lib/tinymce/plugins/formula_master/formula/plugin.min.js'},
				autosave_interval: "5s",
				image_advtab: true,
				theme_advanced_buttons3_add: "save",
				autosave_ask_before_unload: false,
				save_enablewhendirty: true,
				save_onsavecallback: function() {
					$(document).find('.o_form_button_save').trigger('click')
					alert("Record Saved")
					$(document).find('.o_form_button_edit').trigger('click')
				},
				toolbar: 'undo redo | formatselect | sizeselect |  fontselect |  fontsizeselect | bold italic underline forecolor backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | insertdatetime media link table hr nonbreaking pagebreak | removeformat | fullscreen | formula',
//				plugins : 'advlist autolink link image lists charmap print preview',
			});
			self.$('.mce-tinymce').css('display','block');
			var pro = self._createWysiwygIntance();
			var styleTag = $('<style>.note-editor { display: none; }</style>')
			$('html > head').append(styleTag);
			} else {
				var value = self._textToHtml(self.value);
				if (self.nodeOptions.wrapper) {
					value = self._wrap(value);
				}
				self.$target = $('<textarea>').val(value).hide();
				self.$target.appendTo(self.$el);

				var fieldNameAttachment = _.chain(self.recordData)
					.pairs()
					.find(function (value) {
						return _.isObject(value[1]) && value[1].model === "ir.attachment";
					})
					.first()
					.value();
				if (fieldNameAttachment) {
					self.fieldNameAttachment = fieldNameAttachment;
				}
				if (self.nodeOptions.cssEdit) {
					// must be async because the target must be append in the DOM
					self._createWysiwygIntance();
				} else {
					return self._createWysiwygIntance();
				}
            }
        }, 1000)
	},

    commitChanges: function () {
        var self = this;
		if (is_tinymce) {
		if (this.wysiwyg){
			if (this.wysiwyg.$editor){
			if ($(self.$target[0]).attr("data-id") == 'body'){
				var text_data = $($(tinymce.editors[tinymce.editors.length-1].getBody()))
				var elm = $('<div class="note-editable panel-body" contenteditable="true" style="height: 180px;">'+String(text_data.html()) +' </div>');
				this.wysiwyg.$editor[0]=elm[0]
			}else{
				var text_data = $($(tinymce.editors[self.$target[0].id].getBody()))
				var elm = $('<div class="note-editable panel-body" contenteditable="true" style="height: 180px;">'+String(text_data.html()) +' </div>');
				this.wysiwyg.$editor[0]=elm[0]
			}
			var elm = $('<div class="note-editable panel-body" contenteditable="true" style="height: 180px;">'+String(text_data.html()) +' </div>');
			this.wysiwyg.$editor[0]=elm[0]
			}
		}}
		return this._super();
    },
    })
    return FieldHtml;
});