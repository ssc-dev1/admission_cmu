/* ...existing code... */
 /* global $, bootstrap */
(function () {
  // ---------- helpers ----------
  function ajaxForm($form, url, onSuccess) {
    const fd = new FormData($form[0]);
    $.ajax({
      url: url,
      type: 'POST',
      data: fd,
      contentType: false,
      processData: false,
      success: function (resp) {
        let data = resp;
        try { data = typeof resp === 'string' ? JSON.parse(resp) : resp; } catch (e) {}
        if (data.status === 'success' || data.status === 'noerror') {
          if (onSuccess) onSuccess(data);
        } else {
          alert(data.msg || 'Something went wrong.');
        }
      },
      error: function (xhr) {
        let msg = 'Request failed';
        try { msg = JSON.parse(xhr.responseText).msg || msg; } catch (e) {}
        alert(msg);
      }
    });
  }

  // numeric & UI helpers
  function nbsValNum(v){ var n=parseFloat(v); return isNaN(n)?0:n; }
  function nbsTogglePair(chkSelector, wrapSelector, amountName){
    var on = $(chkSelector).is(':checked');
    if ($(wrapSelector).length){ $(wrapSelector).toggle(on); }
    else {
      var $amt = $('[name="'+amountName+'"]');
      if ($amt.length) $amt.closest('.col-md-3, .col-md-4, .col-md-6, .col-12').toggle(on);
    }
  }
  function nbsRequireIfChecked($form, chkName, amountName, label){
    const on = $form.find('[name="'+chkName+'"]').is(':checked');
    if (!on) return true;
    const val = nbsValNum($form.find('[name="'+amountName+'"]').val());
    if (val<=0){ alert('Please enter a valid amount for "'+label+'".'); return false; }
    return true;
  }
  function nbsRequireGroupIfChecked($form, chkName, reqs, groupLabel){
    const on = $form.find('[name="'+chkName+'"]').is(':checked');
    if (!on) return true;
    for (const r of reqs){
      const $el = $form.find('[name="'+r.name+'"]');
      const isFile = $el.attr('type') === 'file';
      const val = isFile ? ($el[0]?.files?.length ? 'ok' : '') : ($el.val()||'').trim();
      if (!val){ alert('Please provide "'+r.label+'" for '+groupLabel+'.'); return false; }
      if (r.type==='number' && nbsValNum($el.val())<=0){
        alert('Please provide a valid number for "'+r.label+'" ('+groupLabel+').');
        return false;
      }
    }
    return true;
  }
  function nbsValidateFile($input, opts){
    // opts: {maxMB, types: ['application/pdf','image/*']}
    const f = $input[0]?.files?.[0];
    if (!f) return true;
    if (opts && opts.maxMB && f.size > opts.maxMB * 1024 * 1024){
      alert('File too large. Max '+opts.maxMB+' MB.'); return false;
    }
    if (opts && opts.types && opts.types.length){
      const ok = opts.types.some(function(t){
        if (t.endsWith('/*')) return f.type.startsWith(t.slice(0,-1));
        return f.type === t;
      });
      if (!ok){ alert('Invalid file type.'); return false; }
    }
    return true;
  }

  // step expand/collapse (deterministic)
  function openStep(stepIdToOpen, stepIdToClose) {
    // hide current
    if (stepIdToClose) {
      const current = document.getElementById(stepIdToClose);
      if (current) {
        if (window.bootstrap && bootstrap.Collapse) {
          new bootstrap.Collapse(current, {toggle: false}).hide();
        } else {
          $(current).collapse('hide');
        }
      }
    }
    // show next
    const next = document.getElementById(stepIdToOpen);
    if (next) {
      if (window.bootstrap && bootstrap.Collapse) {
        new bootstrap.Collapse(next, {toggle: false}).show();
      } else {
        $(next).collapse('show');
      }
    }
    const btn = document.querySelector('[data-bs-target="#' + stepIdToOpen + '"]');
    if (btn) btn.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  // toggles
  function togglePrevScholarship() {
    const sel = document.getElementById('prev_scholarship');
    const wrap = document.getElementById('prev_scholarship_details_wrap');
    if (!sel || !wrap) return;
    wrap.style.display = (sel.value === 'yes') ? 'block' : 'none';
  }
  function toggleFather() {
    const v = ($('#father_occupation').val() || '');
    $('.nbs-father-employed').toggle(v === 'employed' || v === 'self_employed');
    $('.nbs-father-unemployed').toggle(v === 'unemployed');
    $('.nbs-father-deceased').toggle(v === 'deceased');
    // When deceased, disable all non-relevant inputs; only allow death certificate upload
    const $form = $('.nbs-father-form');
    const isDeceased = (v === 'deceased');
    const disableList = ['father_employer_name','father_designation','father_salary_slips','father_unemployed_reason'];
    disableList.forEach(function(n){ $form.find('[name="'+n+'"]').prop('disabled', isDeceased); });
    // Ensure death certificate input enabled when deceased
    $form.find('[name="father_death_certificate"]').prop('disabled', !isDeceased);
  }
  function toggleMother() {
    const v = ($('#mother_occupation').val() || '');
    $('.nbs-mother-employed').toggle(v === 'employed' || v === 'self_employed');
    $('.nbs-mother-unemployed').toggle(v === 'unemployed');
    $('.nbs-mother-deceased').toggle(v === 'deceased');
    // When deceased, disable all non-relevant inputs; only allow death certificate upload
    const $form = $('.nbs-mother-form');
    const isDeceased = (v === 'deceased');
    const disableList = ['mother_employer_name','mother_designation','mother_salary_slips','mother_unemployed_reason'];
    disableList.forEach(function(n){ $form.find('[name="'+n+'"]').prop('disabled', isDeceased); });
    // Ensure death certificate input enabled when deceased
    $form.find('[name="mother_death_certificate"]').prop('disabled', !isDeceased);
  }
  function toggleMemberForm() {
    const v = ($('#member_occupation').val() || '');
    $('.when-employed').toggle(v === 'employed' || v === 'self_employed');
    $('.when-student').toggle(v === 'student');
    $('.when-unemployed').toggle(v === 'unemployed');
  }
  function toggleSibExp() { $('#sibexp_block').toggle($('#chk_sibexp').is(':checked')); }
  function toggleMed()    { $('.med-block').toggle($('#chk_med').is(':checked')); }
  function toggleOtherRec(){ $('.otherrec-block').toggle($('#chk_otherrec').is(':checked')); }
  function toggleLoans()  { $('#loan_block').toggle($('#chk_loans').is(':checked')); }
  function toggleVehicles() { $('#vehicle_fields').toggle($('#chk_vehicles').is(':checked')); }
  function toggleIncomeBlocks(){
    nbsTogglePair('[name="income_rental"]',     '.nbs-show-when-rental',     'income_rental_amount');
    nbsTogglePair('[name="income_pension"]',    '.nbs-show-when-pension',    'income_pension_amount');
    nbsTogglePair('[name="income_zakat"]',      '.nbs-show-when-zakat',      'income_zakat_amount');
    nbsTogglePair('[name="income_remittance"]', '.nbs-show-when-remittance', 'income_remittance_amount');
    nbsTogglePair('[name="income_self"]',       '.nbs-show-when-self',       'income_self_amount');
  }
  function toggleRentBlock(){
    var on = $('#chk_rent').is(':checked');
    var $col = $('#chk_rent').closest('.col-md-3, .col-md-4, .col-md-6, .col-12');
    if ($col.length){
      $col.find('[name="monthly_rent"], [name="rent_agreement"], .small-note').toggle(on);
    } else {
      $('[name="monthly_rent"]').toggle(on);
      $('[name="rent_agreement"]').toggle(on);
    }
  }

  function toggleAssets(){
    function toggleByChk(chkName, fieldNames){
      const on = $('[name="'+chkName+'"]').is(':checked');
      fieldNames.forEach(function(fn){
        const $input = $('[name="'+fn+'"]').first();
        if ($input.length) { $input.toggle(on); }
      });
    }
    toggleByChk('asset_house', ['asset_house_area','asset_house_value']);
    toggleByChk('asset_land', ['asset_land_area','asset_land_value']);
    toggleByChk('asset_business', ['asset_business_value']);
  }

  // ---------- EDIT MODAL (open, populate, save) ----------
  const EDIT_CONFIG = {
    member: {
      url: '/nbs/household_member/edit',
      title: 'Edit Household Member',
      fields: [
        {name:'name', label:'Name', type:'text'},
        {name:'relation', label:'Relation', type:'text'},
        {name:'occupation', label:'Occupation', type:'select', options:[
          {v:'', t:'Select'},
          {v:'employed', t:'Employed'},
          {v:'student', t:'Student'},
          {v:'self_employed', t:'Self-Employed / Business'},
          {v:'unemployed', t:'Un-employed'}
        ]},
        {name:'employer_or_institute', label:'Employer / Institute', type:'text'},
        {name:'designation_or_type', label:'Designation / Type', type:'text'}
      ],
      updateCells: {
        '.c-name': 'name',
        '.c-relation': 'relation',
        '.c-occupation': 'occupation',
        '.c-employer': 'employer_or_institute',
        '.c-designation': 'designation_or_type'
      }
    },
    other_income: {
      url: '/nbs/other_income/edit',
      title: 'Edit Other Income',
      fields: [
        {name:'name', label:'Name', type:'text'},
        {name:'relation', label:'Relation', type:'text'},
        {name:'monthly_income', label:'Monthly Income', type:'number'}
      ],
      updateCells: {
        '.c-name': 'name',
        '.c-relation': 'relation',
        '.c-amount': 'monthly_income'
      }
    },
    sibexp: {
      url: '/nbs/sibling_expense/edit',
      title: 'Edit Sibling Education Expense',
      fields: [
        {name:'sibling_name', label:'Sibling Name', type:'text'},
        {name:'monthly_expense', label:'Monthly Expense', type:'number'}
      ],
      updateCells: {
        '.c-name': 'sibling_name',
        '.c-amount': 'monthly_expense'
      }
    },
    vehicle: {
      url: '/nbs/vehicle/edit',
      title: 'Edit Vehicle',
      fields: [
        {name:'make_model', label:'Make & Model', type:'text'},
        {name:'estimated_value', label:'Estimated Value', type:'number'}
      ],
      updateCells: {
        '.c-make': 'make_model',
        '.c-value': 'estimated_value'
      }
    },
    loan: {
      url: '/nbs/loan/edit',
      title: 'Edit Loan',
      fields: [
        {name:'purpose', label:'Purpose', type:'text'},
        {name:'outstanding_amount', label:'Outstanding Amount', type:'number'}
      ],
      updateCells: {
        '.c-purpose': 'purpose',
        '.c-amount': 'outstanding_amount'
      }
    }
  };

  function renderEditFields($container, type, dataset){
    const cfg = EDIT_CONFIG[type];
    $container.empty();
    if (!cfg) return;
    cfg.fields.forEach(function(f){
      let inputHtml = '';
      const val = (dataset[f.name] || '').toString();
      if (f.type === 'select'){
        const opts = (f.options || []).map(function(o){
          const sel = (o.v === val) ? ' selected' : '';
          return '<option value="'+o.v+'"'+sel+'>'+o.t+'</option>';
        }).join('');
        inputHtml = '<select class="form-select" name="'+f.name+'">'+opts+'</select>';
      } else {
        const attrs = f.type === 'number' ? ' step="0.01"' : '';
        inputHtml = '<input class="form-control" type="'+f.type+'" name="'+f.name+'" value="'+$('<div>').text(val).html()+'"'+attrs+'/>';
      }
      const group = [
        '<div class="mb-3">',
          '<label class="form-label">'+f.label+'</label>',
          inputHtml,
        '</div>'
      ].join('');
      $container.append(group);
    });
  }

  function showEditModal(type, dataset){
    const cfg = EDIT_CONFIG[type];
    if (!cfg) return;
    const $modal = $('#nbsEditModal');
    const $form = $('#nbsEditForm');
    $form[0].reset();
    $form.attr('data-url', cfg.url);
    $form.find('input[name="id"]').val(dataset.id || '');
    $modal.find('.modal-title').text(cfg.title);
    renderEditFields($modal.find('.nbs-edit-container'), type, dataset);
    const inst = (window.bootstrap && bootstrap.Modal) ? new bootstrap.Modal($modal[0]) : null;
    if (inst) inst.show(); else $modal.modal('show');
  }

  function updateRowFromRecord($row, type, record){
    const cfg = EDIT_CONFIG[type];
    if (!cfg) return;
    Object.keys(cfg.updateCells).forEach(function(sel){
      const field = cfg.updateCells[sel];
      const value = (record[field] != null) ? record[field] : '';
      $row.find(sel).text(value);
    });
  }

  // ---------- wire up ----------
  $(document).ready(function () {
    // serial number utilities
    function reindexTableBody($tbody){
      $tbody.find('tr').each(function(i){
        var $first = $(this).find('td').first();
        if ($first.hasClass('c-idx')) {
          $first.text(i + 1);
        }
      });
    }
    function reindexAllTables(){
      reindexTableBody($('#tbl-members tbody'));
      reindexTableBody($('#tbl-other-income tbody'));
      reindexTableBody($('#tbl-sibexp tbody'));
      reindexTableBody($('#tbl-vehicles tbody'));
      reindexTableBody($('#tbl-loans tbody'));
    }
    // initial toggles
    togglePrevScholarship(); toggleFather(); toggleMother();
    toggleMemberForm(); toggleSibExp(); toggleMed(); toggleOtherRec(); toggleLoans();
    toggleIncomeBlocks(); toggleRentBlock(); toggleAssets(); toggleVehicles();

    // change listeners
    $(document).on('change', '#prev_scholarship', togglePrevScholarship);
    $(document).on('change', '#father_occupation', toggleFather);
    $(document).on('change', '#mother_occupation', toggleMother);
    $(document).on('change', '#member_occupation', toggleMemberForm);
    $(document).on('change', '#chk_sibexp', toggleSibExp);
    $(document).on('change', '#chk_med', toggleMed);
    $(document).on('change', '#chk_otherrec', toggleOtherRec);
    $(document).on('change', '#chk_loans', toggleLoans);
    $(document).on('change', '#chk_vehicles', toggleVehicles);
    $(document).on('change', '#chk_rent', toggleRentBlock);
    $(document).on('change', '[name="asset_house"],[name="asset_land"],[name="asset_business"]', toggleAssets);
    $(document).on('change',
      '[name="income_rental"],[name="income_pension"],[name="income_zakat"],[name="income_remittance"],[name="income_self"]',
      toggleIncomeBlocks
    );

    function extractDataFromRow($row, type){
      const map = {
        member: {
          id: function(){ return $row.data('id'); },
          name: function(){ return $row.find('.c-name').text().trim(); },
          relation: function(){ return $row.find('.c-relation').text().trim(); },
          occupation: function(){ return $row.find('.c-occupation').text().trim(); },
          employer_or_institute: function(){ return $row.find('.c-employer').text().trim(); },
          designation_or_type: function(){ return $row.find('.c-designation').text().trim(); }
        },
        other_income: {
          id: function(){ return $row.data('id'); },
          name: function(){ return $row.find('.c-name').text().trim(); },
          relation: function(){ return $row.find('.c-relation').text().trim(); },
          monthly_income: function(){ return $row.find('.c-amount').text().trim(); }
        },
        sibexp: {
          id: function(){ return $row.data('id'); },
          sibling_name: function(){ return $row.find('.c-name').text().trim(); },
          monthly_expense: function(){ return $row.find('.c-amount').text().trim(); }
        },
        vehicle: {
          id: function(){ return $row.data('id'); },
          make_model: function(){ return $row.find('.c-make').text().trim(); },
          estimated_value: function(){ return $row.find('.c-value').text().trim(); }
        },
        loan: {
          id: function(){ return $row.data('id'); },
          purpose: function(){ return $row.find('.c-purpose').text().trim(); },
          outstanding_amount: function(){ return $row.find('.c-amount').text().trim(); }
        }
      };
      const getter = map[type] || {};
      const out = {};
      Object.keys(getter).forEach(function(k){
        try { out[k] = getter[k](); } catch(e) { out[k] = ''; }
      });
      return out;
    }

    // open edit modal (robust: use button dataset; fallback to row cells)
    $(document).on('click', '.nbs-edit-row', function () {
      const $btn = $(this);
      const type = $btn.data('type');
      const $row = $btn.closest('tr');
      const fromBtn = $.extend({}, $btn.data());
      // Ensure id present
      fromBtn.id = fromBtn.id || $row.data('id');
      const fromRow = extractDataFromRow($row, type);
      // Prefer button dataset values if present; otherwise row values
      const dataset = Object.assign({}, fromRow, fromBtn);
      showEditModal(type, dataset);
    });

    // save edit
    $(document).on('click', '#nbsEditSaveBtn', function () {
      const $form = $('#nbsEditForm');
      const url = $form.attr('data-url');
      const id = $form.find('input[name="id"]').val();
      if (!url || !id) { alert('Invalid edit request.'); return; }
      const fd = new FormData($form[0]);
      $.ajax({
        url: url,
        type: 'POST',
        data: fd,
        contentType: false,
        processData: false,
        success: function (resp) {
          let data = resp;
          try { data = typeof resp === 'string' ? JSON.parse(resp) : resp; } catch (e) {}
          if (data.status === 'success'){
            // find row and update
            const $row = $('tr[data-id="'+id+'"]').first();
            const type = ($('#nbsEditForm').attr('data-url')||'').split('/')[2];
            // map endpoint to config key
            const map = { 'household_member':'member', 'other_income':'other_income', 'sibling_expense':'sibexp', 'vehicle':'vehicle', 'loan':'loan' };
            const key = map[type] || '';
            if ($row.length && key) updateRowFromRecord($row, key, data.record || {});
            // close modal
            const $modal = $('#nbsEditModal');
            if (window.bootstrap && bootstrap.Modal){
              const inst = bootstrap.Modal.getInstance($modal[0]);
              if (inst) inst.hide();
            } else {
              $modal.modal('hide');
            }
          } else {
            alert(data.msg || 'Failed to save changes.');
          }
        },
        error: function (xhr) {
          let msg = 'Request failed';
          try { msg = JSON.parse(xhr.responseText).msg || msg; } catch (e) {}
          alert(msg);
        }
      });
    });

    // step 1: personal -> next
    $(document).on('submit', '.nbs-personal-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/save/personal', function () {
        openStep('nbs-step2', 'nbs-step1');
      });
    });

    // step 2: father (stay in step2 but continue to step3 per requirement)
    $(document).on('submit', '.nbs-father-form', function (e) {
      e.preventDefault();
      // basic client file validation
      const $pdf = $(this).find('[name="father_salary_slips"]');
      if ($pdf.length && $pdf[0].files.length){ if (!nbsValidateFile($pdf,{maxMB:10,types:['application/pdf']})) return; }
      ajaxForm($(this), '/nbs/save/father', function () {
        openStep('nbs-step3', 'nbs-step2');
      });
    });

    // step 2: mother (go next as well)
    $(document).on('submit', '.nbs-mother-form', function (e) {
      e.preventDefault();
      const $pdf = $(this).find('[name="mother_salary_slips"]');
      if ($pdf.length && $pdf[0].files.length){ if (!nbsValidateFile($pdf,{maxMB:10,types:['application/pdf']})) return; }
      ajaxForm($(this), '/nbs/save/mother', function () {
        openStep('nbs-step3', 'nbs-step2');
      });
    });

    // step 3: add member (append row without reload) - EDIT BUTTON REMOVED
    $(document).on('submit', '.nbs-add-member-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/household_member/add', function (res) {
        const r = res.record;
        const tr = [
          '<tr data-id="'+r.id+'">',
            '<td class="c-idx"></td>',
            '<td class="c-name">'+(r.name||'')+'</td>',
            '<td class="c-relation">'+(r.relation||'')+'</td>',
            '<td class="c-occupation">'+(r.occupation||'')+'</td>',
            '<td class="c-employer">'+(r.employer_or_institute||'')+'</td>',
            '<td class="c-designation">'+(r.designation_or_type||'')+'</td>',
            '<td>',
              '<button type="button" class="btn btn-warning btn-mini nbs-edit-row"',
                ' data-type="member"',
                ' data-id="'+r.id+'"',
                ' data-name="'+(r.name||'')+'"',
                ' data-relation="'+(r.relation||'')+'"',
                ' data-occupation="'+(r.occupation||'')+'"',
                ' data-employer_or_institute="'+(r.employer_or_institute||'')+'"',
                ' data-designation_or_type="'+(r.designation_or_type||'')+'"',
              '>Edit</button> ',
              '<form action="/nbs/household_member/delete" method="post" class="d-inline nbs-del-member-form">',
                '<input type="hidden" name="id" value="'+r.id+'"/>',
                '<button class="btn btn-danger btn-mini" type="submit">Delete</button>',
              '</form>',
            '</td>',
          '</tr>'
        ].join('');
        $('#tbl-members tbody').append(tr);
        reindexTableBody($('#tbl-members tbody'));
        $('#form-add-member')[0].reset();
        toggleMemberForm();
      });
    });
    // step 3: delete member
    $(document).on('submit', '.nbs-del-member-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/household_member/delete', function () {
        const id = $(e.target).find('[name="id"]').val();
        $('#tbl-members tbody tr[data-id="'+id+'"]').remove();
        reindexTableBody($('#tbl-members tbody'));
      });
    });

    // step 4: income (validate + next)
    $(document).on('submit', '.nbs-income-form', function (e) {
      e.preventDefault();
      const $f = $(this);
      if (!nbsRequireIfChecked($f,'income_rental','income_rental_amount','Rental income')) return;
      if (!nbsRequireIfChecked($f,'income_pension','income_pension_amount','Pension')) return;
      if (!nbsRequireIfChecked($f,'income_zakat','income_zakat_amount','Zakat received')) return;
      if (!nbsRequireIfChecked($f,'income_remittance','income_remittance_amount','Remittances')) return;
      if (!nbsRequireIfChecked($f,'income_self','income_self_amount','Self income')) return;

      ajaxForm($f, '/nbs/save/income', function () {
        openStep('nbs-step4', 'nbs-step3');
      });
    });

    // step 4b: add other income (append row) - EDIT BUTTON REMOVED
    $(document).on('submit', '.nbs-add-other-income-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/other_income/add', function (res) {
        const r = res.record;
        const tr = [
          '<tr data-id="'+r.id+'">',
            '<td class="c-idx"></td>',
            '<td class="c-name">'+(r.name||'')+'</td>',
            '<td class="c-relation">'+(r.relation||'')+'</td>',
            '<td class="c-amount">'+(r.monthly_income||0)+'</td>',
            '<td>',
              '<button type="button" class="btn btn-warning btn-mini nbs-edit-row"',
                ' data-type="other_income"',
                ' data-id="'+r.id+'"',
                ' data-name="'+(r.name||'')+'"',
                ' data-relation="'+(r.relation||'')+'"',
                ' data-monthly_income="'+(r.monthly_income||0)+'"',
              '>Edit</button> ',
              '<form action="/nbs/other_income/delete" method="post" class="d-inline nbs-del-other-income-form">',
                '<input type="hidden" name="id" value="'+r.id+'"/>',
                '<button class="btn btn-danger btn-mini" type="submit">Delete</button>',
              '</form>',
            '</td>',
          '</tr>'
        ].join('');
        $('#tbl-other-income tbody').append(tr);
        $('.nbs-add-other-income-form')[0].reset();
        reindexTableBody($('#tbl-other-income tbody'));
      });
    });
    // step 4b: delete other income
    $(document).on('submit', '.nbs-del-other-income-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/other_income/delete', function () {
        const id = $(e.target).find('[name="id"]').val();
        $('#tbl-other-income tbody tr[data-id="'+id+'"]').remove();
        reindexTableBody($('#tbl-other-income tbody'));
      });
    });

    // step 5: expenses -> next
    $(document).on('submit', '.nbs-expenses-form', function (e) {
      e.preventDefault();
      const $f = $(this);
      if (!nbsRequireGroupIfChecked($f, 'is_living_on_rent', [
        {name:'monthly_rent', label:'Monthly Rent', type:'number'},
        {name:'rent_agreement', label:'Rental Agreement (PDF)'}
      ], 'Rent')) return;
      const $ra = $f.find('[name="rent_agreement"]');
      if ($ra[0]?.files?.length){ if (!nbsValidateFile($ra,{maxMB:10,types:['application/pdf']})) return; }

      if (!nbsRequireGroupIfChecked($f, 'has_medical_expense', [
        {name:'medical_expense_nature',  label:'Nature'},
        {name:'medical_expense_amount',  label:'Monthly Amount', type:'number'},
        {name:'medical_expense_attachment', label:'Medical Evidence (PDF)'}
      ], 'Medical expenses')) return;
      const $me = $f.find('[name="medical_expense_attachment"]');
      if ($me[0]?.files?.length){ if (!nbsValidateFile($me,{maxMB:10,types:['application/pdf']})) return; }

      if (!nbsRequireGroupIfChecked($f, 'has_other_recurring', [
        {name:'other_recurring_nature',  label:'Nature'},
        {name:'other_recurring_amount',  label:'Monthly Amount', type:'number'},
        {name:'other_recurring_attachment', label:'Evidence (PDF)'}
      ], 'Other recurring expenses')) return;
      const $oe = $f.find('[name="other_recurring_attachment"]');
      if ($oe[0]?.files?.length){ if (!nbsValidateFile($oe,{maxMB:10,types:['application/pdf']})) return; }

      ajaxForm($f, '/nbs/save/expenses', function () {
        openStep('nbs-step5', 'nbs-step4');
      });
    });

    // step 5: add/delete sibling expense (append/update table) - EDIT BUTTON REMOVED
    $(document).on('submit', '.nbs-add-sibexp-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/sibling_expense/add', function (res) {
        const r = res.record;
        const tr = [
          '<tr data-id="'+r.id+'">',
            '<td class="c-idx"></td>',
            '<td class="c-name">'+(r.sibling_name||'')+'</td>',
            '<td class="c-amount">'+(r.monthly_expense||0)+'</td>',
            '<td>',
              '<button type="button" class="btn btn-warning btn-mini nbs-edit-row"',
                ' data-type="sibexp"',
                ' data-id="'+r.id+'"',
                ' data-sibling_name="'+(r.sibling_name||'')+'"',
                ' data-monthly_expense="'+(r.monthly_expense||0)+'"',
              '>Edit</button> ',
              '<form action="/nbs/sibling_expense/delete" method="post" class="d-inline nbs-del-sibexp-form">',
                '<input type="hidden" name="id" value="'+r.id+'"/>',
                '<button class="btn btn-danger btn-mini" type="submit">Delete</button>',
              '</form>',
            '</td>',
          '</tr>'
        ].join('');
        $('#tbl-sibexp tbody').append(tr);
        $('.nbs-add-sibexp-form')[0].reset();
        reindexTableBody($('#tbl-sibexp tbody'));
      });
    });
    $(document).on('submit', '.nbs-del-sibexp-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/sibling_expense/delete', function () {
        const id = $(e.target).find('[name="id"]').val();
        $('#tbl-sibexp tbody tr[data-id="'+id+'"]').remove();
        reindexTableBody($('#tbl-sibexp tbody'));
      });
    });

    // step 6: assets -> next
    $(document).on('submit', '.nbs-assets-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/save/assets', function () {
        openStep('nbs-step6', 'nbs-step5');
      });
    });
    // vehicles add/delete (append/update) - EDIT BUTTON REMOVED
    $(document).on('submit', '.nbs-add-vehicle-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/vehicle/add', function (res) {
        const r = res.record;
        const tr = [
          '<tr data-id="'+r.id+'">',
            '<td class="c-idx"></td>',
            '<td class="c-make">'+(r.make_model||'')+'</td>',
            '<td class="c-value">'+(r.estimated_value||0)+'</td>',
            '<td>',
              '<button type="button" class="btn btn-warning btn-mini nbs-edit-row"',
                ' data-type="vehicle"',
                ' data-id="'+r.id+'"',
                ' data-make_model="'+(r.make_model||'')+'"',
                ' data-estimated_value="'+(r.estimated_value||0)+'"',
              '>Edit</button> ',
              '<form action="/nbs/vehicle/delete" method="post" class="d-inline nbs-del-vehicle-form">',
                '<input type="hidden" name="id" value="'+r.id+'"/>',
                '<button class="btn btn-danger btn-mini" type="submit">Delete</button>',
              '</form>',
            '</td>',
          '</tr>'
        ].join('');
        $('#tbl-vehicles tbody').append(tr);
        $('.nbs-add-vehicle-form')[0].reset();
        reindexTableBody($('#tbl-vehicles tbody'));
      });
    });
    $(document).on('submit', '.nbs-del-vehicle-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/vehicle/delete', function () {
        const id = $(e.target).find('[name="id"]').val();
        $('#tbl-vehicles tbody tr[data-id="'+id+'"]').remove();
        reindexTableBody($('#tbl-vehicles tbody'));
      });
    });

    // step 7: loans -> next
    $(document).on('submit', '.nbs-loans-toggle-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/save/loans', function () {
        openStep('nbs-step7', 'nbs-step6');
      });
    });
    // loans add/delete (append/update) - EDIT BUTTON REMOVED
    $(document).on('submit', '.nbs-add-loan-form', function (e) {
      e.preventDefault();
      const $p = $(this).find('[name="proof"]');
      if ($p[0]?.files?.length){ if (!nbsValidateFile($p,{maxMB:10,types:['application/pdf']})) return; }
      ajaxForm($(this), '/nbs/loan/add', function (res) {
        const r = res.record;
        const tr = [
          '<tr data-id="'+r.id+'">',
            '<td class="c-idx"></td>',
            '<td class="c-purpose">'+(r.purpose||'')+'</td>',
            '<td class="c-amount">'+(r.outstanding_amount||0)+'</td>',
            '<td>',
              '<button type="button" class="btn btn-warning btn-mini nbs-edit-row"',
                ' data-type="loan"',
                ' data-id="'+r.id+'"',
                ' data-purpose="'+(r.purpose||'')+'"',
                ' data-outstanding_amount="'+(r.outstanding_amount||0)+'"',
              '>Edit</button> ',
              '<form action="/nbs/loan/delete" method="post" class="d-inline nbs-del-loan-form">',
                '<input type="hidden" name="id" value="'+r.id+'"/>',
                '<button class="btn btn-danger btn-mini" type="submit">Delete</button>',
              '</form>',
            '</td>',
          '</tr>'
        ].join('');
        $('#tbl-loans tbody').append(tr);
        $('.nbs-add-loan-form')[0].reset();
        reindexTableBody($('#tbl-loans tbody'));
      });
    });
    $(document).on('submit', '.nbs-del-loan-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/loan/delete', function () {
        const id = $(e.target).find('[name="id"]').val();
        $('#tbl-loans tbody tr[data-id="'+id+'"]').remove();
        reindexTableBody($('#tbl-loans tbody'));
      });
    });

    // step 8: statement (mandatory attachments) + submit (stay in step8)
    $(document).on('submit', '.nbs-statement-form', function (e) {
      e.preventDefault();
      const $f = $(this);
      function hasFile(n){ return ($f.find('[name="'+n+'"]')[0]?.files?.length||0)>0; }

      const missing=[];
      if (!hasFile('bank_statements_6m'))   missing.push('6-month Bank Statement (Parents/Guardians)');
      if (!hasFile('cnic_parents'))         missing.push('CNIC copies of parents/guardians (front & back in one file)');
      if (!hasFile('house_pic_outside_1'))  missing.push('House Picture (Outside 1)');
      if (!hasFile('house_pic_outside_2'))  missing.push('House Picture (Outside 2)');
      if (!hasFile('house_pic_drawing_1'))  missing.push('Drawing Room Picture 1');
      if (!hasFile('house_pic_drawing_2'))  missing.push('Drawing Room Picture 2');

      if (missing.length){
        alert('Please attach the following before saving:\n\n- ' + missing.join('\n- '));
        return;
      }

      ajaxForm($f, '/nbs/save/statement', function () {
        alert('Saved. You can now Submit.');
      });
    });

    $(document).on('submit', '.nbs-submit-form', function (e) {
      e.preventDefault();
      ajaxForm($(this), '/nbs/submit', function () {
        alert('Application submitted!');
        location.reload();
      });
    });
    // initial serial fix in case server rendered IDs
    // replace first cell to be .c-idx if it's still .c-id, then reindex
    ['#tbl-members','#tbl-other-income','#tbl-sibexp','#tbl-vehicles','#tbl-loans'].forEach(function(sel){
      var $tbody = $(sel + ' tbody');
      $tbody.find('tr').each(function(){
        var $first = $(this).find('td').first();
        if ($first.hasClass('c-id')) {
          $first.removeClass('c-id').addClass('c-idx').text('');
        }
      });
    });
    reindexAllTables();
  });
})();
