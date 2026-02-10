
function _addTotalRow() {
    debugger;
    const table = document.getElementById("smsReportTbl");
    const tableBody = document.getElementById("tableBody");

    if (!table || !tableBody) {
        console.warn("Table or table body not found.");
        return;
    }
    const rows = Array.from(tableBody.querySelectorAll("tr"));
    if (!rows.length) return;

    const existingTotalRow = tableBody.querySelector("tr.total-row");
    if (existingTotalRow) {
        existingTotalRow.remove();
    }
    const colCount = rows[0].cells.length;
    const totals = new Array(colCount).fill(0);
    const isNumericCol = new Array(colCount).fill(true);
    rows.forEach(row => {
        Array.from(row.cells).forEach((cell, index) => {
            const text = cell.innerText.replace(/,/g, "").trim();
            if (text === "") return;
            const num = parseFloat(text);
            if (isNaN(num)) {
                isNumericCol[index] = false;
            }
        });
    });
    rows.forEach(row => {
        Array.from(row.cells).forEach((cell, index) => {
            if (!isNumericCol[index]) return;
            const num = parseFloat(cell.innerText.replace(/,/g, "").trim()) || 0;
            totals[index] += num;
        });
    });

    const totalRow = document.createElement("tr");
    totalRow.classList.add("total-row");
    totalRow.style.backgroundColor = "#f0f0f0";
    totalRow.style.fontWeight = "bold";
    totalRow.classList.add("table-total-highlight");

    for (let i = 0; i < colCount; i++) {
        const td = document.createElement("td");
        if (i === 0) {
            td.innerText = "TOTAL";
        } else if (isNumericCol[i]) {
            td.innerText = totals[i].toLocaleString(undefined, { maximumFractionDigits: 2 });
        } else {
            td.innerText = "";
        }
        totalRow.appendChild(td);
    }

    tableBody.appendChild(totalRow);
}


function addStyles() {
    const style = document.createElement('style');
    style.innerHTML = `
        .table-total-highlight {
            background: #e8f5e9; 
            border-top: 2px solid #4caf50;
        }

        .table-total-highlight td {
            padding: 10px;
            font-weight: 600;
            font-size: 14px;
            color: #388e3c;
        }

        .table-total-highlight td:first-child {
            color: #1976d2; 
        }

        .table-total-highlight:hover {
            background: #dcedc8;
        }
        #report-description-title {
            color: #1976d2;   !important
            font-size: 18px;  !important
            font-weight: 600; !important
            margin-bottom: 1rem; !important
        }
         .table thead {
        position: sticky;
        top: 0;
        z-index: 1; 
        background-color: #f8f9fa;
    }

    .table thead th, .table thead td ,#table_header_sticky {
        position: sticky; !important
        top: 0; !important
        z-index: 2;  !important
        background-color: #f8f9fa;
    }
    `;
    
    document.head.appendChild(style);
}



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

