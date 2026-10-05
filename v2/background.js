// The experiment does all the work; we only have to start it.
async function init() {
  try {
    const r = await browser.mu4eBridge.start();
    console.log("mu4e bridge listening on port", r.port);
  } catch (e) {
    console.error("mu4e bridge failed to start:", e);
  }
}
browser.runtime.onInstalled.addListener(init);
browser.runtime.onStartup.addListener(init);
init(); // listeners don't fire when the add-on is re-enabled
