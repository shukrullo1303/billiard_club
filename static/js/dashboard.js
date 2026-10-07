const tables = JSON.parse(document.getElementById('table-data').textContent);
const products = JSON.parse(document.getElementById('product-data').textContent);
const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
const money = value => Number(value).toLocaleString('uz-UZ');
const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let selected = tables.find(t=>t.id===Number(sessionStorage.getItem('selected-table')))?.id || null, editing = false, snapshot = null;
const floor = document.getElementById('floor');
let toastTimeout;
function toast(message) { const el = document.getElementById('toast'); el.textContent = message; el.hidden = false; clearTimeout(toastTimeout); toastTimeout = setTimeout(() => el.hidden = true, 4500); }
async function post(url, data) {
    const response = await fetch(url, {method:'POST', headers:data instanceof FormData ? {'X-CSRFToken':csrf} : {'X-CSRFToken':csrf,'Content-Type':'application/json'}, body:data instanceof FormData ? data : JSON.stringify(data || {})});
    if (response.redirected) throw new Error('Sessiya tugagan. Sahifani yangilab qayta kiring.');
    let result; try { result = await response.json(); } catch { throw new Error('Server javob bermadi. Qayta urinib ko‘ring.'); }
    if (!response.ok || !result.success) {const error=new Error(result.error || 'Amal bajarilmadi.');error.reservations=result.reservations;throw error;}
    return result;
}
const isPS = t => t.type==='PlayStation';
const deviceName = t => isPS(t) ? `PS ${t.number-6}` : `${t.number}-stol`;
const duration = seconds => {const s=Math.max(0,Math.floor(seconds));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(n=>String(n).padStart(2,'0')).join(':');};
function elapsed(t) { return t.start ? Math.max(0, Math.floor((Date.now() - new Date(t.start)) / 1000)) : 0; }
function timer(t) { return duration(t.deadline ? (new Date(t.deadline)-Date.now())/1000 : elapsed(t)); }
function renderMap() {
    if (!document.getElementById('table-nodes')) return;
    document.getElementById('table-nodes').innerHTML = tables.filter(t=>!isPS(t)).map(t=>`<button class="table-node ${t.start?'busy':t.reservations?.length?'reserved':''} ${selected===t.id?'selected':''}" data-id="${t.id}" style="left:${t.x}%;top:${t.y}%;--rotation:${t.rotation}deg" aria-label="${t.number}-stol, ${t.start?'band':t.reservations?.length?'bron qilingan':'bo‘sh'}" aria-pressed="${selected===t.id}"><span class="table-wood">${'<i></i>'.repeat(6)}</span><span class="table-caption"><strong>${t.number}-STOL</strong></span></button>`).join('');
    document.getElementById('ps-nodes').innerHTML=tables.filter(isPS).map((t,index)=>`<button class="ps-node ${t.start?'busy':t.reservations?.length?'reserved':''} ${selected===t.id?'selected':''}" data-id="${t.id}" style="top:${25+index*15.3}%" aria-label="${deviceName(t)}, ${t.start?'band':t.reservations?.length?'bron qilingan':'bo‘sh'}" aria-pressed="${selected===t.id}"><span>⌘</span><strong>${deviceName(t)}</strong><small>${t.start?'Band':t.reservations?.length?'Bron':'Bo‘sh'}</small></button>`).join('');
    document.querySelectorAll('.table-node,.ps-node').forEach(node=>{
        node.addEventListener('click',()=>{selected=Number(node.dataset.id);renderMap();renderDetail();openSide('table');});
        node.addEventListener('pointerdown',event=>{
            if (!editing || node.classList.contains('ps-node')) return;
            event.preventDefault();
            selected = Number(node.dataset.id);
            const t = tables.find(t=>t.id===selected), rect = floor.getBoundingClientRect();
            const origin = {x:event.clientX,y:event.clientY,tx:t.x,ty:t.y};
            node.setPointerCapture(event.pointerId);
            node.onpointermove = e=>{
                t.x = Math.min(85,Math.max(15,origin.tx-(e.clientX-origin.x)/rect.width*100));
                t.y = Math.min(88,Math.max(12,origin.ty-(e.clientY-origin.y)/rect.height*100));
                node.style.left = `${t.x}%`; node.style.top = `${t.y}%`;
            };
            const finish = ()=>{node.onpointermove=null;node.onpointerup=null;node.onpointercancel=null;renderMap();renderDetail();};
            node.onpointerup=finish;node.onpointercancel=finish;
        });
    });
}
function renderDetail() {
    const t=tables.find(t=>t.id===selected),el=document.getElementById('table-detail');
    if(!t){el.innerHTML='<div class="select-table-empty"><span>▦</span><h3>Stol yoki PS ni tanlang</h3><p>Boshlash va hisobni ko‘rish uchun xaritadagi stol yoki PS xonasini bosing.</p></div>';return;}
    let content='';
    if(editing && !isPS(t)) {
        content=`<div class="rotation-controls"><p>Joylashuv · ${t.rotation}°</p><button id="rotate" class="button subtle">↻ 90° aylantirish</button><div class="form-columns"><label>X (%)<input id="position-x" type="number" min="15" max="85" step="0.1" value="${t.x.toFixed(1)}"></label><label>Y (%)<input id="position-y" type="number" min="12" max="88" step="0.1" value="${t.y.toFixed(1)}"></label></div></div>`;
    } else if(t.start) {
        const price=t.billing_type==='prepaid'?Number(t.prepaid_amount):Math.ceil(elapsed(t)/3600*Number(t.rate)/1000)*1000;
        content=`<div class="clock"><span>${t.deadline?'QOLGAN VAQT':'O‘YIN DAVOMIYLIGI'}</span><strong data-timer="${t.id}">${timer(t)}</strong><div class="cost"><span>${t.billing_type==='prepaid'?'Oldindan to‘langan':'Joriy hisob'}</span><b><span id="live-cost">${money(price)}</span> <small>so‘m</small></b></div></div><button id="session-action" class="button full danger">■ O‘yinni yakunlash</button>`;
    } else if(!editing) {
        content=`<div class="start-options"><input id="start-mode" type="hidden" value="metered"><div class="start-mode-buttons" role="group" aria-label="O‘yin turi"><button type="button" data-start-mode="metered" aria-pressed="true"><span aria-hidden="true">♛</span> VIP</button><button type="button" data-start-mode="prepaid" aria-pressed="false"><span aria-hidden="true">▤</span> To‘lov</button><button type="button" id="reserve-table"><span aria-hidden="true">▣</span> Bron</button></div><label id="amount-field" hidden>Olingan pul (so‘m)<input id="prepaid-input" type="number" min="1" max="9999999999" step="1" placeholder="Masalan, 25000"></label><p id="start-estimate">Vaqt bo‘yicha hisoblanadi.</p><button id="session-action" class="button full primary">▷ O‘yinni boshlash</button></div>`;
    } else content='<p class="detail-note-visible">PS xonalarining joylashuvi rejaga biriktirilgan.</p>';
    el.innerHTML=`<div class="detail-title"><h3>${deviceName(t)}</h3><span class="status-pill ${t.start?'busy':''}">${t.start?'● Band':t.reservations?.length?'● Bron':'● Bo‘sh'}</span></div><div class="rate">${money(t.rate)} so‘m / soat</div>${t.reservations?.length?`<div class="reservation-reminder">${escapeHtml(t.reservations[0].note||t.reservations[0].customer||'Bron')} · ${reservationTime(t.reservations[0].starts_at)} ga bron qilingan <button type="button" id="manage-reservation">Ko‘rish</button></div>`:''}${content}${t.start?'<button type="button" id="reserve-table" class="button subtle full">Bron</button>':''}${t.session_id?'<button id="view-current-bill" class="button subtle full">Stol + bar · Batafsil hisob</button>':''}`;
    document.getElementById('reserve-table')?.addEventListener('click',()=>openReservation(t));
    document.getElementById('manage-reservation')?.addEventListener('click',()=>openReservation(t));
    document.getElementById('view-current-bill')?.addEventListener('click',()=>openBill('session',t.session_id));
    if(editing && !isPS(t)) {
        document.getElementById('rotate').onclick=()=>{t.rotation=(t.rotation+90)%360;renderMap();renderDetail();};
        ['x','y'].forEach(axis=>document.getElementById(`position-${axis}`).onchange=e=>{if(!e.target.value||!e.target.checkValidity()){toast('Koordinatani tekshiring.');renderDetail();return;}t[axis]=Number(e.target.value);renderMap();});
        return;
    }
    const button=document.getElementById('session-action');if(!button)return;
    if(!t.start){
        const mode=document.getElementById('start-mode'), amount=document.getElementById('prepaid-input');
        const estimate=()=>{
            document.getElementById('amount-field').hidden=mode.value!=='amount';
            let message='Vaqt bo‘yicha hisoblanadi.';
            if(mode.value==='30'||mode.value==='60')message=`${money(Math.ceil(Number(t.rate)*Number(mode.value)/60))} so‘m oldindan qabul qilinadi.`;
            if(mode.value==='amount')message=Number(t.rate)>0&&Number(amount.value)>0?`Ajratilgan vaqt: ${duration(Number(amount.value)/Number(t.rate)*3600)}`:'Olingan summani kiriting.';
            document.getElementById('start-estimate').textContent=message;
        };
        document.querySelectorAll('[data-start-mode]').forEach(control=>control.onclick=()=>{
            const prepaid=control.dataset.startMode==='prepaid';
            mode.value=prepaid?'amount':'metered';
            document.querySelectorAll('[data-start-mode]').forEach(item=>item.setAttribute('aria-pressed',String(item===control)));
            estimate();
        });
        amount.oninput=estimate;
    }
    let reservationAcknowledged=false;
    button.onclick=async()=>{
        let payload={mode:'metered'};
        if(!t.start){
            const mode=document.getElementById('start-mode').value;
            if(mode==='amount'){
                const input=document.getElementById('prepaid-input');
                if(!input.value||!input.checkValidity()){toast('Olingan pulni to‘g‘ri kiriting.');input.focus();return;}
                payload={mode:'prepaid',prepaid_amount:input.value};
            } else if(mode!=='metered')payload={mode:'prepaid',prepaid_minutes:Number(mode)};
        }
        if(!t.start&&t.reservations?.length&&!reservationAcknowledged){reservationAcknowledged=true;button.textContent='Bronni hisobga olib boshlash';toast(t.reservations.map(r=>`${reservationTime(r.starts_at)} — ${r.note||r.customer||'Stol bron qilingan'}`).join(' · '));return;}
        if(!t.start)payload.reservation_ack=(t.reservations||[]).map(r=>r.id);
        button.disabled=true;
        try{await post(`/${t.start?'stop':'start'}/${t.id}/`,payload);location.reload();}catch(error){if(error.reservations){t.reservations=error.reservations;renderMap();renderDetail();}toast(error.message);button.disabled=false;}
    };
}
function setEditing(value) {
    editing=value;document.body.classList.toggle('editing',value);document.getElementById('edit-tools').hidden=!value;
    document.getElementById('edit-layout').hidden=value;renderMap();renderDetail();if(value)openSide('table');
}
if(document.getElementById('edit-layout')) document.getElementById('edit-layout').onclick=()=>{snapshot=structuredClone(tables);setEditing(true);};
if(document.getElementById('cancel-layout')) document.getElementById('cancel-layout').onclick=()=>{tables.splice(0,tables.length,...snapshot);setEditing(false);};
if(document.getElementById('save-layout')) document.getElementById('save-layout').onclick=async e=>{
    e.target.disabled=true;
    try {await post('/layout/save/',{tables});setEditing(false);toast('Yangi joylashuv saqlandi.');} catch(error){toast(error.message);} finally{e.target.disabled=false;}
};
window.addEventListener('beforeunload',e=>{if(editing&&JSON.stringify(tables)!==JSON.stringify(snapshot)){e.preventDefault();e.returnValue='';}});
let productPage = 0;
let barMode = 'edit';
let cart = {};
let cartKey = crypto.randomUUID();
let cartPage = 0;
function productImage(p) {
    if(p.image_url) return p.image_url;
    const name = (p.name+' '+p.category).toLowerCase();
    let kind = /choy|kofe|amerikano|issiq/.test(name) ? 'hot' : /suv/.test(name) ? 'water' : /sharbat/.test(name) ? 'juice' : /shokolad/.test(name) ? 'chocolate' : /chips|yeryong|yegulik/.test(name) ? 'snack' : 'soda';
    return `/static/img/products/${kind}.svg`;
}
function renderProducts(query='') {
    const filtered=products.filter(p=>(p.name+' '+p.category).toLowerCase().includes(query.toLowerCase()));
    const el=document.getElementById('products');
    const availableHeight = document.querySelector('.drawer-content').clientHeight;
    const pageSize = 2 * Math.max(1, Math.floor((availableHeight - 161) / 106));
    const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
    productPage = Math.min(productPage, pageCount - 1);
    const visibleProducts = filtered.slice(productPage * pageSize, (productPage + 1) * pageSize);
    el.innerHTML=filtered.length?visibleProducts.map(p=>`<button class="product-card" data-id="${p.id}" aria-label="${escapeHtml(p.name)} ${barMode==='sell'?'savatga qo‘shish':'tahrirlash'}" title="${escapeHtml(p.name)}"><span class="product-picture"><img src="${escapeHtml(productImage(p))}" alt="" loading="lazy"><span class="stock-badge ${p.stock===0?'out':''}">${p.stock} dona</span></span><strong>${escapeHtml(p.name)}</strong><span class="card-price">${money(p.price)} so‘m</span></button>`).join(''):`<p class="empty">${products.length?'Mahsulot topilmadi.':'Birinchi mahsulotingizni + tugmasi orqali qo‘shing.'}</p>`;
    el.querySelectorAll('.product-card').forEach(row=>row.onclick=()=>{const product=products.find(p=>p.id===Number(row.dataset.id));if(barMode==='edit')openProduct(product);else addToCart(product);});
    let pager = document.getElementById('product-pager');
    if (!pager) {pager = document.createElement('div');pager.id='product-pager';el.after(pager);}
    pager.innerHTML = `<button type="button" aria-label="Oldingi mahsulotlar" ${productPage===0?'disabled':''}>←</button><span>${filtered.length ? productPage+1 : 0} / ${filtered.length ? pageCount : 0} · ${filtered.length} mahsulot</span><button type="button" aria-label="Keyingi mahsulotlar" ${productPage>=pageCount-1?'disabled':''}>→</button>`;
    pager.firstElementChild.onclick=()=>{productPage--;renderProducts(query);};
    pager.lastElementChild.onclick=()=>{productPage++;renderProducts(query);};
}
const form=document.getElementById('product-form');
let imagePreviewUrl = null;
let editingProduct = null;
function clearPreviewUrl() {if(imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);imagePreviewUrl=null;}
function closeProduct() {clearPreviewUrl();document.getElementById('cart-panel').hidden=true;document.getElementById('product-editor').hidden=true;document.getElementById('bar-catalog').hidden=false;}
function openProduct(product) {
    clearPreviewUrl();editingProduct=product || null;form.reset();form.elements.id.value='';
    document.getElementById('upload-preview').src=productImage(product || {name:'',category:''});document.getElementById('form-error').textContent='';
    document.getElementById('product-title').textContent=product?'Mahsulotni tahrirlash':'Yangi mahsulot';
    if(product) ['id','name','category','price','stock'].forEach(k=>form.elements[k].value=product[k]);
    openSide('bar');document.getElementById('cart-panel').hidden=true;document.getElementById('bar-catalog').hidden=true;document.getElementById('product-editor').hidden=false;form.elements.name.focus();
}
['add-product','add-product-bottom'].forEach(id=>document.getElementById(id).onclick=()=>openProduct());
document.getElementById('close-product').onclick=closeProduct;
document.getElementById('product-search').oninput=e=>{productPage=0;renderProducts(e.target.value);};
document.getElementById('bar-nav').onclick=e=>{e.preventDefault();openBarOrder();};
document.getElementById('table-bar').onclick=openBarOrder;
document.getElementById('payments-nav').onclick=e=>{e.preventDefault();openSide('payments');};
document.getElementById('product-image').onchange=e=>{
    const file=e.target.files[0];if(!file)return;
    if(file.size>5*1024*1024 || !['image/png','image/jpeg','image/webp'].includes(file.type)) {document.getElementById('form-error').textContent='JPG, PNG yoki WebP rasm tanlang (5 MB gacha).';e.target.value='';return;}
    clearPreviewUrl();imagePreviewUrl=URL.createObjectURL(file);document.getElementById('upload-preview').src=imagePreviewUrl;
    form.elements.remove_image.value='false';document.getElementById('form-error').textContent='';
};
document.getElementById('remove-image').onclick=()=>{clearPreviewUrl();form.elements.image.value='';form.elements.remove_image.value='true';document.getElementById('upload-preview').src=productImage({...editingProduct,image_url:'',name:form.elements.name.value,category:form.elements.category.value});};
form.onsubmit=async e=>{
    e.preventDefault();const button=form.querySelector('[type=submit]');button.disabled=true;
    try {
        const {product} = await post('/bar/save/',new FormData(form));
        const index = products.findIndex(p=>p.id===product.id);
        if(index<0) products.push(product); else products[index]=product;
        products.sort((a,b)=>(a.category+a.name).localeCompare(b.category+b.name));
        renderProducts(document.getElementById('product-search').value);
        closeProduct();toast('Mahsulot saqlandi.');
    } catch(error){document.getElementById('form-error').textContent=error.message;}
    finally {button.disabled=false;}
};
document.querySelectorAll('.pay').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await post(`/payment/${button.dataset.id}/`);location.reload();}catch(error){toast(error.message);button.disabled=false;}});
const dateParts = new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'numeric',year:'numeric',timeZone:'Asia/Tashkent'}).formatToParts(new Date());
const dateValue = key => dateParts.find(p=>p.type===key).value;
const months = ['yanvar','fevral','mart','aprel','may','iyun','iyul','avgust','sentabr','oktabr','noyabr','dekabr'];
document.getElementById('today').textContent = `${dateValue('day')}-${months[Number(dateValue('month'))-1]}, ${dateValue('year')}`;
setInterval(()=>{document.querySelectorAll('[data-timer]').forEach(el=>{const t=tables.find(t=>t.id===Number(el.dataset.timer));el.textContent=timer(t);});const t=tables.find(t=>t.id===selected);if(t&&document.getElementById('live-cost'))document.getElementById('live-cost').textContent=money(t.billing_type==='prepaid'?t.prepaid_amount:Math.ceil(elapsed(t)/3600*Number(t.rate)/1000)*1000);},1000);
const drawer = document.getElementById('control-drawer');
function openPayments() {
    const dialog=document.getElementById('payments-dialog');
    const list=document.querySelector('#drawer-payments > .payments');
    if(list)document.getElementById('payments-dialog-content').append(list);
    if(!dialog.open)dialog.showModal();
    document.getElementById('payments-nav').classList.add('selected');
}
document.getElementById('close-payments-dialog').onclick=()=>document.getElementById('payments-dialog').close();
document.getElementById('payments-dialog').addEventListener('close',()=>{
    const list=document.querySelector('#payments-dialog-content > .payments');
    if(list)document.getElementById('drawer-payments').append(list);
    document.getElementById('payments-nav').classList.remove('selected');
});
let drawerTrigger = null;
function openSide(panel) {
    const showPayments = panel==='payments';
    document.body.classList.remove('mobile-menu-open');
    document.getElementById('mobile-menu-toggle').setAttribute('aria-expanded','false');
    if(panel==='bar') {
        document.getElementById('bar-manage-dialog').showModal();
        document.getElementById('drawer-bar').hidden=false;
        renderProducts(document.getElementById('product-search').value);
        return;
    }
    panel='table';
    drawer.hidden=false;
    document.body.classList.add('drawer-open');
    document.getElementById('drawer-shade').hidden=false;
    document.getElementById('drawer-table').hidden=false;
    document.getElementById('payments-nav').classList.toggle('selected',showPayments);
    if(showPayments) {
        if(window.matchMedia('(max-width: 760px)').matches){drawer.hidden=true;document.body.classList.remove('drawer-open');}
        openPayments();
    }
    if(panel==='bar') renderProducts(document.getElementById('product-search').value);
    sessionStorage.setItem('drawer-panel',panel);
    sessionStorage.setItem('selected-table',selected || '');
}
function closeSide() {
    if(window.matchMedia('(max-width: 760px)').matches){drawer.hidden=true;document.body.classList.remove('drawer-open');document.getElementById('drawer-shade').hidden=true;return;}
    selected=null;sessionStorage.removeItem('selected-table');renderMap();renderDetail();openSide('table');
}
document.getElementById('close-drawer').onclick=closeSide;
document.getElementById('drawer-shade').onclick=closeSide;
document.querySelectorAll('[data-panel]').forEach(tab=>{
    tab.onclick=()=>openSide(tab.dataset.panel);
    tab.onkeydown=e=>{
        const names=['table','bar'];let index=names.indexOf(tab.dataset.panel);
        if(e.key==='ArrowRight')index=(index+1)%2;else if(e.key==='ArrowLeft')index=(index+1)%2;else return;
        e.preventDefault();openSide(names[index]);document.getElementById(`tab-${names[index]}`).focus();
    };
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!drawer.hidden&&!document.querySelector('dialog[open]'))closeSide();});
renderMap();renderDetail();renderProducts();
const previousPanel=new URLSearchParams(location.search).get('panel') || sessionStorage.getItem('drawer-panel');
if(previousPanel==='payments')openSide('payments');else if(!window.matchMedia('(max-width: 760px)').matches)openSide('table');

