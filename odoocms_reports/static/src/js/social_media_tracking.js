

var sortDirection = {};

function _report_sort_table(columnIndex) {
    debugger;
    const table = document.getElementById('smsReportTbl');
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);

    if (!sortDirection[columnIndex]) {
        sortDirection[columnIndex] = 1;
    } else {
        sortDirection[columnIndex] = -sortDirection[columnIndex];
    }

    rows.sort((rowA, rowB) => {
        const cellA = rowA.cells[columnIndex].innerText;
        const cellB = rowB.cells[columnIndex].innerText;

        if (!isNaN(cellA) && !isNaN(cellB)) {
            return (parseFloat(cellA) - parseFloat(cellB)) * sortDirection[columnIndex];
        } else {
            return cellA.localeCompare(cellB) * sortDirection[columnIndex];
        }
    });

    rows.forEach(row => tbody.appendChild(row));
}



function _smseReportfilter(tlen,idPrefix,tBodyId){ 
    debugger;
    var filter, input;
    var filterParam=[];
    for(let i=0;i<tlen;i++){
        input = document.getElementById(idPrefix+i);
        filter = input.value?.toUpperCase();
        if(filter!=null&&filter!=""){
             let obg= {index:i,text: filter }
             filterParam.push(obg);
        }
    }
    if(filterParam.length>0){
        searchfilter(filterParam,tBodyId,"specific");
    }else{
        searchfilter(filterParam,tBodyId,"all");

    }
};

function searchfilter(filterParam,tBodyId,type){
    var table, tr, td, txtValue;
    table = document.getElementById(tBodyId);
    tr = table.getElementsByTagName("tr");
    if(type=="specific"){
        for (i = 0; i < tr.length; i++) {
            for (j = 0; j < filterParam.length; j++) {
                td = tr[i].getElementsByTagName("td")[filterParam[j].index]; 
                if (td) {
                    txtValue = td.textContent || td.innerText;
                    if (txtValue.toUpperCase().indexOf(filterParam[j].text) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                        break;
                    }
                }
            }
          
        }
    }
else if(type=="all"){
    for (i = 0; i < tr.length; i++) {
                    tr[i].style.display = "";
    }
}

}


function report_sort(array, key, sortOrder = 'asc') {
    const multiplier = sortOrder === 'asc' ? 1 : -1;
    
    return array.sort((a, b) => {
        const valA = a[key];
        const valB = b[key];

        if (valA > valB) {
            return 1 * multiplier;
        } else if (valA < valB) {
            return -1 * multiplier;
        } else {
            return 0;
        }
    });
}

odoo.define('odoo_admission_ext_a.social_media_tracking', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var qweb = core.qweb;
    var framework = require('web.framework');
    var social_media_tracking = AbstractAction.extend({
        contentTemplate: 'social_media_tracking',
        xmlDependencies: ['/odoocms_reports/static/xml/social_media_tracking.xml'],
        events: {
            'click button[name="action_generate_report"]': '_onGenerateReport',
            'click button[name="action_download_report"]': '_onDownloadReport',
            'change #report_type': '_onReportTypeChange',
            'change #group_by': '_onGroupByChange',
        },
        init: function(parent, action) {
            this._super.apply(this, arguments);
            let today = new Date().toISOString().split('T')[0];
            this.from_date = today;
            this.to_date = today;
            this.report_type = 'summary';
            this.group_by = 'none';
            this.report_data = null;  // To store the report data
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$('#from_date').val(this.from_date);
            this.$('#to_date').val(this.to_date);
            this.$('#report_type').val(this.report_type);
            this.$('#group_by').val(this.group_by);
            this._toggleGroupByField(this.report_type);
            if (this.from_date && this.to_date) {
                this._loadData();
            }
        },
        _onGenerateReport: function(ev) {
            ev.preventDefault();
          
            var self = this;
            var $from_date = this.$('#from_date');
            var $to_date = this.$('#to_date');
            var $report_type = this.$('#report_type');
            var $group_by = this.$('#group_by');
            this.from_date = $from_date.val();
            this.to_date = $to_date.val();
            this.report_type = $report_type.val();
            this.group_by = $group_by.val();
            this._loadData();
        },
        _onReportTypeChange: function(ev) {
            var reportType = this.$('#report_type').val();
            this._toggleGroupByField(reportType);

        },
        _onGroupByChange: function(ev) {
            this._toggleDownloadIcon();
        },
        _toggleGroupByField: function(reportType) {
            if (reportType === 'detail') {
                this.$('.group-by-container').show();
            } else {
                this.$('.group-by-container').hide();
            }
        },
        _toggleDownloadIcon: function() {
            if (this.report_data && this.report_data.length > 0) {
                this.$('.download-icon-container').show();
            } else {
                this.$('.download-icon-container').hide();
            }
        },
        _onDownloadReport: function(ev) {
            ev.preventDefault();
            var self = this;
            this._rpc({
                model: 'social.media.tracking',
                method: 'generate_excel_report',
                args: [this.from_date, this.to_date, this.report_type, this.group_by],
            }).then(function(response) {
                var filename = response[0];
                var file_content = response[1];
                var blob = new Blob([self._base64ToArrayBuffer(file_content)], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
        
                // Create a download link
                var link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = filename;
        
                // Trigger the click event to start download
                document.body.appendChild(link);
                link.click();
        
                // Clean up
                document.body.removeChild(link);
                window.URL.revokeObjectURL(link.href);
            }).catch(function(error) {
                console.log('Failed to download report', error);
            });
        },
        
        _base64ToArrayBuffer: function(base64) {
            var binary_string = window.atob(base64);
            var len = binary_string.length;
            var bytes = new Uint8Array(len);
            for (var i = 0; i < len; i++) {
                bytes[i] = binary_string.charCodeAt(i);
            }
            return bytes.buffer;
        },
        _loadData: function() {
            var self = this;
            debugger;
            framework.blockUI();
            this._rpc({
                model: 'social.media.tracking',
                method: 'get_social_media_tracking_report',
                args: [this.from_date, this.to_date, this.report_type, this.group_by],
            }).then(function(data) {
                if (!Array.isArray(data[0])) {
                    self.$('.table_view').html('<div class="alert alert-danger d-flex justify-content-center align-items-center text-center" >Invalid data format received for SMS report.</div>');
                    self.report_data = null;
                    self._toggleDownloadIcon();
                    framework.unblockUI();
                    return;
                }
                self.report_data = data[0];
                self.render_report(data);
                self._toggleDownloadIcon();
            }).catch(function(error) {
                self.$('.table_view').html('<div class="alert alert-danger d-flex justify-content-center align-items-center text-center">Failed to load Social Media Tracking report data.</div>');
                self.report_data = null;
                self._toggleDownloadIcon();
                framework.unblockUI();
            });
        },
        render_report: function(data) {
            if(data[0] && data[0].length > 4){
                $("#smsReportTbl").removeClass("col-11").addClass("col-8");
            }else if(data[0] && data[0].length < 4){ 
                $("#smsReportTbl").removeClass("col-8").addClass("col-11");
            }
            var template = (data[0] && data[0].length > 0) ? 'social_media_tracking_view' : 'social_media_tracking_no_data';
            this.$('.table_view').html(qweb.render(template, {
                report_lines: data[0],
                report_headings: data[1],
                keys: data[2],
                sms_count_as_per_alphabets: data[3]
            }));
            framework.unblockUI();
        },
    });

    core.action_registry.add('social_media_tracking', social_media_tracking);

    return social_media_tracking;
});

