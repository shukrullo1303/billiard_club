const timers = {};

// Start session
function startSession(tableId){
    fetch(`/start/${tableId}/`, {
        method:'POST',
        headers:{'X-CSRFToken': csrftoken}
    }).then(res=>res.json()).then(data=>{
        if(data.success){
            document.getElementById(`start-${tableId}`).disabled = true;
            document.getElementById(`stop-${tableId}`).disabled = false;
            document.getElementById(`timer-${tableId}`).textContent = data.start_time;
            document.getElementById(`price-${tableId}`).textContent = 0;
            document.getElementById(`table-${tableId}`).classList.add('active');
            document.getElementById(`table-${tableId}`).classList.remove('inactive');

            // Table card rangini active qilish
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