new ResizeObserver(()=>renderProducts(document.getElementById('product-search').value)).observe(document.querySelector('.drawer-content'));

function changeCart() {cartKey=crypto.randomUUID();document.getElementById('cart-count').textContent=Object.values(cart).reduce((sum,n)=>sum+n,0);}
function addToCart(product) {
    if((cart[product.id]||0)>=product.stock){toast('Mahsulot qoldig‘i yetarli emas.');return;}
    cart[product.id]=(cart[product.id]||0)+1;changeCart();toast(`${product.name} savatga qo‘shildi.`);
}
function renderCart() {
    const items=Object.entries(cart).filter(([,q])=>q>0).map(([id,quantity])=>({...products.find(p=>p.id===Number(id)),quantity}));
    const count=Math.max(1,Math.ceil(items.length/2));cartPage=Math.min(cartPage,count-1);
    document.getElementById('cart-items').innerHTML=items.length?items.slice(cartPage*2,cartPage*2+2).map(p=>`<div class="cart-item"><span><strong>${escapeHtml(p.name)}</strong><small>${money(p.price)} so‘m</small></span><div class="quantity-control"><button data-id="${p.id}" data-delta="-1" aria-label="${escapeHtml(p.name)} kamaytirish">−</button><b>${p.quantity}</b><button data-id="${p.id}" data-delta="1" aria-label="${escapeHtml(p.name)} ko‘paytirish">+</button></div></div>`).join('')+`<div class="cart-pages"><button id="cart-prev" ${cartPage===0?'disabled':''}>←</button><small>${cartPage+1}/${count} · ${items.length} mahsulot</small><button id="cart-next" ${cartPage>=count-1?'disabled':''}>→</button></div>`:'<p class="empty">Savat bo‘sh. Kartochkadan mahsulot tanlang.</p>';
    document.querySelectorAll('.quantity-control button').forEach(button=>button.onclick=()=>{const id=Number(button.dataset.id),q=(cart[id]||0)+Number(button.dataset.delta),product=products.find(p=>p.id===id);if(q>product.stock){toast('Qoldiq yetarli emas.');return;}if(q<=0)delete cart[id];else cart[id]=q;changeCart();renderCart();});
    if(items.length){document.getElementById('cart-prev').onclick=()=>{cartPage--;renderCart();};document.getElementById('cart-next').onclick=()=>{cartPage++;renderCart();};}
    document.getElementById('cart-total').textContent=`${money(items.reduce((sum,p)=>sum+Number(p.price)*p.quantity,0))} so‘m`;
    document.getElementById('checkout').disabled=!items.length;
}
document.getElementById('bar-sell-mode').onclick=()=>setBarMode('sell');
document.getElementById('bar-edit-mode').onclick=()=>setBarMode('edit');
function setBarMode(mode){barMode=mode;document.getElementById('bar-sell-mode').setAttribute('aria-pressed',String(mode==='sell'));document.getElementById('bar-edit-mode').setAttribute('aria-pressed',String(mode==='edit'));renderProducts(document.getElementById('product-search').value);}
document.getElementById('open-cart').onclick=()=>{document.getElementById('bar-catalog').hidden=true;document.getElementById('product-editor').hidden=true;document.getElementById('cart-panel').hidden=false;document.getElementById('sale-table').value=selected||'';document.getElementById('cart-error').textContent='';renderCart();};
document.getElementById('close-cart').onclick=closeProduct;
document.getElementById('checkout').onclick=async()=>{
    const button=document.getElementById('checkout');button.disabled=true;
    try{
        const result=await post('/bar/sale/',{request_key:cartKey,table_id:document.getElementById('sale-table').value||null,items:Object.entries(cart).map(([id,quantity])=>({id:Number(id),quantity}))});
        cart={};changeCart();products.splice(0,products.length,...result.products);closeProduct();renderProducts();toast(`Bar savdosi #${result.sale_id}: ${money(result.total)} so‘m qabul qilindi.`);
        if(!editing)location.reload();
    }catch(error){document.getElementById('cart-error').textContent=error.message;button.disabled=false;}
};

