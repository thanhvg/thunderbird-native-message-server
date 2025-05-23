/*
On startup, connect to the "ping_pong" app.
*/
// let port = browser.runtime.connectNative("tb_srv");
// let port = browser.runtime.connectNative("tb_nt_msg_srv");
// let port = browser.runtime.connectNative("ping_pong");
let port = browser.runtime.connectNative("run");

console.log("starting: " + port);

port.onMessage.addListener((nativeAppMessage) => {
  console.log("Received: " + JSON.stringify(nativeAppMessage));

  // mid
  if (nativeAppMessage.type === 'mid') {
    messenger.messages.query({ headerMessageId: nativeAppMessage.payload })
      .then(result => {
      result.messages.forEach(msgHeader =>
        {
          console.log(msgHeader);
          messenger.messages.update(msgHeader.id, { read: true, });
        });
    });
  }

  //
  if (nativeAppMessage.type === 'query_read_status') {
    // payload = [mid]
    let messagePromises = nativeAppMessage.payload.map(it => messenger.messages.query({ headerMessageId: it }))

    Promise.all(messagePromises).then(
      messageLists => {
        let bag = {};
        messageLists.forEach(({ messages }) => {
          messages.forEach(it => {
            bag[it.headerMessageId] = it.read
          });
        });
        console.log(JSON.stringify(bag));
        port.postMessage({
          type: 'query_read_status',
          payload: bag
        });
      }
    )
    
  }

});

/*
Listen for the native messaging port closing.
*/
port.onDisconnect.addListener((port) => {
  if (port.error) {
    console.log(`Disconnected due to an error: ${port.error.message}`);
  } else {
    // The port closed for an unspecified reason. If this occurred right after
    // calling `browser.runtime.connectNative()` there may have been a problem
    // starting the the native messaging client in the first place.
    // https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging#troubleshooting
    console.log(`Disconnected`, port);
  }
});

/*
When the extension's action icon is clicked, send the app a message.
*/
browser.browserAction.onClicked.addListener(() => {
  console.log("Sending:  exit request");
  port.postMessage("exit");
});
