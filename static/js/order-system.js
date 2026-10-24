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

  function drawQr(canvas) {
    const modules = 29;
    const quiet = 2;
    const cell = 8;
    const total = modules + quiet * 2;
    const context = canvas.getContext("2d");
    const seedText = canvas.dataset.qrSeed || "SisaBijak";

    canvas.width = total * cell;
    canvas.height = total * cell;
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);

    let seed = 2166136261;
    for (let index = 0; index < seedText.length; index += 1) {
      seed ^= seedText.charCodeAt(index);
      seed = Math.imul(seed, 16777619);
    }

    function randomBit() {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      return (seed >>> 30) & 1;
    }

    function moduleRect(x, y, color = "#050605") {
      context.fillStyle = color;
      context.fillRect((x + quiet) * cell, (y + quiet) * cell, cell, cell);
    }

    function inFinderZone(x, y) {
      return (
        (x <= 7 && y <= 7) ||
        (x >= modules - 8 && y <= 7) ||
        (x <= 7 && y >= modules - 8)
      );
    }

    for (let y = 0; y < modules; y += 1) {
      for (let x = 0; x < modules; x += 1) {
        if (inFinderZone(x, y)) continue;
        const timing = (x === 6 || y === 6) && (x + y) % 2 === 0;
        const data = randomBit() || ((x * 3 + y * 5 + seedText.length) % 11 === 0);
        if (timing || data) moduleRect(x, y);
      }
    }

    function finder(x, y) {
      context.fillStyle = "#050605";
      context.fillRect((x + quiet) * cell, (y + quiet) * cell, 7 * cell, 7 * cell);
      context.fillStyle = "#fff";
      context.fillRect((x + quiet + 1) * cell, (y + quiet + 1) * cell, 5 * cell, 5 * cell);
      context.fillStyle = "#050605";
      context.fillRect((x + quiet + 2) * cell, (y + quiet + 2) * cell, 3 * cell, 3 * cell);
    }

    finder(0, 0);
    finder(modules - 7, 0);
    finder(0, modules - 7);
    context.fillStyle = "#050605";
    context.fillRect((modules - 9 + quiet) * cell, (modules - 9 + quiet) * cell, 5 * cell, 5 * cell);
    context.fillStyle = "#fff";
    context.fillRect((modules - 8 + quiet) * cell, (modules - 8 + quiet) * cell, 3 * cell, 3 * cell);
    moduleRect(modules - 7, modules - 7);
  }

  document.querySelectorAll(".qr-canvas").forEach(drawQr);

  const profileTrigger = document.querySelector(".profile-trigger");
  const profileDropdown = document.getElementById("profile-dropdown");
  if (profileTrigger && profileDropdown) {
    profileTrigger.addEventListener("click", () => {
      const open = profileDropdown.hidden;
      profileDropdown.hidden = !open;
      profileTrigger.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".profile-menu")) {
        profileDropdown.hidden = true;
        profileTrigger.setAttribute("aria-expanded", "false");
      }
    });
  }

  const productCard = document.querySelector(".product-card[data-unit-price]");
  const quantityOutput = document.getElementById("quantity-value");
  const quantityInput = document.getElementById("quantity-input");
  if (productCard && quantityOutput && quantityInput) {
    const unitPrice = Number(productCard.dataset.unitPrice);
    const originalPrice = Number(productCard.dataset.originalPrice);
    const maxQuantity = Math.min(10, Number(productCard.dataset.maxStock));
    let quantity = 1;

    function updateQuantity(next) {
      quantity = Math.max(1, Math.min(maxQuantity, next));
      quantityOutput.value = String(quantity);
      quantityOutput.textContent = String(quantity);
      quantityInput.value = String(quantity);
      document.getElementById("summary-subtotal").textContent = rupiah(unitPrice * quantity);
      document.getElementById("summary-total").textContent = rupiah(unitPrice * quantity);
      document.getElementById("summary-savings").textContent = rupiah((originalPrice - unitPrice) * quantity);
      document.getElementById("summary-original").textContent = rupiah(originalPrice * quantity);
    }

    document.querySelectorAll("[data-quantity]").forEach((button) => {
      button.addEventListener("click", () => {
        updateQuantity(quantity + (button.dataset.quantity === "plus" ? 1 : -1));
      });
    });
    updateQuantity(1);
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
      } catch (_error) {
        // Polling will try again; a temporary network error should not break the page.
      }
    };
    window.setInterval(pollStatus, 2000);
  }

  document.querySelectorAll("[data-download-qr]").forEach((button) => {
    button.addEventListener("click", () => {
      const link = document.createElement("a");
      link.download = `${button.dataset.downloadQr}.jpeg`;
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
      const valid = file && file.size <= 5 * 1024 * 1024 && file.type.startsWith("image/");
      scanPayment.disabled = !valid;
      if (!file) {
        paymentFileName.textContent = "Belum ada file dipilih";
      } else if (!valid) {
        paymentFileName.textContent = "Gunakan gambar maksimal 5 MB.";
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
