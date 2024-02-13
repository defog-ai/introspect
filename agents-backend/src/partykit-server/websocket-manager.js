export function setupWebsocketManager(
  url = `ws://agents-nginx/editor`,
  onMessage = () => {}
) {
  let socket = null;
  let log = false;

  function connect() {
    return reconnect();
  }

  function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
  }

  function reconnect() {
    return new Promise((resolve, reject) => {
      if (socket && socket.close) {
        socket.close();
      }

      socket = new WebSocket(url);
      socket.onopen = function () {
        if (log) {
          console.log("reconnected to", url);
        }
        resolve();
      };

      socket.onerror = function () {
        reject("Can't connect to", url);
      };

      socket.onmessage = onMessage;

      socket.onclose = function (e) {
        if (log) {
          console.log("closed", url);
          console.log("reconnecting to", url);
        }
        // reconnect();
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

  return connect().then(() => {
    return {
      send,
      reconnect,
      changeUrlAndReconnect,
      isConnected,
      logging,
    };
  });
}