odoo.define('odoo_admission_ext_a.admission_comparison_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var qweb = core.qweb;
    var framework = require('web.framework');
    addStyles();
    var admission_comparison_report = AbstractAction.extend({
        contentTemplate: 'admission_comparison_report',
        xmlDependencies: ['/odoocms_reports/static/xml/admission_comparison_report.xml'],
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
            this.term_id = null;
            this.integer_input =0;
            this.compare_term = null; // Store the selected term
            this.report_data = null;
        },
        start: function() {
            this._super.apply(this, arguments);
            this.$('#from_date').val(this.from_date);
            this.$('#to_date').val(this.to_date);
            this.$('#report_type').val(this.report_type);
            this.$('#group_by').val(this.group_by);
            this .$('#integer_input').val(this.integer_input);
            this._toggleGroupByField(this.report_type);
            this._loadTerms();
            this. _loadCompanies();
            if (this.from_date && this.to_date) {
                this._loadData();
            }
        },
        _loadCompanies: function() {
            var self = this;
            this._rpc({
                model: 'odoocms.application',
                method: 'get_companies',
                args: [],
            }).then(function(company_data) {
                var $companySelect = self.$('#company_select');
                $companySelect.empty();
                company_data.forEach(function(company) {
                    $companySelect.append(`<option value="${company.id}">${company.name}</option>`);
                });
            }).catch(function(error) {
                console.log('Failed to load terms:', error);
            });
        },
        _loadTerms: function() {
            var self = this;
            console.log("Fetching terms..."); // Debugging log
            this._rpc({
                model: 'odoocms.application',
                method: 'get_terms',
                args: [],
            }).then(function(term_data) {
                var $termSelect = self.$('#term_select');
                $termSelect.empty(); 
                term_data.forEach(function(term) {
                    $termSelect.append(`<option value="${term.id}">${term.name}</option>`);
                });
                var $compareSelect = self.$('#compare_term');
                $compareSelect.empty(); 
                term_data.forEach(function(term) {
                    $compareSelect.append(`<option value="${term.id}">${term.name}</option>`);
                });
            }).catch(function(error) {
                console.log('Failed to load terms:', error);
            });
        },
        _onGenerateReport: function(ev) {
            ev.preventDefault();

            var self = this;
            var $from_date = this.$('#from_date');
            var $to_date = this.$('#to_date');
            var $report_type = this.$('#report_type');
            var $group_by = this.$('#group_by');
            var $term_select = this.$('#term_select');
            var $compare_term =this.$('#compare_term');
            var $integer_input = this.$('#integer_input');
            this.from_date = $from_date.val();
            this.to_date = $to_date.val();
            this.report_type = $report_type.val();
            this.group_by = $group_by.val();
            this.term_id = $term_select.val();
            this.compare_term = $compare_term.val();
            this.integer_value = $integer_input.val();
            
            if (!this.integer_value || isNaN(this.integer_value) || this.integer_value <= 0) {
                alert("Please enter a valid positive integer.");
                return;
            }
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
                model: 'odoocms.application',
                method: 'generate_excel_report_admission_comparison',
                args: [this.report_type, this.group_by, this.term_id, this.compare_term, this.integer_value],
            }).then(function(response) {
                var filename = response[0];
                var file_content = response[1];
                var blob = new Blob([self._base64ToArrayBuffer(file_content)], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
                var link = document.createElement('a');
                link.href = window.URL.createObjectURL(blob);
                link.download = filename;
                document.body.appendChild(link);
                link.click();
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
            framework.blockUI();
            this._rpc({
                model: 'odoocms.application',
                method: 'get_admission_comparison_report',
                args: [this.report_type, this.group_by, this.term_id,this.compare_term, this.integer_value],
            }).then(function(data) {
                if (!Array.isArray(data[0])) {
                    self.$('.table_view').html('<div class="alert alert-danger d-flex justify-content-center align-items-center text-center" >Invalid data format received for report.</div>');
                    self.report_data = null;
                    self._toggleDownloadIcon();
                    framework.unblockUI();
                    return;
                }
                self.report_data = data[0];
                self.render_report(data);
                self._toggleDownloadIcon();
            }).catch(function(error) {
                self.$('.table_view').html('<div class="alert alert-danger d-flex justify-content-center align-items-center text-center">Please Select filters and generate report.</div>');
                self.report_data = null;
                self._toggleDownloadIcon();
                framework.unblockUI();
            });
        },
        render_report: function(data) {
            // this._loadTerms();
            debugger;
            if (data[0] && data[0].length > 4) {
                $("#smsReportTbl").removeClass("col-11").addClass("col-8");
            } else if (data[0] && data[0].length < 4) {
                $("#smsReportTbl").removeClass("col-8").addClass("col-11");
            }
            var template = (data[0] && data[0].length > 0) ? 'admission_comparison_report_view' : 'admission_comparison_report_no_data';
            this.$('.table_view').html(qweb.render(template, {
                report_lines: data[0],
                report_headings: data[1],
                keys: data[2],
                description: data[3]
            }));
            addStyles();
            _addTotalRow();
            framework.unblockUI();
        },
    });

    core.action_registry.add('admission_comparison_report', admission_comparison_report);

    return admission_comparison_report;
});


