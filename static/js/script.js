/**
 * Client-Side JavaScript for
 * Blockchain-Integrated Multimodal Biometric Electronic Voting System
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Bootstrap Tooltips & Popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Candidate Selection on Voting Ballot Page
    const candidateCards = document.querySelectorAll('.candidate-select-card');
    const submitVoteBtn = document.getElementById('proceedToConfirmBtn');

    candidateCards.forEach(card => {
        card.addEventListener('click', function () {
            candidateCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');

            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
            }

            if (submitVoteBtn) {
                submitVoteBtn.removeAttribute('disabled');
            }
        });
    });

    // 3. Copy to Clipboard Utility
    const copyButtons = document.querySelectorAll('.btn-copy-hash');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const targetText = this.getAttribute('data-hash') || this.innerText;
            navigator.clipboard.writeText(targetText).then(() => {
                const originalHtml = this.innerHTML;
                this.innerHTML = '<i class="fa-solid fa-check text-success"></i> Copied!';
                setTimeout(() => {
                    this.innerHTML = originalHtml;
                }, 2000);
            }).catch(err => {
                console.error("Clipboard copy failed: ", err);
            });
        });
    });

    // 4. Auto-dismiss alerts after 6 seconds
    const autoAlerts = document.querySelectorAll('.alert-dismissible');
    autoAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });
});

/**
 * Webcam Manager Class for Biometric Capturing
 */
class BiometricCamera {
    constructor(videoId, canvasId, hiddenInputId, statusId) {
        this.video = document.getElementById(videoId);
        this.canvas = document.getElementById(canvasId);
        this.hiddenInput = document.getElementById(hiddenInputId);
        this.statusElement = document.getElementById(statusId);
        this.stream = null;
    }

    startCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showStatus("Webcam not supported in this browser environment. Please use file upload or Demo Mode.", "warning");
            return;
        }

        this.showStatus("Initializing camera...", "info");
        navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 } } })
            .then(stream => {
                this.stream = stream;
                if (this.video) {
                    this.video.srcObject = stream;
                    this.video.play();
                }
                this.showStatus("Camera active. Align face/print inside frame and capture.", "success");
            })
            .catch(err => {
                console.warn("Camera access denied or hardware unavailable: ", err);
                this.showStatus("Webcam unavailable. You may upload a biometric photo or use Demo Mode.", "secondary");
            });
    }

    captureSnapshot() {
        if (!this.video || !this.canvas || !this.stream) {
            this.showStatus("Cannot capture: Camera stream not active.", "danger");
            return false;
        }

        const width = this.video.videoWidth || 320;
        const height = this.video.videoHeight || 240;
        this.canvas.width = width;
        this.canvas.height = height;

        const ctx = this.canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0, width, height);

        const dataUrl = this.canvas.toDataURL('image/png');
        if (this.hiddenInput) {
            this.hiddenInput.value = dataUrl;
        }

        this.showStatus("Biometric frame captured successfully!", "success");
        return true;
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    showStatus(message, type) {
        if (this.statusElement) {
            this.statusElement.innerHTML = `<div class="badge bg-${type} p-2 text-wrap">${message}</div>`;
        }
    }
}
