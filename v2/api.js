/* Experiment API: loopback HTTP server inside Thunderbird for mu4e.
 *
 * Endpoints (all POST, JSON in/out, "Authorization: Bearer <token>"):
 *   /ping
 *   /read-status    {mids:[...]}                       -> {mid:{read,flagged}}
 *   /set-flags      {items:[{mid,read?,flagged?}]}     -> {mid: copiesTouched}
 *   /compose-fields {from,to,cc,bcc,subject,body,
 *                    inReplyTo,references,
 *                    attachments:[{path,name?,contentType?}]} -> {ok:true}
 *   /compose        {from, eml}   (experimental: import .eml, open as draft)
 *
 * Patterns marked "proven" are copied from thunderbird-mcp's api.js, which is
 * known to work.  Lines marked VERIFY are my own and untested.
 */
/* global ExtensionCommon, ChromeUtils, Services, Cc, Ci, Components */

const { MailServices } = ChromeUtils.importESModule("resource:///modules/MailServices.sys.mjs");
const { NetUtil } = ChromeUtils.importESModule("resource://gre/modules/NetUtil.sys.mjs");

const RES_HOST = "mu4e-bridge";
const PORT_BASE = 8790;
const PORT_TRIES = 10;
const MAX_BODY = 32 * 1024 * 1024;

const resProto = Cc["@mozilla.org/network/protocol;1?name=resource"]
  .getService(Ci.nsISubstitutingProtocolHandler);

// ------------------------------------------------------------ small helpers

function createLocalFile(path) {                       // proven
  const f = Cc["@mozilla.org/file/local;1"].createInstance(Ci.nsIFile);
  f.initWithPath(path);
  return f;
}

function timingSafeEqual(a, b) {                       // proven
  const x = String(a), y = String(b);
  let r = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    r |= (x.charCodeAt(i) || 0) ^ (y.charCodeAt(i) || 0);
  }
  return r === 0;
}

function runtimeBase() {
  // Per-user tmpfs on Linux; falls back to TmpD.
  return Services.env.exists("XDG_RUNTIME_DIR")
    ? createLocalFile(Services.env.get("XDG_RUNTIME_DIR"))
    : Services.dirsvc.get("TmpD", Ci.nsIFile);
}

function privateDir(...names) {
  // Create (0700) and return nested directories under runtimeBase().
  let dir = runtimeBase();
  for (const n of names) {
    dir.append(n);
    if (!dir.exists()) dir.create(Ci.nsIFile.DIRECTORY_TYPE, 0o700);
    else if (dir.isSymlink()) throw new Error("refusing symlinked directory " + dir.path);
    dir = dir.clone();
  }
  return dir;
}

function writeText(file, text, flags) {                // proven pattern (0600)
  const os = Cc["@mozilla.org/network/file-output-stream;1"]
    .createInstance(Ci.nsIFileOutputStream);
  os.init(file, flags, 0o600, 0);
  const conv = Cc["@mozilla.org/intl/converter-output-stream;1"]
    .createInstance(Ci.nsIConverterOutputStream);
  conv.init(os, "UTF-8");
  conv.writeString(text);
  conv.close();
}
const O_WRONLY = 0x02, O_CREAT = 0x08, O_TRUNC = 0x20, O_EXCL = 0x80;

function connectionFile() {
  const f = privateDir("mu4e-bridge");
  f.append("connection.json");
  return f;
}

function writeConnectionFile(port, token) {
  const f = connectionFile();
  if (f.exists()) f.remove(false);                     // O_EXCL below beats symlink races
  writeText(f, JSON.stringify({ port, token, pid: Services.appinfo.processID }),
    O_WRONLY | O_CREAT | O_EXCL);
}

function removeQuietly(file, recursive = false) {
  try { if (file.exists()) file.remove(recursive); } catch (e) { /* best effort */ }
}

// ---------------------------------------------------------------- HTTP glue

function reply(res, status, obj) {                     // proven: res.write + utf-8
  res.setStatusLine("1.1", status, status === 200 ? "OK" : "Error");
  res.setHeader("Content-Type", "application/json; charset=utf-8", false);
  res.write(JSON.stringify(obj));
  res.finish();
}

function route(server, token, path, fn) {
  server.registerPathHandler(path, (req, res) => {
    res.processAsync();
    (async () => {
      try {
        let auth = "";
        try { auth = req.getHeader("Authorization") || ""; } catch (e) { /* missing */ }
        if (!timingSafeEqual(auth, "Bearer " + token)) {
          return reply(res, 403, { error: "forbidden" });
        }
        if (req.method !== "POST") return reply(res, 405, { error: "POST only" });
        let len = 0;
        try { len = parseInt(req.getHeader("Content-Length"), 10) || 0; } catch (e) { /* none */ }
        if (len > MAX_BODY) return reply(res, 413, { error: "body too large" });
        const s = req.bodyInputStream;
        const text = NetUtil.readInputStreamToString(s, s.available(), { charset: "UTF-8" });
        return reply(res, 200, await fn(text ? JSON.parse(text) : {}));
      } catch (e) {
        return reply(res, 500, { error: String(e) });
      }
    })().catch(() => { try { res.finish(); } catch (e) { /* already finished */ } });
  });
}

