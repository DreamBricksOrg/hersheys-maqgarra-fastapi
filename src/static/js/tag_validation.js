var html5QrCode = null;
const qrScanContainer = document.getElementById("Qr-reader-container")
const btn_scan = document.getElementById("btn_scan")
const modal_alert = document.getElementById("modal_alert")
const modal_success = document.getElementById("modal_success")
const modal_error = document.getElementById("modal_error")
const tbody_element = document.getElementById('queue_table').getElementsByTagName('tbody')[0];

btn_scan.addEventListener("click", function () {
    startScan();
})
function onScanSuccess(decodedText, decodedResult) {
    // handle the scanned code as you like, for example:
    console.log("Code matched = ${decodedText}", decodedResult);
    fetch(`/api/tags/${decodedText}`, {
        method: 'GET',
        headers: {
            'x-api-key': 'capibarra-tablet-03',
            'x-device-id': 'tablet-03',
            'Content-Type': 'application/json'
        }
    }).then(resp => {
        if (!resp.ok) {
            throw new Error(`HTTP error: ${resp.status}`)
        }
        return resp.json()
    }).then(response => {
        console.log(response);
        if (response.available_for_play) {
            modal_success.style.display = "flex";
            setTimeout(() => { hideElement(modal_success) }, 2000);
            deactivateTag(decodedText);
        }
        else {
            modal_error.style.display = "flex";
            setTimeout(() => { hideElement(modal_error) }, 2000);
        }
    }).catch(error => {
        modal_alert.style.display = "flex";
        setTimeout(() => { hideElement(modal_alert) }, 2000);
    });
    html5QrCode.stop();
    btn_scan.style.display = "flex"
}

async function deactivateTag(tag_key) {
    fetch(`/api/tags/${tag_key}/deactivate`, {
        method: 'POST',
        headers: {
            'x-api-key': 'capibarra-tablet-03',
            'x-device-id': 'tablet-03',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ "reason": "used_for_play" })
    }).then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`)
        }
    });
}

async function startScan() {
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

function test_queue() {
    for (let x = 1; x < 15; x++) {
        let newRow = tbody_element.insertRow(-1);

        // 3. Insert cells (<td>) into the new row
        let cell_position = newRow.insertCell(0);
        let cell_code = newRow.insertCell(1);
        newRow.insertCell(2).textContent = "-";
        let cell_tag = newRow.insertCell(3);

        cell_position.textContent = `${x + 1}.`;
        cell_code.textContent = `1000000${x + 1}`;
        cell_tag.textContent = `${Math.floor(Math.random() * 10)}`;
    }
}

test_queue()
// 4. Add text or HTML to the cell
newCell.textContent = 'New Data';
function hideElement(element) {
    element.style.display = "none";
    //startScan()
}