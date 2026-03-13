var html5QrCode = null;

function onScanSuccess(decodedText, decodedResult) {
    const modal_alert = document.getElementById("modal_alert")
    const modal_success = document.getElementById("modal_success")
    const modal_error = document.getElementById("modal_error")
    // handle the scanned code as you like, for example:
    console.log("Code matched = ${decodedText}", decodedResult);
    fetch("/tags/validate", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code: decodedText })
    }).then(resp => resp.json())
        .then(response => {
            console.log(response);
            if (response == "Valid") {
                modal_success.style.display = "flex";
                setTimeout(() => { hideElement(modal_success) }, 2000);
            }
            else if (response == "Invalid") {
                modal_error.style.display = "flex";
                setTimeout(() => { hideElement(modal_error) }, 2000);

            }
        }).catch(error => {
            modal_alert.style.display = "flex";
            setTimeout(() => { hideElement(modal_alert) }, 2000);
        });
    html5QrCode.stop();
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