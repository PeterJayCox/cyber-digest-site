/* Flashforge gate — build-time encrypted seed data.
 *
 * The seed payload (starter glossary + wiki bundle) is AES-256-GCM encrypted at build
 * time by build_site.py and shipped as a JSON data block in #fc-payload. The passphrase
 * lives outside the repo (~/.hermes/secrets/ai-weekly-gate.txt, 0600), so neither it nor
 * the payload can be read from this page, from the repo, or from raw.githubusercontent.
 *
 * Same mechanism as the drafts gate (ai_weekly.py), deliberately: one passphrase, one
 * crypto implementation, one thing to reason about.
 *
 * Honest limit: there is no server, so the ciphertext is public and an offline guess is
 * unlimited. Passphrase length is the only real defence. This deters casual readers and
 * crawlers; it is not confidentiality against someone who wants in.
 *
 * The payload block is <script type="application/json"> — not executed, so it survives a
 * future CSP with per-build hashes. No inline handlers here: the app calls FC_GATE.unlock.
 */
(function () {
  window.FC_GATE = (function () {
    var node = document.getElementById('fc-payload');
    var payload = null;
    try { payload = node ? JSON.parse(node.textContent) : null; } catch (e) { payload = null; }

    function b64(s) {
      var raw = atob(s), a = new Uint8Array(raw.length);
      for (var i = 0; i < raw.length; i++) { a[i] = raw.charCodeAt(i); }
      return a;
    }

    return {
      /* true only when the build actually shipped ciphertext. */
      configured: !!(payload && payload.ct),

      /* Resolves {starter:[...], bundle:{...}}; rejects with a coded Error otherwise so
       * the lock screen can tell "wrong password" apart from "built unconfigured". */
      unlock: function (pw) {
        if (!(window.crypto && window.crypto.subtle)) {
          return Promise.reject(new Error('NO_CRYPTO'));
        }
        if (!payload || !payload.ct) {
          return Promise.reject(new Error('UNCONFIGURED'));
        }
        var enc = new TextEncoder();
        return crypto.subtle.importKey('raw', enc.encode(pw), { name: 'PBKDF2' }, false, ['deriveKey'])
          .then(function (base) {
            return crypto.subtle.deriveKey(
              { name: 'PBKDF2', salt: b64(payload.kdf.salt), iterations: payload.kdf.iterations, hash: 'SHA-256' },
              base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
          })
          .then(function (key) {
            return crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64(payload.iv) }, key, b64(payload.ct));
          })
          .then(function (plain) { return JSON.parse(new TextDecoder().decode(plain)); })
          .catch(function () { throw new Error('BAD_PASSWORD'); });
      }
    };
  })();
})();