// Expiration is reconciled by the server; notices remain until dismissed.
let stateInFlight=false;
const notified=new Set(JSON.parse(localStorage.getItem('expired-notifications')||'[]'));
function showExpiration(item) {
    if(notified.has(item.id))return;
    notified.add(item.id);localStorage.setItem('expired-notifications',JSON.stringify([...notified].slice(-300)));
    const label=item.device_name || (item.table_type==='PlayStation'?`PS ${item.table_number-6}`:`${item.table_number}-stol`);
    const notice=document.createElement('div');notice.className='expiry-notice';
    const text=document.createElement('strong');text.textContent=`${label}: vaqt tugadi!`;
    const close=document.createElement('button');close.textContent='×';close.setAttribute('aria-label','Bildirishnomani yopish');close.onclick=()=>notice.remove();notice.append(text,close);document.getElementById('expiry-alerts').append(notice);
    if('Notification' in window&&Notification.permission==='granted')new Notification('O‘yin vaqti tugadi',{body:`${label} uchun oldindan to‘langan vaqt yakunlandi.`,tag:`session-${item.id}`});
}
async function syncState() {
    if(stateInFlight)return;stateInFlight=true;
    try{
        const response=await fetch('/state/',{headers:{'Accept':'application/json'}});
        if(!response.ok||response.redirected)return;
        const data=await response.json();if(!data.success)return;
        let changed=false;
        data.tables.forEach(row=>{const table=tables.find(t=>t.id===row.id);if(!table)return;if(table.start!==row.start||table.deadline!==row.deadline||JSON.stringify(table.reservations)!==JSON.stringify(row.reservations))changed=true;Object.assign(table,row);});
        (data.expired||[]).forEach(showExpiration);
        if(changed){renderMap();renderDetail();}
    }catch{/* Retry on the next tick without interrupting data entry. */}finally{stateInFlight=false;}
}
const notificationButton=document.getElementById('enable-notifications');
notificationButton.onclick=async()=>{
    if(!('Notification' in window)){toast('Bildirishnomalar shu sahifada ko‘rsatiladi.');return;}
    const result=await Notification.requestPermission();toast(result==='granted'?'Brauzer bildirishnomalari yoqildi.':'Vaqt tugaganda shu sahifada xabar ko‘rinadi.');
};
syncState();setInterval(syncState,5000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncState();});

