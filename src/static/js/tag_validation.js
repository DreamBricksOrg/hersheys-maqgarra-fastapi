var html5QrCode = null;

function onScanSuccess(decodedText, decodedResult) {
    const modal_alert = document.getElementById("modal_alert")
    const modal_success = document.getElementById("modal_success")
    const modal_error = document.getElementById("modal_error")
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
    html5QrCode = new Html5Qrcode("reader");
    let qrboxFunction = function (viewfinderWidth, viewfinderHeight) {
        let minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
        let qrboxSize = Math.floor(minEdgeSize * 0.9); // 70% of the smaller edge
        return { width: qrboxSize, height: qrboxSize };
    }
    const config = { fps: 10, qrbox: qrboxFunction };

    // If you want to prefer back camera
    html5QrCode.start({ facingMode: "user" }, config, onScanSuccess);
}
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(startScan(), 3000);
}, false);

function hideElement(element) {
    element.style.display = "none";
    startScan()
}