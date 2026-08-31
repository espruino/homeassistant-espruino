class EspruinoPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._unsub = null;
    this._subscribed = false;
    this._connectedAddress = null;
    this._iframe = null;
    this._onMessage = this._onMessage.bind(this);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._subscribed && this._hass && this._hass.connection) {
      this._subscribe();
    }
  }

  connectedCallback() {
    window.addEventListener("message", this._onMessage);
    this._render();
    if (!this._subscribed && this._hass && this._hass.connection) {
      this._subscribe();
    }
  }

  disconnectedCallback() {
    window.removeEventListener("message", this._onMessage);
    if (this._unsub) {
      this._unsub();
      this._unsub = null;
      this._subscribed = false;
    }
  }

  async _subscribe() {
    if (this._subscribed || !this._hass || !this._hass.connection) return;
    this._subscribed = true;
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (event) => this._handleBackendEvent(event),
        { type: "espruino/subscribe" }
      );
    } catch (err) {
      console.error("Failed to subscribe to Espruino events:", err);
      this._subscribed = false;
    }
  }

  _render() {
    if (this._iframe) return;
    this.style.display = "block";
    this.style.width = "100%";
    this.style.height = "100vh";
    this.style.position = "relative";
    this.style.top = "0px";
    this.style.left = "0px";
    this.style.right = "0px";
    this.style.bottom = "0px";
    this.style.inset = "unset";

    const iframe = document.createElement("iframe");
    iframe.src = "https://www.espruino.com/ide/";
    iframe.style.width = "100%";
    iframe.style.height = "100%";
    iframe.style.border = "none";
    iframe.allow = "usb; bluetooth";
    this.appendChild(iframe);
    this._iframe = iframe;
  }

  _postToIde(msg) {
    if (this._iframe && this._iframe.contentWindow) {
      msg.for = "ide";
      this._iframe.contentWindow.postMessage(msg, "*");
    }
  }

  _handleBackendEvent(event) {
    if (!event) return;
    if (event.type === "data") {
      this._postToIde({ type: "receive", data: event.data });
    } else if (event.type === "connection") {
      if (!event.connected && event.address === this._connectedAddress) {
        this._connectedAddress = null;
        this._postToIde({ type: "disconnected" });
      }
    }
  }

  async _onMessage(e) {
    const event = e.data;
    if (!event || typeof event !== "object" || event.from !== "ide") {
      return;
    }

    switch (event.type) {
      case "init":
        this._postToIde({ type: "initialised" });
        this._postToIde({ type: "setMaxWriteLength", data: 20 });
        break;

      case "getPorts":
        try {
          const devices = await this._hass.connection.sendMessagePromise({
            type: "espruino/devices",
          });
          const ports = (devices || []).map((dev) => ({
            path: dev.address,
            description: `${dev.name || "Espruino"} (${dev.address})`,
            type: "bluetooth",
          }));
          this._postToIde({ type: "ports", data: ports });
        } catch (err) {
          console.error("Error getting Espruino devices:", err);
          this._postToIde({ type: "ports", data: [] });
        }
        break;

      case "connect":
        try {
          const address = event.data;
          this._connectedAddress = address;
          await this._hass.connection.sendMessagePromise({
            type: "espruino/connect",
            address: address,
          });
          this._postToIde({ type: "connected" });
        } catch (err) {
          console.error("Error connecting to Espruino device:", err);
          this._connectedAddress = null;
          this._postToIde({ type: "disconnected" });
        }
        break;

      case "write":
        try {
          let dataStr = event.data;
          if (dataStr instanceof ArrayBuffer) {
            const bytes = new Uint8Array(dataStr);
            let binary = "";
            for (let i = 0; i < bytes.byteLength; i++) {
              binary += String.fromCharCode(bytes[i]);
            }
            dataStr = binary;
          }
          await this._hass.connection.sendMessagePromise({
            type: "espruino/write",
            address: this._connectedAddress,
            data: dataStr,
          });
          this._postToIde({ type: "written" });
        } catch (err) {
          console.error("Error writing to Espruino device:", err);
        }
        break;

      case "disconnect":
        try {
          if (this._connectedAddress) {
            await this._hass.connection.sendMessagePromise({
              type: "espruino/disconnect",
              address: this._connectedAddress,
            });
            this._connectedAddress = null;
          }
        } catch (err) {
          console.error("Error disconnecting Espruino device:", err);
        }
        this._postToIde({ type: "disconnected" });
        break;
    }
  }
}

customElements.define("espruino-panel", EspruinoPanel);
