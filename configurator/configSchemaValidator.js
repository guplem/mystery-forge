// @ts-check
// A small validator for the JSON Schema subset that contracts/game-config.schema.json uses. The page runs from
// file://, with no library, so this file implements that subset only. The Python toolkit validates the same schema
// with the jsonschema library, and contracts/config-vectors.json keeps both sides equal.

(function registerConfigValidator() {
  /** Keywords that this validator applies, plus the annotations that it ignores. */
  const SUPPORTED_KEYWORDS = new Set([
    '$schema',
    'title',
    'description',
    'default',
    'type',
    'enum',
    'minimum',
    'maximum',
    'maxLength',
    'maxItems',
    'items',
    'properties',
    'required',
    'additionalProperties',
  ]);

  /**
   * @param {unknown} value
   * @returns {value is Record<string, unknown>}
   */
  function isPlainObject(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  /** @type {Record<string, (value: unknown) => boolean>} */
  const TYPE_CHECKS = {
    object: isPlainObject,
    array: (value) => Array.isArray(value),
    string: (value) => typeof value === 'string',
    integer: (value) => Number.isInteger(value),
    number: (value) => typeof value === 'number',
    boolean: (value) => typeof value === 'boolean',
    null: (value) => value === null,
  };

  /**
   * @param {(string | number)[]} pathParts
   * @param {string} keyword
   * @param {string} message
   * @returns {MysteryForgeConfigFinding}
   */
  function makeFinding(pathParts, keyword, message) {
    return { path: pathParts.join('.'), keyword, message };
  }

  /**
   * @param {MysteryForgeJsonSchema} schema
   * @param {Record<string, unknown>} value
   * @param {(string | number)[]} pathParts
   * @param {MysteryForgeConfigFinding[]} findings
   * @returns {void}
   */
  function validateObject(schema, value, pathParts, findings) {
    const properties = schema.properties ?? {};
    // jsonschema reports a missing or an unknown key at the parent object. Both sides report it at the key itself,
    // so that the page can show the problem next to its own field.
    for (const key of schema.required ?? []) {
      if (!(key in value)) {
        findings.push(makeFinding([...pathParts, key], 'required', 'This value is required.'));
      }
    }
    for (const [key, item] of Object.entries(value)) {
      const propertySchema = properties[key];
      if (propertySchema) {
        validateNode(propertySchema, item, [...pathParts, key], findings);
      } else if (schema.additionalProperties === false) {
        findings.push(
          makeFinding([...pathParts, key], 'additionalProperties', `The key "${key}" is not allowed here.`),
        );
      }
    }
  }

  /**
   * @param {MysteryForgeJsonSchema} schema
   * @param {unknown} value
   * @param {(string | number)[]} pathParts
   * @param {MysteryForgeConfigFinding[]} findings
   * @returns {void}
   */
  function validateNode(schema, value, pathParts, findings) {
    if (schema.type !== undefined && !(TYPE_CHECKS[schema.type]?.(value) ?? false)) {
      findings.push(makeFinding(pathParts, 'type', `This value must be of type ${schema.type}.`));
    }
    if (schema.enum !== undefined && !schema.enum.includes(value)) {
      findings.push(makeFinding(pathParts, 'enum', `This value must be one of: ${schema.enum.join(', ')}.`));
    }
    if (typeof value === 'number') {
      if (schema.minimum !== undefined && value < schema.minimum) {
        findings.push(makeFinding(pathParts, 'minimum', `This value must be ${schema.minimum} or more.`));
      }
      if (schema.maximum !== undefined && value > schema.maximum) {
        findings.push(makeFinding(pathParts, 'maximum', `This value must be ${schema.maximum} or less.`));
      }
    }
    // JSON Schema counts characters as Unicode code points, as Python does. A spread string counts code points too;
    // `.length` would count an emoji twice.
    if (typeof value === 'string' && schema.maxLength !== undefined && [...value].length > schema.maxLength) {
      findings.push(
        makeFinding(pathParts, 'maxLength', `This text must have ${schema.maxLength} characters or fewer.`),
      );
    }
    if (Array.isArray(value)) {
      if (schema.maxItems !== undefined && value.length > schema.maxItems) {
        findings.push(makeFinding(pathParts, 'maxItems', `This list must have ${schema.maxItems} items or fewer.`));
      }
      const itemSchema = schema.items;
      if (itemSchema !== undefined) {
        value.forEach((item, index) => validateNode(itemSchema, item, [...pathParts, index], findings));
      }
    }
    if (isPlainObject(value)) {
      validateObject(schema, value, pathParts, findings);
    }
  }

  /**
   * Return every problem in a value, sorted by path, then by keyword. The empty path is the whole value.
   * @param {MysteryForgeJsonSchema} schema
   * @param {unknown} value
   * @returns {MysteryForgeConfigFinding[]}
   */
  function validateConfig(schema, value) {
    /** @type {MysteryForgeConfigFinding[]} */
    const findings = [];
    validateNode(schema, value, [], findings);
    return findings.sort(
      (first, second) =>
        first.path.localeCompare(second.path, 'en') || first.keyword.localeCompare(second.keyword, 'en'),
    );
  }

  /**
   * Return a deep copy of a value where each missing property with a `default` takes it, at every depth.
   * @param {MysteryForgeJsonSchema} schema
   * @param {unknown} value
   * @returns {unknown}
   */
  function applyDefaults(schema, value) {
    if (!isPlainObject(value)) {
      return structuredClone(value);
    }
    const properties = schema.properties ?? {};
    /** @type {Record<string, unknown>} */
    const filled = {};
    for (const [key, propertySchema] of Object.entries(properties)) {
      if (key in value) {
        filled[key] = applyDefaults(propertySchema, value[key]);
      } else if ('default' in propertySchema) {
        filled[key] = applyDefaults(propertySchema, propertySchema.default);
      }
    }
    for (const [key, item] of Object.entries(value)) {
      if (!(key in properties)) {
        filled[key] = structuredClone(item);
      }
    }
    return filled;
  }

  /**
   * Return the sorted keywords in a schema, at any depth, that this validator does not support.
   * @param {object} schema
   * @returns {string[]}
   */
  function listUnsupportedKeywords(schema) {
    /** @type {Set<string>} */
    const unsupported = new Set();
    /** @param {Record<string, unknown>} node */
    function visit(node) {
      for (const [keyword, child] of Object.entries(node)) {
        if (!SUPPORTED_KEYWORDS.has(keyword)) {
          unsupported.add(keyword);
        } else if (keyword === 'items') {
          visit(/** @type {Record<string, unknown>} */ (child));
        } else if (keyword === 'properties') {
          Object.values(/** @type {Record<string, Record<string, unknown>>} */ (child)).forEach(visit);
        }
      }
    }
    visit(/** @type {Record<string, unknown>} */ (schema));
    return [...unsupported].sort();
  }

  globalThis.MysteryForgeConfigValidator = { validateConfig, applyDefaults, listUnsupportedKeywords };
})();
