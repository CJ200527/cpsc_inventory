/* staff_withdraw_logic.js — withdraw modal logic. Loaded after ui_helpers.js. */

        
        let availableProducts = [];
        let withdrawCatalogReady = loadWithdrawCatalog();
        async function loadWithdrawCatalog(){
            try {
                // Warehouse-real stock only: server filters is_active = 1 AND stock > 0.
                const res = await fetch('/products/api/list?available_only=1');
                const data = await res.json();
                availableProducts = (data.products || []).map(p => ({
                    id: p.product_id, name: p.product_name,
                    category: p.category || '', unit: p.unit || 'pcs',
                    details: p.details || '', size: p.size || '',
                    price: Number(p.price || 0),
                    stock: (p.stock === undefined || p.stock === null)
                        ? 0 : parseInt(p.stock),
                    reorder: (p.reorder === undefined || p.reorder === null)
                        ? 10 : parseInt(p.reorder)
                }));
                availableProducts.sort((a,b)=>String(a.name||'').localeCompare(String(b.name||''),undefined,{sensitivity:'base'}));
            } catch (e) { availableProducts = []; }
        }

        function fmtPeso(n){ return '₱ ' + Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2, maximumFractionDigits:2}); }
        function shortWdNum(s){
            s=String(s||'');
            if(s.indexOf('-')===-1) return s;
            const parts=s.split('-');
            const tail=(parts.pop()||'').trim();
            const head=(parts[0]||'').trim();
            if(!tail||!head) return s;
            return head+'-'+tail;
        }
        const VIEW_MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
        function fmtViewDate(s){
            s=String(s||'').trim();
            const m=s.match(/(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?/);
            if(!m) return s||'—';
            let h=parseInt(m[4]||'0',10); const ap=h>=12?'PM':'AM'; h=h%12||12;
            return `${VIEW_MONTHS[parseInt(m[2],10)-1]} ${parseInt(m[3],10)}, ${m[1]} | ${h}:${m[5]||'00'} ${ap}`;
        }
        function todayLocal(){ const n=new Date(); const p=x=>String(x).padStart(2,'0'); return `${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())}`; }
        /* Withdraw Number: daily server sequence (offline fallback keeps the
           WD-YYYY-MM-DD shape with a random suffix; DB enforces uniqueness). */
        function fetchWithdrawNumber(numEl){
            if(!numEl) return;
            numEl.value=''; numEl.classList.remove('has-content'); numEl.placeholder='Loading...';
            fetch('/withdraw/get_next_number').then(r=>r.json()).then(dt=>{
                if(dt.withdraw_number){ numEl.value=dt.withdraw_number; numEl.classList.add('has-content'); }
                else numEl.placeholder='Auto-generated';
            }).catch(()=>{
                const n=new Date(); const p=x=>String(x).padStart(2,'0');
                numEl.value=`WD-${n.getFullYear()}-${p(n.getMonth()+1)}-${p(n.getDate())}-${Math.floor(1000+Math.random()*9000)}`;
                numEl.classList.add('has-content');
            });
        }
        /* Duplicate guard (PR-style): one product per request — scan hidden product_id[] values. */
        function isDuplicateWithdrawProduct(selfTr, prodId){
            if(!prodId) return false;
            const hiddens=document.querySelectorAll('#withdraw-items-body input[name="product_id[]"]');
            for(const h of hiddens){
                if(h.closest('tr')!==selfTr && h.value && String(h.value)===String(prodId)) return true;
            }
            return false;
        }
        function escHtml(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
        async function openWithdrawModal(){
            try { await withdrawCatalogReady; } catch (e) {} document.getElementById('withdraw-items-body').innerHTML=''; addWithdrawRow(); document.getElementById('withdraw-modal').classList.remove('hidden');
            const numEl=document.querySelector('#withdraw-modal input[name="ris_number"]'); if(numEl && !numEl.value) fetchWithdrawNumber(numEl);
            const d=document.querySelector('#withdraw-modal input[name="date_requested"]'); if(d){ if(!d.value) d.valueAsDate=new Date(); d.max=todayLocal(); d.classList.toggle('has-content',!!d.value); } }
        function closeWithdrawModal(){ document.getElementById('withdraw-modal').classList.add('hidden'); }
        function addWithdrawRow(){
            const tbody=document.getElementById('withdraw-items-body');
            const rowId=tbody.rows.length;
            const tr=document.createElement('tr');
            tr.innerHTML=`
                <td><div class="custom-dropdown-wrap fx21-field"><input type="text" class="effect-21" placeholder="Select Product" autocomplete="off" required oninput="onWithdrawSearchInput(this)" onfocus="showWithdrawDropdown(this)" onblur="hideWithdrawDropdown(this)" style="padding-right:26px;"><span class="focus-border"><i></i></span><span class="dd-caret">▾</span><input type="hidden" name="product_id[]" id="w-prod-${rowId}"><div class="custom-dropdown-list hidden"></div></div></td>
                <td><span id="w-spec-${rowId}" class="readonly-cell">—</span></td>
                <td><span id="w-unit-${rowId}">—</span></td>
                <td><span id="w-cat-${rowId}">—</span></td>
                <td><span id="w-stock-${rowId}" class="stock-info">—</span></td>
                <td><div class="fx21-field" style="display:inline-block;"><input type="number" name="quantity[]" id="w-qty-${rowId}" class="effect-21" min="1" placeholder="0" style="width:90px; padding:6px; border:1.5px solid #d0dbe5; border-radius:6px;" oninput="calcWithdrawSubtotal(${rowId})" required><span class="focus-border"><i></i></span></div></td>
                <td><button type="button" class="btn-action btn-delete" title="Remove row" onclick="this.closest('tr').remove()"><svg class="act-icon" aria-hidden="true"><use href="#i-x"/></svg></button></td>
            `;
            tbody.appendChild(tr);
        }
        /* Rich product picker (PR-list structure): Name / Specs+Category lines,
           stock pill instead of price. Typing filters; only an explicit pick
           links a product (free text never submits). */
        function withdrawSpecs(p){ return [p.details, p.size].filter(Boolean).join(' '); }
        function filterWithdrawHits(q){
            q=(q||'').trim().toLowerCase();
            const out=[];
            availableProducts.forEach((p,idx)=>{
                const hay=`${p.name||''} ${withdrawSpecs(p)} ${p.category||''}`.toLowerCase();
                if(!q || hay.includes(q)) out.push({p, idx});
            });
            return out.slice(0,50);
        }
        function renderWithdrawDropdown(input, hits){
            const tr=input.closest('tr');
            const list=tr ? tr.querySelector('.custom-dropdown-list') : null;
            if(!list) return;
            if(hits.length===0){
                list.innerHTML=`<div class="custom-dropdown-empty">No matching products.</div>`;
            } else {
                list.innerHTML=hits.map(h=>{
                    const p=h.p;
                    const specLine=[withdrawSpecs(p), p.category].filter(Boolean).join(' | ');
                    return `<div class="custom-dropdown-item" data-idx="${h.idx}" onmousedown="selectWithdrawItem(this)">`
                        +`<span class="cd-text"><span class="cd-name">${escHtml(p.name)}</span>`
                        +`<span class="cd-specs">${escHtml(specLine) || '&nbsp;'}</span></span>`
                        +`<span class="cd-stock">Stock: ${p.stock}</span></div>`;
                }).join('');
            }
            list.classList.remove('hidden');
        }
        function showWithdrawDropdown(input){ renderWithdrawDropdown(input, filterWithdrawHits('')); }
        function onWithdrawSearchInput(input){
            renderWithdrawDropdown(input, filterWithdrawHits(input.value));
            input.setCustomValidity('');
            const key=(input.value||'').trim().toLowerCase();
            const tr=input.closest('tr');
            const hidden=tr ? tr.querySelector('input[name="product_id[]"]') : null;
            const exact=availableProducts.find(p=>(p.name||'').toLowerCase()===key);
            if(hidden && !exact){
                hidden.value='';
                const rid=hidden.id.replace('w-prod-','');
                ['w-spec-','w-unit-','w-cat-','w-stock-'].forEach(prefix=>{
                    const el=document.getElementById(prefix+rid);
                    if(el){ el.innerText='—'; if(prefix==='w-stock-') el.className='stock-info'; }
                });
            }
        }
        function hideWithdrawDropdown(input){
            const tr=input.closest('tr');
            const list=tr ? tr.querySelector('.custom-dropdown-list') : null;
            if(list) setTimeout(()=>list.classList.add('hidden'),150);
        }
        function selectWithdrawItem(el){
            const tr=el.closest('tr');
            const list=el.closest('.custom-dropdown-list');
            if(list) list.classList.add('hidden');
            const p=availableProducts[parseInt(el.dataset.idx,10)];
            if(!tr || !p) return;
            const input=tr.querySelector('input[type="text"]');
            const hidden=tr.querySelector('input[name="product_id[]"]');
            const rowId=hidden ? hidden.id.replace('w-prod-','') : '';
            // Duplicate guard: same item twice → reset + validity bubble (adjust qty instead).
            if(isDuplicateWithdrawProduct(tr, p.id)){
                if(input){ input.value=''; input.setCustomValidity('Already added — adjust its quantity instead.'); input.reportValidity(); }
                if(hidden) hidden.value='';
                return;
            }
            if(input){ input.value=p.name; input.setCustomValidity(''); }
            if(hidden) hidden.value=p.id;
            if(rowId==='') return;
            document.getElementById(`w-spec-${rowId}`).innerText=withdrawSpecs(p) || '—';
            document.getElementById(`w-unit-${rowId}`).innerText=p.unit;
            document.getElementById(`w-cat-${rowId}`).innerText=p.category || '—';
            const stockEl=document.getElementById(`w-stock-${rowId}`);
            stockEl.innerText=p.stock;
            stockEl.className = p.stock==0 ? 'stock-out' : (p.stock<=p.reorder ? 'stock-low' : 'stock-ok');
            const qty=document.getElementById(`w-qty-${rowId}`);
            if(qty){ qty.max=p.stock; qty.value=''; }
        }
        /* Stock guard only: over-requests stay blocked via field validity. */
        function calcWithdrawSubtotal(rowId){
            const qty=parseInt(document.getElementById(`w-qty-${rowId}`).value)||0;
            const prodId=document.getElementById(`w-prod-${rowId}`).value;
            const prod=availableProducts.find(pp=>String(pp.id)===String(prodId));
            if(!prod) return;
            const qtyInput=document.getElementById(`w-qty-${rowId}`);
            if(qty > prod.stock){ qtyInput.setCustomValidity(`Exceeds stock ${prod.stock}`); qtyInput.reportValidity(); }
            else { qtyInput.setCustomValidity(''); }
        }
        function validateWithdrawForm(){
            const rows=document.querySelectorAll('#withdraw-items-body tr');
            if(rows.length===0){ alert('Add at least one item.'); return false; }
            let ok=true, msg='';
            rows.forEach(tr=>{
                const hidden=tr.querySelector('input[name="product_id[]"]');
                const qtyInput=tr.querySelector('input[name="quantity[]"]');
                if(!hidden || !hidden.value){ ok=false; msg='Select product for each row.'; return; }
                const qty=parseInt(qtyInput.value||0);
                const prod=availableProducts.find(pp=>String(pp.id)===String(hidden.value));
                if(prod && qty > prod.stock){ ok=false; msg=`Requested ${qty} exceeds stock ${prod.stock} for ${prod.name}`; }
                if(qty<=0){ ok=false; msg='Quantity must be >0.'; }
            });
            // Submit-time backstop: no two rows may carry the same product.
            const seenPids={};
            document.querySelectorAll('#withdraw-items-body input[name="product_id[]"]').forEach((h,idx)=>{
                if(h.value){
                    if(seenPids[h.value]!==undefined){ ok=false; msg=`Rows ${seenPids[h.value]+1} and ${idx+1} list the same item. Adjust its quantity instead.`; }
                    seenPids[h.value]=idx;
                }
            });
            if(!ok){ alert(msg); return false; }
            return true;
        }
        function openViewModal(id){
            const c=document.getElementById('view-modal-content');
            c.innerHTML='Loading...';
            const gtot0=document.getElementById('view-modal-grand-total');
            if(gtot0) gtot0.innerHTML='Grand Total: <span>₱ 0.00</span>';
            document.getElementById('view-modal').classList.remove('hidden');
            fetch('/withdraw/details/'+id).then(r=>r.json()).then(data=>{
                if(data.error){ c.innerHTML=data.error; return; }
                document.getElementById('view-ris-number').innerText=shortWdNum(data.header.ris_number) + ' Details';
                let html=`<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px 14px;background:#f8fcff;border:1px solid #e2f0fb;border-radius:8px;padding:12px;margin-bottom:12px;font-size:12px;color:#333;">`;
                html+=`<div><strong>WD No.:</strong> <span title="${data.header.ris_number||''}">${shortWdNum(data.header.ris_number)}</span></div><div><strong>Department:</strong> ${data.header.department||'-'}</div><div><strong>Date:</strong> ${fmtViewDate(data.header.date_requested)}</div>`;
                html+=`<div><strong>Requested by:</strong> ${data.header.Firstname||''} ${data.header.Lastname||''}</div><div><strong>Purpose:</strong> ${data.header.purpose||'-'}</div><div><strong>Status:</strong> <span class="badge badge-${(data.header.status||'').toLowerCase()}">${data.header.status}</span></div>`;
                html+=`</div>`;
                html+=`<table class="item-table"><thead><tr><th>Item Name</th><th>Category</th><th>Specification</th><th>Unit</th><th>QTY</th></tr></thead><tbody>`;
                data.items.forEach(i=>{ html+=`<tr><td><strong>${i.item_name}</strong></td><td>${i.category||'-'}</td><td>${i.withdraw_details||i.details||'—'}</td><td>${i.unit||'pcs'}</td><td style="text-align:center;font-weight:700;">${i.quantity}</td></tr>`; });
                html+=`</tbody></table>`;
                if(data.header.status==='Pending') html+=`<div style="margin-top:10px; padding:8px; background:#fff3cd; border:1px solid #ffe082; border-radius:6px; font-size:11px; color:#856404;">Pending — awaiting Admin approval.</div>`;
                c.innerHTML=html;
            });
        }
        function closeViewModal(){ document.getElementById('view-modal').classList.add('hidden'); }
    