const barOrderDialog=document.getElementById('bar-order-dialog');
let orderQuantities={},orderKey=crypto.randomUUID(),orderBusy=false;
function openBarOrder() {
    document.body.classList.remove('mobile-menu-open');
    document.getElementById('mobile-menu-toggle').setAttribute('aria-expanded','false');
    document.getElementById('order-device').value=selected||'';
    document.getElementById('order-error').textContent='';
    const category=document.getElementById('order-category');
    const chosen=category.value;
    category.innerHTML='<option value="">Barcha kategoriyalar</option>'+[...new Set(products.map(p=>p.category))].sort().map(c=>`<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    category.value=chosen;renderOrderProducts();barOrderDialog.showModal();document.getElementById('order-search').focus();
}
function renderOrderProducts() {
    const query=document.getElementById('order-search').value.toLowerCase(),category=document.getElementById('order-category').value;
    const matches=products.filter(p=>(!category||p.category===category)&&(p.name+' '+p.category).toLowerCase().includes(query));
    document.getElementById('order-product-grid').innerHTML=matches.length?matches.map(p=>`<article class="order-card ${(orderQuantities[p.id]||0)>0?'chosen':''}"><div class="order-picture"><img src="${escapeHtml(productImage(p))}" alt=""><span>${p.stock} dona mavjud</span></div><h3>${escapeHtml(p.name)}</h3><p>${money(p.price)} so‘m</p><div class="order-quantity"><button type="button" data-product="${p.id}" data-delta="-1" aria-label="${escapeHtml(p.name)} sonini kamaytirish" ${(orderQuantities[p.id]||0)===0?'disabled':''}>−</button><output aria-label="${escapeHtml(p.name)} soni">${orderQuantities[p.id]||0}</output><button type="button" data-product="${p.id}" data-delta="1" aria-label="${escapeHtml(p.name)} sonini oshirish" ${(orderQuantities[p.id]||0)>=p.stock?'disabled':''}>+</button></div></article>`).join(''):'<p class="empty">Mahsulot topilmadi.</p>';
    document.querySelectorAll('.order-quantity button').forEach(button=>button.onclick=()=>{
        if(orderBusy)return;
        const id=Number(button.dataset.product),p=products.find(p=>p.id===id),value=(orderQuantities[id]||0)+Number(button.dataset.delta);
        if(value<0||value>p.stock)return;
        if(value===0)delete orderQuantities[id];else orderQuantities[id]=value;
        orderKey=crypto.randomUUID();const action=button.dataset.delta;
        renderOrderProducts();document.querySelector(`.order-quantity button[data-product="${id}"][data-delta="${action}"]:not(:disabled)`)?.focus({preventScroll:true});
    });
    const count=Object.values(orderQuantities).reduce((a,b)=>a+b,0);
    const total=products.reduce((sum,p)=>sum+(orderQuantities[p.id]||0)*Number(p.price),0);
    document.getElementById('order-summary').textContent=`${count} dona · ${money(total)} so‘m`;
    document.getElementById('save-bar-order').disabled=count===0||orderBusy;
}
document.getElementById('close-bar-order').onclick=()=>{if(!orderBusy)barOrderDialog.close();};
barOrderDialog.addEventListener('cancel',e=>{if(orderBusy)e.preventDefault();});
document.getElementById('order-search').oninput=renderOrderProducts;
document.getElementById('order-category').onchange=renderOrderProducts;
document.getElementById('order-device').onchange=()=>{orderKey=crypto.randomUUID();};
document.getElementById('save-bar-order').onclick=async()=>{
    if(orderBusy)return;
    orderBusy=true;document.getElementById('save-bar-order').disabled=true;
    const target=tables.find(t=>t.id===Number(document.getElementById('order-device').value));
    try{
        const result=await post('/bar/sale/',{request_key:orderKey,defer_payment:true,table_id:target?.id||null,session_id:target?.session_id||null,items:Object.entries(orderQuantities).map(([id,quantity])=>({id:Number(id),quantity}))});
        orderQuantities={};orderKey=crypto.randomUUID();products.splice(0,products.length,...result.products);barOrderDialog.close();renderProducts();toast('Mahsulotlar hisobga qo‘shildi. To‘lov keyin tasdiqlanadi.');
        if(!editing)location.reload();
    }catch(error){document.getElementById('order-error').textContent=error.message;}
    finally{orderBusy=false;renderOrderProducts();}
};
document.querySelectorAll('.pay-bar').forEach(button=>button.onclick=async()=>{button.disabled=true;try{await post(`/bar/payment/${button.dataset.id}/`);location.reload();}catch(error){toast(error.message);button.disabled=false;}});

document.getElementById('manage-products').onclick=()=>{barOrderDialog.close();openSide('bar');};
document.getElementById('close-bar-manage').onclick=()=>document.getElementById('bar-manage-dialog').close();
const billDialog=document.getElementById('bill-dialog');
let currentBill=null,billBusy=false;
const billDate=value=>value?new Date(value).toLocaleString('uz-UZ',{timeZone:'Asia/Tashkent',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';
async function openBill(kind,id) {
    if(!billDialog.open)billDialog.showModal();
    currentBill=null;document.getElementById('bill-pay').hidden=true;document.getElementById('bill-stop').hidden=true;
    document.getElementById('bill-content').innerHTML='<p class="empty">Hisob yuklanmoqda…</p>';document.getElementById('bill-error').textContent='';
    try{
        const response=await fetch(`/bill/${kind}/${id}/`);
        if(!response.ok||response.redirected)throw new Error('Hisobni yuklab bo‘lmadi.');
        const bill=await response.json();currentBill={...bill,kind,id};
        document.getElementById('bill-title').textContent=`${bill.name} · Hisob #${id}`;
        document.getElementById('bill-content').innerHTML=`${bill.session_id?`<div class="bill-game"><h3>O‘yin tafsilotlari</h3><p>${billDate(bill.start)} — ${bill.active?'Davom etmoqda':billDate(bill.end)}</p><strong>${duration(bill.seconds)} · ${money(bill.game)} so‘m</strong></div>`:''}<h3>Olingan mahsulotlar</h3><div class="bill-items">${bill.items.length?`<table><thead><tr><th>Mahsulot</th><th>Narxi</th><th>Soni</th><th>Jami</th><th>Holati</th></tr></thead><tbody>${bill.items.map(i=>`<tr><td>${escapeHtml(i.name)}<small>Buyurtma #${i.order}</small></td><td>${money(i.price)}</td><td>${i.quantity}</td><td>${money(i.total)} so‘m</td><td>${i.paid?'To‘langan':'Kutilmoqda'}</td></tr>`).join('')}</tbody></table>`:'<p>Bar mahsulotlari olinmagan.</p>'}</div><div class="bill-totals"><p>O‘yin <strong>${money(bill.game)} so‘m</strong></p><p>Bar <strong>${money(bill.bar)} so‘m</strong></p><p>Umumiy hisob <strong>${money(bill.total)} so‘m</strong></p><p>Oldin to‘langan <strong>${money(bill.paid)} so‘m</strong></p><p class="bill-due">${bill.active?'Joriy qoldiq':'To‘lanadigan jami'} <strong>${money(bill.due)} so‘m</strong></p></div>${bill.active?'<p>O‘yin davom etmoqda. Yakunlangach aniq jami hisob chiqadi.</p>':''}`;
        document.getElementById('bill-stop').hidden=!bill.active;
        const pay=document.getElementById('bill-pay');pay.hidden=bill.active||Number(bill.due)===0;pay.textContent=`${money(bill.due)} so‘m · To‘lovni qabul qilish`;
    }catch(error){document.getElementById('bill-content').textContent=error.message;}
}
document.querySelectorAll('.bill-open').forEach(button=>button.onclick=()=>openBill(button.dataset.kind,button.dataset.id));
document.getElementById('close-bill').onclick=()=>{if(!billBusy)billDialog.close();};
billDialog.addEventListener('cancel',event=>{if(billBusy)event.preventDefault();});
document.getElementById('bill-pay').onclick=async function(){
    if(!currentBill||billBusy)return;
    billBusy=true;this.disabled=true;
    try{await post(`/bill/${currentBill.kind}/${currentBill.id}/`,{due:currentBill.due,unpaid_sales:currentBill.unpaid_sales});location.reload();}
    catch(error){document.getElementById('bill-error').textContent=error.message;}
    finally{billBusy=false;this.disabled=false;}
};
document.getElementById('bill-stop').onclick=async function(){
    if(!currentBill||billBusy)return;
    billBusy=true;this.disabled=true;
    try{await post(`/stop/${currentBill.table_id}/`);await openBill(currentBill.kind,currentBill.id);await syncState();}
    catch(error){document.getElementById('bill-error').textContent=error.message;}
    finally{billBusy=false;this.disabled=false;}
};