// ------------------------------------------------------------ mail helpers

function* allFolders() {
  // Same walk thunderbird-mcp uses: account root -> subFolders (proven).
  for (const account of MailServices.accounts.accounts) {
    const root = account.incomingServer?.rootFolder;
    if (!root) continue;
    const stack = [root];
    while (stack.length) {
      const f = stack.pop();
      for (const sf of f.subFolders) stack.push(sf);
      if (f !== root) yield f;
    }
  }
}

function findHeaders(mid) {
  // O(#folders) scan using the direct DB lookup (proven call).
  const hits = [];
  for (const folder of allFolders()) {
    try {
      if (folder.getFlag(Ci.nsMsgFolderFlags.Virtual)) continue;
      const hdr = folder.msgDatabase?.getMsgHdrForMessageID(mid);
      if (hdr) hits.push({ folder, hdr });
    } catch (e) { /* folder db unavailable */ }
  }
  return hits;
}

function identityFor(from) {                           // proven walk
  const want = (from || "").toLowerCase();
  for (const account of MailServices.accounts.accounts) {
    for (const identity of account.identities) {
      if (identity.key === from || (identity.email || "").toLowerCase() === want) {
        return identity;
      }
    }
  }
  throw new Error("unknown identity: " + from);
}

// Outgoing attachments are copied into a private dir that lives until
// Thunderbird shuts down, because the compose window reads them only when
// the user finally presses Send.
function stageAttachment({ path, name, contentType }) {
  const src = createLocalFile(path);
  if (!src.exists() || !src.isFile()) throw new Error("attachment not found: " + path);
  const dir = privateDir("mu4e-bridge", "attachments",
    Services.uuid.generateUUID().toString().slice(1, -1));
  const fname = name || src.leafName;
  src.copyTo(dir, fname);
  const dest = dir.clone();
  dest.append(fname);
  const att = Cc["@mozilla.org/messengercompose/attachment;1"]   // proven
    .createInstance(Ci.nsIMsgAttachment);
  att.url = Services.io.newFileURI(dest).spec;
  att.name = fname;
  att.size = dest.fileSize;
  if (contentType) att.contentType = contentType;
  return att;
}

// ---------------------------------------------------------------- handlers

function readStatus({ mids = [] }) {
  const out = {};
  for (const mid of mids) {
    const hits = findHeaders(mid);
    if (hits.length) {
      out[mid] = {
        read: hits.every(h => h.hdr.isRead),
        flagged: hits.some(h => h.hdr.isFlagged),
      };
    }
  }
  return out;
}

function setFlags({ items = [] }) {
  const out = {};
  const batches = new Map();                           // one call per folder+value
  const add = (folder, kind, value, hdr) => {
    const k = `${folder.URI}|${kind}|${value}`;
    if (!batches.has(k)) batches.set(k, { folder, kind, value, hdrs: [] });
    batches.get(k).hdrs.push(hdr);
  };
  for (const { mid, read, flagged } of items) {
    const hits = findHeaders(mid);
    out[mid] = hits.length;
    for (const { folder, hdr } of hits) {
      if (typeof read === "boolean") add(folder, "read", read, hdr);
      if (typeof flagged === "boolean") add(folder, "flagged", flagged, hdr);
    }
  }
  for (const { folder, kind, value, hdrs } of batches.values()) {
    // folder-level calls so IMAP changes propagate to the server (proven)
    if (kind === "read") folder.markMessagesRead(hdrs, value);
    else folder.markMessagesFlagged(hdrs, value);
  }
  return out;
}

function composeFromFields(a) {
  // Mirrors thunderbird-mcp's composeMail review path (proven), plain text.
  const params = Cc["@mozilla.org/messengercompose/composeparams;1"]
    .createInstance(Ci.nsIMsgComposeParams);
  const fields = Cc["@mozilla.org/messengercompose/composefields;1"]
    .createInstance(Ci.nsIMsgCompFields);
  fields.to = a.to || "";
  fields.cc = a.cc || "";
  fields.bcc = a.bcc || "";
  fields.subject = a.subject || "";
  fields.body = a.body || "";
  if (a.inReplyTo) fields.setHeader("In-Reply-To", a.inReplyTo);
  if (a.references || a.inReplyTo) fields.references = a.references || a.inReplyTo;
  params.type = Ci.nsIMsgCompType.New;
  params.format = Ci.nsIMsgCompFormat.PlainText;
  params.composeFields = fields;
  params.identity = identityFor(a.from);
  for (const att of a.attachments || []) fields.addAttachment(stageAttachment(att));
  MailServices.compose.OpenComposeWindowWithParams(null, params);
  return { ok: true };
}

