(function () {
  const INITIAL_RECONNECT_DELAY_MS = 5000;
  const HEARTBEAT_INTERVAL_MS = 30000;
  const MAX_RECONNECT_DELAY_MS = 60000;

  function getCookie(name) {
    const cookie = document.cookie
      .split(";")
      .map((entry) => entry.trim())
      .find((entry) => entry.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
  }

  function formatTimestamp(value) {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return date.toLocaleString();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function isAuctionEvent(notification) {
    return ["auction_update", "status_change", "new_auction"].includes(
      notification.notificationType
    );
  }

  document.addEventListener("DOMContentLoaded", function () {
    const bell = document.getElementById("notificationBell");
    const badge = document.getElementById("notificationUnreadBadge");
    const dropdown = document.getElementById("notificationDropdown");
    const list = document.getElementById("notificationList");
    const statusDot = document.getElementById("notificationConnectionStatus");

    if (!bell || !badge || !dropdown || !list || !statusDot) {
      return;
    }

    let notifications = [];
    let socket = null;
    let reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
    let reconnectTimer = null;
    let heartbeatTimer = null;
    let manualClose = false;

    function setStatus(status) {
      statusDot.classList.remove("bg-success", "bg-warning", "bg-danger");
      if (status === "connected") {
        statusDot.classList.add("bg-success");
        statusDot.setAttribute("aria-label", "Notification connection connected");
        return;
      }
      if (status === "reconnecting") {
        statusDot.classList.add("bg-warning");
        statusDot.setAttribute("aria-label", "Notification connection reconnecting");
        return;
      }
      statusDot.classList.add("bg-danger");
      statusDot.setAttribute("aria-label", "Notification connection failed");
    }

    function updateBadge() {
      const unreadCount = notifications.filter((item) => !item.isRead).length;
      badge.textContent = String(unreadCount);
      badge.classList.toggle("d-none", unreadCount === 0);
    }

    function renderNotifications() {
      if (!notifications.length) {
        list.innerHTML =
          '<div class="px-3 py-3 text-muted small">No unread notifications.</div>';
        return;
      }

      list.innerHTML = notifications
        .map(
          (notification) => {
            const label = escapeHtml(
              notification.propertyAddress ||
                notification.title ||
                "Auction alert"
            );
            const eventType = escapeHtml(
              notification.notificationType || "auction_update"
            );
            const createdAt = escapeHtml(formatTimestamp(notification.createdAt));
            const notificationId = escapeHtml(notification.id);
            return `
          <div class="list-group-item">
            <div class="d-flex justify-content-between align-items-start gap-2">
              <div class="small">
                <div class="fw-semibold">${label}</div>
                <div>${eventType} • ${createdAt}</div>
              </div>
              <button type="button" class="btn btn-sm btn-link p-0 notification-mark-read" data-id="${notificationId}">Mark read</button>
            </div>
          </div>`;
          }
        )
        .join("");
    }

    function upsertNotification(notification) {
      if (!notification || !notification.id) {
        return;
      }
      if (!isAuctionEvent(notification)) {
        return;
      }
      const existingIndex = notifications.findIndex(
        (item) => item.id === notification.id
      );
      if (existingIndex >= 0) {
        notifications[existingIndex] = notification;
      } else {
        notifications.unshift(notification);
      }
      notifications = notifications.filter((item) => !item.isRead);
      renderNotifications();
      updateBadge();
    }

    async function fetchNotifications() {
      try {
        const response = await fetch("/api/v1/notifications", {
          credentials: "same-origin",
        });
        if (!response.ok) {
          console.error("Failed to fetch notifications:", response.status);
          return;
        }
        const data = await response.json();
        notifications = (data.notifications || []).filter(isAuctionEvent);
        renderNotifications();
        updateBadge();
      } catch (error) {
        console.error("Failed to fetch notifications:", error);
      }
    }

    async function markRead(notificationId) {
      try {
        const response = await fetch(
          `/api/v1/notifications/${notificationId}/read`,
          {
            method: "POST",
            headers: {
              "X-CSRFToken": getCookie("csrftoken"),
            },
            credentials: "same-origin",
          }
        );
        if (!response.ok) {
          console.error("Failed to mark notification read:", response.status);
          return;
        }
        notifications = notifications.filter((item) => item.id !== notificationId);
        renderNotifications();
        updateBadge();
      } catch (error) {
        console.error("Failed to mark notification read:", error);
      }
    }

    function stopHeartbeat() {
      if (heartbeatTimer) {
        window.clearInterval(heartbeatTimer);
        heartbeatTimer = null;
      }
    }

    function startHeartbeat() {
      stopHeartbeat();
      heartbeatTimer = window.setInterval(function () {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, HEARTBEAT_INTERVAL_MS);
    }

    function connectWebSocket() {
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/auctions/`);

      socket.onopen = function () {
        reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
        setStatus("connected");
        startHeartbeat();
      };

      socket.onmessage = function (event) {
        let payload = null;
        try {
          payload = JSON.parse(event.data);
        } catch (error) {
          return;
        }

        if (payload.type === "pong") {
          return;
        }

        if (payload.type === "new_auction" || payload.type === "status_change") {
          upsertNotification(payload.notification || payload);
        }
      };

      socket.onclose = function () {
        stopHeartbeat();
        if (manualClose) {
          return;
        }
        setStatus("reconnecting");
        reconnectTimer = window.setTimeout(function () {
          connectWebSocket();
        }, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY_MS);
      };

      socket.onerror = function () {
        setStatus("failed");
      };
    }

    bell.addEventListener("click", function () {
      dropdown.classList.toggle("show");
      bell.setAttribute(
        "aria-expanded",
        dropdown.classList.contains("show") ? "true" : "false"
      );
    });

    document.addEventListener("click", function (event) {
      if (!dropdown.contains(event.target) && !bell.contains(event.target)) {
        dropdown.classList.remove("show");
        bell.setAttribute("aria-expanded", "false");
      }
    });

    list.addEventListener("click", function (event) {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const notificationId = target.dataset.id;
      if (!notificationId || !target.classList.contains("notification-mark-read")) {
        return;
      }
      markRead(notificationId);
    });

    window.addEventListener("beforeunload", function () {
      manualClose = true;
      stopHeartbeat();
      if (socket) {
        socket.close();
      }
    });

    setStatus("failed");
    fetchNotifications();
    connectWebSocket();
  });
})();
