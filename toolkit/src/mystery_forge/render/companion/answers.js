// @ts-check
// Answer normalization and hashing for the companion page. This is the JavaScript copy of
// toolkit/src/mystery_forge/answers.py; contracts/answer-vectors.json keeps both copies equal.
// The page runs from file://, where crypto.subtle is not always available, so SHA-256 is implemented here.

(function registerAnswers() {
  /** Letters that Unicode decomposition (NFKD) does not split into a base letter plus a mark. */
  /** @type {Record<string, string>} */
  const SPECIAL_LETTERS = { æ: 'ae', œ: 'oe', ø: 'o', ł: 'l', đ: 'd', ð: 'd', þ: 'th', ı: 'i' };

  /** A leading article is dropped only when another word follows it. */
  /** @type {Record<string, string[]>} */
  const LEADING_ARTICLES = {
    en: ['the', 'a', 'an'],
    es: ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'],
    ca: ['el', 'la', 'els', 'les', 'l', 'un', 'una'],
    fr: ['le', 'la', 'les', 'l', 'un', 'une', 'des'],
    de: ['der', 'die', 'das', 'ein', 'eine'],
    it: ['il', 'lo', 'la', 'i', 'gli', 'le', 'l', 'un', 'una', 'uno'],
    pt: ['o', 'a', 'os', 'as', 'um', 'uma'],
  };

  /** The first letter that keeps its marks: Armenian. Below it lie Latin, Greek, and Cyrillic. */
  const FIRST_MARKED_SCRIPT = 0x0530;
  /** Latin Extended Additional and Greek Extended: their letters lose their accents too. */
  const EXTENDED_ACCENTED_START = 0x1e00;
  const EXTENDED_ACCENTED_END = 0x2000;

  /**
   * True when a mark on this base letter is only an accent: in Latin, Greek, and Cyrillic, "é" counts as "e".
   * @param {string} base
   * @returns {boolean}
   */
  function dropsAccent(base) {
    const code = /** @type {number} */ (base.codePointAt(0));
    return code < FIRST_MARKED_SCRIPT || (code >= EXTENDED_ACCENTED_START && code < EXTENDED_ACCENTED_END);
  }

  /**
   * @param {string} decomposed
   * @returns {string}
   */
  function withoutAccents(decomposed) {
    /** @type {string[]} */
    const kept = [];
    let base = '';
    for (const character of decomposed) {
      if (!/\p{M}/u.test(character)) {
        base = character;
      } else if (base && dropsAccent(base)) {
        continue;
      }
      kept.push(character);
    }
    // Compose again, so a kana with its voicing mark or a Hangul syllable is one character, as players type it.
    return kept.join('').normalize('NFC');
  }

  /**
   * Return the comparable form of an answer: lowercase letters and digits of any script, no Latin, Greek, or
   * Cyrillic accents, no punctuation or spaces, and no leading article.
   * @param {string} text
   * @param {string} language
   * @returns {string}
   */
  function normalizeAnswer(text, language) {
    // Python uses casefold(). toLowerCase() gives the same result for these letters, except for ß, which casefold()
    // turns into "ss", and the Greek final sigma, which casefold() turns into a plain sigma.
    const lowered = withoutAccents(text.normalize('NFKD')).toLowerCase().replace(/ß/g, 'ss').replace(/ς/g, 'σ');
    const transliterated = Array.from(lowered, (character) => SPECIAL_LETTERS[character] ?? character).join('');
    /** @type {string[]} */
    let words = transliterated.match(/[\p{L}\p{N}\p{M}]+/gu) ?? [];
    const articles = LEADING_ARTICLES[language] ?? [];
    if (words.length > 1 && articles.includes(/** @type {string} */ (words[0]))) {
      words = words.slice(1);
    }
    return words.join('');
  }

  /** @type {number[]} */
  const ROUND_CONSTANTS = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98,
    0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8,
    0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819,
    0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7,
    0xc67178f2,
  ];

  /**
   * @param {number} value
   * @param {number} bits
   * @returns {number}
   */
  function rotateRight(value, bits) {
    return (value >>> bits) | (value << (32 - bits));
  }

  /**
   * Return the SHA-256 digest of the UTF-8 bytes of a text, as lowercase hex.
   * @param {string} text
   * @returns {string}
   */
  function sha256Hex(text) {
    const message = new TextEncoder().encode(text);
    const bitLength = message.length * 8;
    // Padding: one 0x80 byte, zeros, then the 64-bit length, so the total is a multiple of 64 bytes.
    const paddedLength = Math.ceil((message.length + 9) / 64) * 64;
    const padded = new Uint8Array(paddedLength);
    padded.set(message);
    padded[message.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000));
    view.setUint32(paddedLength - 4, bitLength >>> 0);

    /** @type {[number, number, number, number, number, number, number, number]} */
    let hash = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
    const schedule = new Array(64).fill(0);
    for (let blockStart = 0; blockStart < paddedLength; blockStart += 64) {
      for (let index = 0; index < 16; index += 1) {
        schedule[index] = view.getUint32(blockStart + index * 4);
      }
      for (let index = 16; index < 64; index += 1) {
        const previous15 = schedule[index - 15];
        const previous2 = schedule[index - 2];
        const sigma0 = rotateRight(previous15, 7) ^ rotateRight(previous15, 18) ^ (previous15 >>> 3);
        const sigma1 = rotateRight(previous2, 17) ^ rotateRight(previous2, 19) ^ (previous2 >>> 10);
        schedule[index] = (schedule[index - 16] + sigma0 + schedule[index - 7] + sigma1) | 0;
      }
      let [a, b, c, d, e, f, g, h] = hash;
      for (let index = 0; index < 64; index += 1) {
        const sum1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25);
        const choice = (e & f) ^ (~e & g);
        const temporary1 = (h + sum1 + choice + /** @type {number} */ (ROUND_CONSTANTS[index]) + schedule[index]) | 0;
        const sum0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22);
        const majority = (a & b) ^ (a & c) ^ (b & c);
        const temporary2 = (sum0 + majority) | 0;
        h = g;
        g = f;
        f = e;
        e = (d + temporary1) | 0;
        d = c;
        c = b;
        b = a;
        a = (temporary1 + temporary2) | 0;
      }
      hash = [
        (hash[0] + a) | 0,
        (hash[1] + b) | 0,
        (hash[2] + c) | 0,
        (hash[3] + d) | 0,
        (hash[4] + e) | 0,
        (hash[5] + f) | 0,
        (hash[6] + g) | 0,
        (hash[7] + h) | 0,
      ];
    }
    return hash.map((word) => (word >>> 0).toString(16).padStart(8, '0')).join('');
  }

  /**
   * Return the SHA-256 hex digest of `<salt>:<normalized answer>`, the form that the companion page stores.
   * @param {string} normalizedAnswer
   * @param {string} salt
   * @returns {string}
   */
  function answerHash(normalizedAnswer, salt) {
    return sha256Hex(`${salt}:${normalizedAnswer}`);
  }

  globalThis.MysteryForgeAnswers = { normalizeAnswer, answerHash, sha256Hex };
})();
