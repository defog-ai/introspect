import { onConnect } from "y-partykit";
import { setupWebsocketManager } from "./websocket-manager";
import * as Y from "yjs";

const docsEndpoint = "ws://agents-python-server:1235/docs";

const getDocsEndpoint = "http://agents-python-server:1235/get_doc";

export default {
  async onConnect(ws, room, context) {
    // get doc id from uri
    const params = new URLSearchParams(ws.uri.split("?").pop());
    const docId = params.get("doc_id");
    const apiToken = params.get("api_token");
    const username = params.get("username");
    const docsBackend = await setupWebsocketManager(docsEndpoint);

    console.log("onConnect", docId, apiToken, username);

    return await onConnect(ws, room, {
      load() {
        return fetch(getDocsEndpoint, {
          method: "POST",
          body: JSON.stringify({
            api_key: apiToken,
            doc_id: docId,
            col_name: "doc_uint8",
            username: username,
          }),
        })
          .then((d) => d.json())
          .then((d) => {
            const yDoc = new Y.Doc();
            try {
              let uint8Array = [];
              if (d.doc_data.doc_uint8) {
                const obj = JSON.parse(d.doc_data.doc_uint8);

                // Get the bytes array
                const byteValues = obj.bytes;

                // Create Uint8Array from bytes
                uint8Array = new Uint8Array(byteValues);
                Y.applyUpdate(yDoc, uint8Array);
              }

              return yDoc;
            } catch (e) {
              return null;
            }
          })
          .catch((e) => console.log(e));
      },
      callback: {
        async handler(yDoc) {
          const yjsState = Y.encodeStateAsUpdate(yDoc);

          const title = yDoc.getMap("document-title").get("title");

          try {
            // write to db
            docsBackend.send({
              doc_uint8: JSON.stringify({ bytes: Array.from(yjsState) }),
              doc_id: docId,
              doc_title: title,
              username: username,
              api_key: apiToken,
            });
          } catch (e) {
            // console.log(e);
          }
        },
      },
    });
  },
};
