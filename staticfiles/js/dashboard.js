const timers = {};

// Start session
function startSession(tableId){
    fetch(`/start/${tableId}/`, {
        method:'POST',
        headers:{'X-CSRFToken': csrftoken}
    }).then(res=>res.json()).then(data=>{
        if(data.success){
            const startBtn = document.getElementById(`start-${tableId}`);
            startBtn.disabled = true;                // bosib bo‘lmasligi
            startBtn.classList.add('btn-inactive');  // kulrang qilish

            const stopBtn = document.getElementById(`stop-${tableId}`);
            stopBtn.disabled = false;

            const tableCard = document.getElementById(`table-${tableId}`);
            tableCard.classList.add('active');
            tableCard.classList.remove('inactive');

            const timerEl = document.getElementById(`timer-${tableId}`);
            timerEl.textContent = data.start_time;

            const priceEl = document.getElementById(`price-${tableId}`);
            priceEl.textContent = 0;
        }
    });
}


// Stop session
function stopSession(tableId){
    fetch(`/stop/${tableId}/`, {
        method:'POST',
        headers:{'X-CSRFToken': csrftoken}
    }).then(res=>res.json()).then(data=>{
        if(data.success){
            document.getElementById(`start-${tableId}`).disabled = false;
            document.getElementById(`stop-${tableId}`).disabled = true;
            document.getElementById(`timer-${tableId}`).textContent = "00:00";
            document.getElementById(`price-${tableId}`).textContent = 0;
            document.getElementById(`table-${tableId}`).classList.remove('active');
            document.getElementById(`table-${tableId}`).classList.add('inactive');

            // Waiting payment listga qo'shish
            const li = document.createElement("li");
            li.id = `session-${data.session.id}`;
            li.innerHTML = `${data.session.table_number} - ${data.session.start_time} - ${data.session.end_time} - ${data.session.price} <button onclick="paySession(${data.session.id})">x</button>`;
            document.getElementById(`session-list-${tableId}`).appendChild(li);

            document.getElementById("total-income").textContent = `Bugungi foyda: ${data.total_income} so'm`;
            tableCard.classList.add('inactive');
            tableCard.classList.remove('active');

        }
    });
}

// Pay session
function paySession(sessionId){
    fetch(`/payment/${sessionId}/`, {
        method:'POST',
        headers:{'X-CSRFToken': csrftoken}
    }).then(res=>res.json()).then(data=>{
        if(data.success){
            const li = document.getElementById(`session-${sessionId}`);
            li.remove();
            const paidList = document.getElementById("paid-sessions-list");
            const paidLi = document.createElement("li");
            paidLi.textContent = `${data.index} - Table ${data.table_number} - ${data.start_time} - ${data.end_time} - ${data.price}`;
            paidList.appendChild(paidLi);

            document.getElementById("total-income").textContent = `Bugungi foyda: ${data.total_income} so'm`;
        }
    });
}

function updatePrice(tableId, startTime, pricePerHour) {
    const priceEl = document.getElementById(`price-${tableId}`);
    const now = new Date();
    const diffHours = (now - startTime)/3600000;
    const price = Math.ceil(diffHours*pricePerHour/1000)*1000;
    priceEl.textContent = price;
}

function startTimer(tableId, startTimeStr, pricePerHour){
    const startTime = new Date(startTimeStr);
    updatePrice(tableId, startTime, pricePerHour); // darhol price ko'rsatish
    if(timers[tableId]) clearInterval(timers[tableId]);
    timers[tableId] = setInterval(()=>{
        updatePrice(tableId, startTime, pricePerHour);
    }, 60000); // har 1 daqiqa
}

function initializeTables(){
    document.querySelectorAll('.table-card').forEach(card => {
        const tableId = card.dataset.tableId;
        const pricePerHour = parseFloat(card.dataset.pricePerHour);
        const startTimeStr = card.dataset.activeStart;
        const startBtn = document.getElementById(`start-${tableId}`);
        const stopBtn = document.getElementById(`stop-${tableId}`);

        // Agar active session bor bo'lsa
        if(startTimeStr && startTimeStr !== "None"){
            startBtn.disabled = true;
            stopBtn.disabled = false;
            card.classList.add('active');
            card.classList.remove('inactive');

            // Timerni boshlash
            const startTime = new Date(startTimeStr);
            if(timers[tableId]) clearInterval(timers[tableId]);
            timers[tableId] = setInterval(()=>{
                const now = new Date();
                const diffHours = (now - startTime)/3600000;
                const price = Math.ceil(diffHours * pricePerHour / 1000) * 1000;
                document.getElementById(`price-${tableId}`).textContent = price;

                // Timerni ham har daqiqa yangilash (soat:minut)
                const h = startTime.getHours().toString().padStart(2,'0');
                const m = startTime.getMinutes().toString().padStart(2,'0');
                document.getElementById(`timer-${tableId}`).textContent = `${h}:${m}`;
            }, 60000);

            // Darhol yangilash
            const now = new Date();
            const diffHours = (now - startTime)/3600000;
            const price = Math.ceil(diffHours * pricePerHour / 1000) * 1000;
            document.getElementById(`price-${tableId}`).textContent = price;

            const h = startTime.getHours().toString().padStart(2,'0');
            const m = startTime.getMinutes().toString().padStart(2,'0');
            document.getElementById(`timer-${tableId}`).textContent = `${h}:${m}`;

        } else {
            // Bosh table
            startBtn.disabled = false;
            stopBtn.disabled = true;
            card.classList.remove('active');
            card.classList.add('inactive');
            document.getElementById(`timer-${tableId}`).textContent = "00:00";
            document.getElementById(`price-${tableId}`).textContent = 0;
            if(timers[tableId]) clearInterval(timers[tableId]);
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initializeTables(); // page load bo‘lganda active sessionlarni yangilash
});

