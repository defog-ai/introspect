export function setupWebsocketManager(
  url = `ws://${process.env.NEXT_PUBLIC_AGENTS_ENDPOINT}/editor`,
  onMessage = () => {}
) {
  let socket = null;
  let _url = url;
  let log = false;
  let interval = null;

  function connect() {
    return reconnect();
  }

  function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
  }

  function reconnect() {
    return new Promise((resolve, reject = () => {}) => {
      clearInterval(interval);

      if (socket && socket.close) {
        socket.close();
      }

      socket = new WebSocket(url);

      socket.onopen = function () {
        console.log("reconnected to", url);

        clearInterval(interval);
        resolve();
      };

      socket.onerror = function () {
        // reject("Can't connect to", url);
      };

      socket.onmessage = onMessage;

      socket.onclose = function (e) {
        if (log) {
          console.log("closed", url);
          console.log("reconnecting to", url);
        }
        // connect in 1 second

        interval = setTimeout(() => {
          reconnect();
        }, 1000);
      };
    });
  }

  function changeUrlAndReconnect(newUrl) {
    url = newUrl;
    return reconnect();
  }

  function send(data) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(data));
    }
  }

  function logging(on = false) {
    log = on;
  }

  return connect()
    .then(() => {
      return {
        send,
        reconnect,
        changeUrlAndReconnect,
        isConnected,
        logging,
        interval,
      };
    })
    .catch((e) => {});
}
