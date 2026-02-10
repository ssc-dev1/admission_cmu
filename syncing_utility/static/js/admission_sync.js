odoo.define('your_module.admission_sync', function (require) {
    "use strict";

    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var AdmissionSyncFormController = FormController.extend({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if ($node) {
                this.$buttons.on('click', '.o_fetch_students', this._onFetchStudents.bind(this));
                this.$buttons.on('click', '.o_call_db_procedure', this._onCallDbProcedure.bind(this));
            }
        },

        _onFetchStudents: function () {
            var self = this;
            this._rpc({
                model: 'admission.sync',
                method: 'fetch_students',
                args: [[self.initialState.data.id]],
            }).then(function () {
                self.reload();
            });
        },

        _onCallDbProcedure: function () {
            var self = this;
            this._rpc({
                model: 'admission.sync',
                method: 'call_db_procedure',
                args: [[self.initialState.data.id]],
            }).then(function () {
                self.reload();
            });
        },
    });

    var AdmissionSyncFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Controller: AdmissionSyncFormController,
        }),
    });

    viewRegistry.add('admission_sync_form', AdmissionSyncFormView);
});
