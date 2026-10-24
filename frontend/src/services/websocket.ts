export class SessionWebSocket {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private onMessageCallback: (msg: any) => void;
  private isClosedExplicitly = false;

  constructor(sessionId: string, onMessage: (msg: any) => void) {
    this.sessionId = sessionId;
    this.onMessageCallback = onMessage;
    this.connect();
  }

  private connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${this.sessionId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log(`[WS] Connected to session ${this.sessionId}`);
    };

    this.ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.onMessageCallback(parsed);
      } catch (err) {
        console.error('[WS] Parse error:', err);
      }
    };

    this.ws.onerror = (err) => {
      console.warn('[WS] Socket error:', err);
    };

    this.ws.onclose = () => {
      console.log(`[WS] Disconnected from session ${this.sessionId}`);
      if (!this.isClosedExplicitly) {
        // Attempt reconnect in 2 seconds if still relevant
        setTimeout(() => {
          if (!this.isClosedExplicitly) {
            this.connect();
          }
        }, 2000);
      }
    };
  }

  public close() {
    this.isClosedExplicitly = true;
    if (this.ws) {
      this.ws.close();
    }
  }
}