function outboxFolder() {
  const root = MailServices.accounts.localFoldersServer.rootFolder;
  let box = null;
  try { box = root.getChildNamed("mu4e-outbox"); } catch (e) { /* missing */ }
  return box || root.QueryInterface(Ci.nsIMsgLocalMailFolder)
    .createLocalSubfolder("mu4e-outbox");              // VERIFY
}

function importFile(folder, file) {
  return new Promise((resolve, reject) => {
    let key = null;
    MailServices.copy.copyFileMessage(file, folder, null, true, 0, "", { // VERIFY
      QueryInterface: ChromeUtils.generateQI(["nsIMsgCopyServiceListener"]),
      onStartCopy() {},
      onProgress() {},
      setMessageKey(k) { key = k; },
      getMessageId() { return null; },
      onStopCopy(status) {
        if (Components.isSuccessCode(status)) resolve(folder.GetMessageHeader(key)); // VERIFY
        else reject(new Error("importing message failed: " + status));
      },
    }, null);
  });
}

async function composeFromEml({ eml, from }) {
  const identity = identityFor(from);
  const folder = outboxFolder();
  const tmp = Services.dirsvc.get("TmpD", Ci.nsIFile);
  tmp.append("mu4e-outgoing.eml");
  tmp.createUnique(Ci.nsIFile.NORMAL_FILE_TYPE, 0o600);
  try {
    writeText(tmp, eml.replace(/\r?\n/g, "\r\n"), O_WRONLY | O_TRUNC);
    const hdr = await importFile(folder, tmp);
    // Same 8-argument call thunderbird-mcp uses for forward-inline (proven
    // signature); Draft mode with an imported message is the VERIFY part.
    MailServices.compose.OpenComposeWindow(
      null, hdr, folder.getUriForMsg(hdr),
      Ci.nsIMsgCompType.Draft, Ci.nsIMsgCompFormat.Default,
      identity, identity.email || "", null);
  } finally {
    removeQuietly(tmp);
  }
  return { ok: true };
}

// --------------------------------------------------------- server lifecycle

function randomToken() {                               // proven (no crypto global here)
  const rng = Cc["@mozilla.org/security/random-generator;1"]
    .createInstance(Ci.nsIRandomGenerator);
  return Array.from(rng.generateRandomBytes(32), b => b.toString(16).padStart(2, "0")).join("");
}

async function startServer() {
  // globalThis survives extension reloads; module-level state would not.
  if (globalThis.__mu4eStart) return globalThis.__mu4eStart;
  const attempt = (async () => {
    try { globalThis.__mu4eServer?.stop(() => {}); } catch (e) { /* ignore */ }
    const { HttpServer } = ChromeUtils.importESModule(`resource://${RES_HOST}/httpd.sys.mjs`);
    const token = randomToken();
    const server = new HttpServer();
    route(server, token, "/ping", () => ({ ok: true }));
    route(server, token, "/read-status", readStatus);
    route(server, token, "/set-flags", setFlags);
    route(server, token, "/compose-fields", composeFromFields);
    route(server, token, "/compose", composeFromEml);

    let port = null;
    for (let i = 0; i < PORT_TRIES && port === null; i++) {
      try { server.start(PORT_BASE + i); port = PORT_BASE + i; }   // loopback only (proven)
      catch (e) { if (i === PORT_TRIES - 1) throw e; }
    }
    globalThis.__mu4eServer = server;
    writeConnectionFile(port, token);
    return { port };
  })();
  globalThis.__mu4eStart = attempt;
  try { return await attempt; }
  catch (e) { globalThis.__mu4eStart = null; throw e; }
}

var mu4eBridge = class extends ExtensionCommon.ExtensionAPI {
  getAPI(context) {
    resProto.setSubstitutionWithFlags(RES_HOST, context.extension.rootURI,
      resProto.ALLOW_CONTENT_ACCESS);                 // proven
    return { mu4eBridge: { start: () => startServer() } };
  }

  onShutdown(isAppShutdown) {
    try { globalThis.__mu4eServer?.stop(() => {}); } catch (e) { /* ignore */ }
    globalThis.__mu4eServer = null;
    globalThis.__mu4eStart = null;
    removeQuietly(connectionFile());
    try {
      const att = runtimeBase();
      att.append("mu4e-bridge");
      att.append("attachments");
      removeQuietly(att, true);
    } catch (e) { /* ignore */ }
    if (isAppShutdown) return;
    resProto.setSubstitution(RES_HOST, null);
    Services.obs.notifyObservers(null, "startupcache-invalidate");
  }
};