document.querySelectorAll('.bill-pay-direct').forEach(button=>button.onclick=async()=>{
    button.disabled=true;
    try{
        await post(`/bill/${button.dataset.kind}/${button.dataset.id}/`,{due:button.dataset.due,unpaid_sales:button.dataset.sales?button.dataset.sales.split(',').map(Number):[]});
        location.reload();
    }catch(error){toast(error.message);button.disabled=false;}
});

function reservationTime(value){return new Date(value).toLocaleString('uz-UZ',{timeZone:'Asia/Tashkent',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});}
function openReservation(t){
    const dialog=document.getElementById('reservation-dialog'),form=document.getElementById('reservation-form');
    form.reset();form.dataset.table=t.id;
    const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tashkent',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
    const part=type=>parts.find(p=>p.type===type).value;
    const today=`${part('year')}-${part('month')}-${part('day')}`;
    form.elements.day.value=today;form.elements.day.min=today;
    document.getElementById('reservation-title').textContent=`${deviceName(t)} · Bron`;
    document.getElementById('reservation-error').textContent='';
    document.getElementById('reservation-list').innerHTML=(t.reservations||[]).map(r=>`<div class="reservation-row"><strong>${escapeHtml(r.note||r.customer||'Bron')}</strong><p>${reservationTime(r.starts_at)}</p><button type="button" class="button subtle" data-cancel-reservation="${r.id}">Bronni yopish</button></div>`).join('');
    document.querySelectorAll('[data-cancel-reservation]').forEach(button=>button.onclick=async()=>{
        button.disabled=true;
        try{const result=await post(`/reserve/${t.id}/`,{cancel:Number(button.dataset.cancelReservation)});t.reservations=result.reservations;renderMap();renderDetail();openReservation(t);}catch(error){toast(error.message);button.disabled=false;}
    });
    if(!dialog.open)dialog.showModal();
}
document.getElementById('reservation-form').onsubmit=async event=>{
    event.preventDefault();const form=event.target,button=form.querySelector('[type=submit]');button.disabled=true;
    try{
        const t=tables.find(t=>t.id===Number(form.dataset.table));
        const result=await post(`/reserve/${t.id}/`,{note:form.elements.note.value,starts_at:form.elements.day.value+'T'+form.elements.time.value+'+05:00'});
        t.reservations=result.reservations;renderMap();renderDetail();document.getElementById('reservation-dialog').close();toast('Bron saqlandi.');
    }catch(error){document.getElementById('reservation-error').textContent=error.message;}
    finally{button.disabled=false;}
};
document.getElementById('close-reservation').onclick=()=>document.getElementById('reservation-dialog').close();

document.getElementById('mobile-menu-toggle').onclick=()=>{
    const open=document.body.classList.toggle('mobile-menu-open');
    document.getElementById('mobile-menu-toggle').setAttribute('aria-expanded',String(open));
};
document.getElementById('mobile-menu-shade').onclick=()=>{document.body.classList.remove('mobile-menu-open');document.getElementById('mobile-menu-toggle').setAttribute('aria-expanded','false');};
window.matchMedia('(max-width: 760px)').addEventListener('change',event=>{
    if(event.matches)closeSide();else openSide('table');
});
