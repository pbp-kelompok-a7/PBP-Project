(() => {
  "use strict";

  if ("scrollRestoration" in window.history) {
    window.history.scrollRestoration = "manual";
  }
  window.scrollTo(0, 0);

  const toast = document.getElementById("order-toast");
  let toastTimer;

  function showToast(message) {
    if (!toast) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add("show");
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2800);
  }

  function rupiah(value) {
    return `Rp${Math.round(value).toLocaleString("id-ID")}`;
  }


  const cartForm = document.querySelector("[data-cart-form]");
  if (cartForm) {
    const items = [...cartForm.querySelectorAll("[data-cart-item]")];
    function updateTotals() {
      let total = 0;
      let original = 0;
      items.forEach((item) => {
        const quantity = Number(item.querySelector(".cart-quantity").value) || 0;
        total += Number(item.dataset.unitPrice) * quantity;
        original += Number(item.dataset.originalPrice) * quantity;
      });
      document.getElementById("summary-subtotal").textContent = rupiah(total);
      document.getElementById("summary-total").textContent = rupiah(total);
      document.getElementById("summary-savings").textContent = rupiah(original - total);
      document.getElementById("summary-original").textContent = rupiah(original);
    }
    items.forEach((item) => {
      const input = item.querySelector(".cart-quantity");
      input.addEventListener("input", updateTotals);
      item.querySelectorAll("[data-quantity]").forEach((button) => {
        button.addEventListener("click", () => {
          const step = button.dataset.quantity === "plus" ? 1 : -1;
          input.value = Math.max(1, Math.min(10, (Number(input.value) || 1) + step));
          updateTotals();
        });
      });
    });
    updateTotals();
  }

  const timer = document.querySelector("[data-payment-deadline]");
  if (timer) {
    const deadline = Date.parse(timer.dataset.paymentDeadline);
    const countdown = document.getElementById("payment-countdown");
    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
      const seconds = String(remaining % 60).padStart(2, "0");
      countdown.textContent = `${minutes}:${seconds}`;
      if (remaining === 0) {
        document.getElementById("payment-status-label").textContent = "Waktu Pembayaran Habis";
      }
    };
    updateCountdown();
    window.setInterval(updateCountdown, 1000);
  }

  const pollContainer = document.querySelector("[data-payment-poll]");
  if (pollContainer) {
    const pollStatus = async () => {
      try {
        const response = await fetch(pollContainer.dataset.statusUrl, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
          cache: "no-store",
        });
        if (!response.ok) return;
        const result = await response.json();
        const label = document.getElementById("payment-status-label");
        if (label) label.textContent = result.status_label;
        if (result.redirect_url) window.location.href = result.redirect_url;
        else if (result.status === "expired") window.location.reload();
      } catch (_error) {
        // Polling will try again; a temporary network error should not break the page.
      }
    };
    window.setInterval(pollStatus, 2000);
  }

  document.querySelectorAll("[data-download-qr]").forEach((button) => {
    button.addEventListener("click", () => {
      const link = document.createElement("a");
      link.download = `${button.dataset.downloadQr}.png`;
      link.href = button.dataset.qrSource;
      link.click();
      showToast("SisaBayarQR berhasil diunduh.");
    });
  });

  const paymentProof = document.getElementById("payment-proof");
  const paymentFileName = document.getElementById("payment-file-name");
  const scanPayment = document.getElementById("scan-payment");
  if (paymentProof && paymentFileName && scanPayment) {
    scanPayment.disabled = true;
    paymentProof.addEventListener("change", () => {
      const [file] = paymentProof.files;
      const valid = file && file.size <= 5 * 1024 * 1024 &&
        file.type === "image/png" && file.name.toLowerCase().endsWith(".png");
      scanPayment.disabled = !valid;
      if (!file) {
        paymentFileName.textContent = "Belum ada file dipilih";
      } else if (!valid) {
        paymentFileName.textContent = "Gunakan PNG asli hasil unduhan, maksimal 5 MB.";
        paymentProof.value = "";
      } else {
        paymentFileName.textContent = file.name;
      }
    });
  }

  const tabButtons = document.querySelectorAll("[role='tab']");
  tabButtons.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabButtons.forEach((item) => {
        const selected = item === tab;
        const panel = document.getElementById(item.getAttribute("aria-controls"));
        item.setAttribute("aria-selected", String(selected));
        if (panel) panel.hidden = !selected;
      });
    });
  });

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copy);
        showToast("Kode klaim berhasil disalin.");
      } catch (_error) {
        showToast(`Kode klaim: ${button.dataset.copy}`);
      }
    });
  });
})();
