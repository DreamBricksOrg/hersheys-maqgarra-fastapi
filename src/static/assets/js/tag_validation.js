var html5QrCode = null;
const qrScanContainer = document.getElementById("Qr-reader-container")
const btn_scan = document.getElementById("btn_scan")
const modal_alert = document.getElementById("modal_alert")
const modal_overlay = document.getElementsByClassName("modal-overlay")[0]
const modal_success = document.getElementById("modal_success")
const modal_error = document.getElementById("modal_error")
const current_player_id = document.getElementById("current-player-id")
const spinner = document.getElementById("spinner")
const states = ["waiting", "requeued"]
hideLoading();
const tbody_element = document.getElementById('queue_table').getElementsByTagName('tbody')[0];

async function start() {
    startScan()
    getCurrentPlayer();
    getQueue(true);
}

btn_scan.addEventListener("click", function () {
    startScan();
})
async function onScanSuccess(decodedText, decodedResult) {
    html5QrCode.stop();
    startLoading();
    try {
        if (decodedText == "T03177") {
            await log_special_tag();
            modal_success.style.display = "flex";
            modal_overlay.style.display = "flex";
            setTimeout(() => { hideModal(modal_success) }, 2000);
        } else {
            let session_id = await getSessionWithTagKey(decodedText);
            let session = await getSession(session_id);
            let isValid = await Validate_tag(decodedText)
            if (session.status == "skipped" && isValid) {
                await Disable_tag(decodedText);
            }
            else if (isValid) {
                let goNext = await play(decodedText, session.queue_entry_id)
                if (goNext) {
                    await getNext();
                    await getCurrentPlayer()
                }
            }
            else if (isValid == false) {
                modal_error.style.display = "flex";
                modal_overlay.style.display = "flex";
                setTimeout(() => { hideModal(modal_error) }, 2000);
            }
        }
        hideLoading();
    }
    catch (error) {
        console.log(error)
        hideLoading();
        if (error.status == 409) {
            modal_error.style.display = "flex";
            modal_overlay.style.display = "flex";
            setTimeout(() => { hideModal(modal_error) }, 2000);
        }
        else {
            modal_alert.style.display = "flex";
            modal_overlay.style.display = "flex";
            setTimeout(() => { hideModal(modal_alert) }, 2000);
        }
    }
}

async function log_special_tag() {
    let resp = await fetch(`/api/tags/log_unique_tag`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    });
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }
}

async function Validate_tag(tag_key) {
    let resp = await fetch(`/api/tags/key/${tag_key}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    });
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }
    const response = await resp.json();

    if (response.available_for_play) {
        return true;
    }
    else
        return false;
}
async function Disable_tag(tag_key) {
    let resp = await fetch(`/api/tags/key/${tag_key}/deactivate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    });
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }

}
async function getSessionWithTagKey(tag_key) {

    const resp = await fetch(`/api/sessions/session/${tag_key}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    })
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }
    const response = await resp.json();
    console.log(response);
    return response.session_id
}

async function getSession(session_id) {
    const resp = await fetch(`/api/sessions/${session_id}`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    })
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }
    const response = await resp.json();
    console.log(response);
    return response
}

async function play(tag_key, player_id) {
    let resp = await fetch(`/api/queue/play`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        },
        body: JSON.stringify({ "player_id": player_id, "tag_key": tag_key })

    });
    if (!resp.ok) {
        const error = new Error("Request Failed");
        error.status = resp.status;
        throw error
    }
    let response = await resp.json();
    modal_success.style.display = "flex";
    modal_overlay.style.display = "flex";
    setTimeout(() => { hideModal(modal_success) }, 2000);
    if (response.remaining_plays == 0) {
        return true;
    }
    return false;
}

async function startScan() {
    if (html5QrCode != null && html5QrCode.getState() === Html5QrcodeScannerState.SCANNING)
        return
    btn_scan.style.display = "none"
    html5QrCode = new Html5Qrcode("reader");
    let qrboxFunction = function (viewfinderWidth, viewfinderHeight) {
        let minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
        let qrboxSize = Math.floor(minEdgeSize * 0.9); // 70% of the smaller edge
        return { width: qrboxSize, height: qrboxSize };
    }
    const config = { fps: 10, qrbox: qrboxFunction };

    html5QrCode.start({ facingMode: "user" }, config, onScanSuccess);
}

async function getCurrentPlayer() {

    const resp = await fetch(`/api/queue/current`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    })
    const response = await resp.json()
    console.log(response);
    if (response.current_queue_number != null) {
        let formatted = String(response.current_queue_number).padStart(8, '0');
        current_player_id.textContent = formatted
    }
    else {
        current_player_id.textContent = "Vazio"

    }
}

async function getQueue(loop) {
    try {
        const resp = await fetch(`/api/queue/active`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': 'capibarra-tablet-01',
                'x-device-id': 'tablet-01'
            }
        })
        const response = await resp.json()
        console.log(response);
        let queueList = response.items.filter(x => states.includes(x.status))
        let count = 1
        if (queueList.some(x => x.status == "waiting") && current_player_id.textContent == "Vazio") {
            await getNext();
            await getCurrentPlayer();
        }
        while (tbody_element.firstChild) {
            tbody_element.removeChild(tbody_element.firstChild);
        }
        queueList.forEach(element => {
            let converted_Queue_Number = String(element.queue_number).padStart(8, '0')
            if (converted_Queue_Number == current_player_id.textContent) {
                return;
            }
            let newRow = tbody_element.insertRow(-1);

            // 3. Insert cells (<td>) into the new row
            let cell_position = newRow.insertCell(0);
            let cell_code = newRow.insertCell(1);
            newRow.insertCell(2).textContent = "-";
            let cell_tag = newRow.insertCell(3);

            cell_position.textContent = `${count + 1}.`;
            cell_code.textContent = String(element.queue_number).padStart(8, '0');
            cell_tag.textContent = element.total_plays;
            count++;
        });
        if (loop == true) {
            setTimeout(() => {
                getQueue(true);
            }, 10000);
        }
    }
    catch (error) {
        console.log(error)
        if (loop == true) {
            setTimeout(() => {
                getQueue(true);
            }, 10000);
        }
    }
}

async function getNextInline() {
    const resp = await fetch(`/api/queue/skip`, {
        method: 'Post',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    })
    const response = await resp.json();
    console.log(response);
    getCurrentPlayer();
    getQueue(false);
    hideLoading()
}
async function getNext() {
    const resp = await fetch(`/api/queue/next`, {
        method: 'Post',
        headers: {
            'Content-Type': 'application/json',
            'x-api-key': 'capibarra-tablet-01',
            'x-device-id': 'tablet-01'
        }
    })
    const response = await resp.json();
    console.log(response);
    hideLoading()
}

// 4. Add text or HTML to the cell
function hideModal(element) {
    element.style.display = "none";
    modal_overlay.style.display = "none";
    startScan()
}

function startLoading() {
    spinner.style.display = "flex";
}
function hideLoading() {
    spinner.style.display = "none";
}

start();