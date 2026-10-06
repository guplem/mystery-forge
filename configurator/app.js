// @ts-check
// DOM glue of the configurator page. It renders the form model, reads the user's input, and shows the results of
// configForm.js. Every decision lives in configForm.js and uiText.js, which have unit tests; the browser tests in
// toolkit/tests/test_configurator_page.py cover this file.

(function startConfigurator() {
  const form = globalThis.MysteryForgeConfigForm;
  const uiText = globalThis.MysteryForgeUiText;
  const SAVE_DELAY_MS = 300;
  const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';

  const browserLanguages = [...navigator.languages, navigator.language];
  const storage = openStorage();
  const draft = storage ? form.loadDraft(storage) : null;

  const state = {
    config: draft?.config ?? form.initialConfig(browserLanguages),
    uiLanguage: draft?.uiLanguage ?? uiText.pickUiLanguage(browserLanguages),
    /** @type {Set<string>} ids of the collapsible panels that the user opened */
    openPanels: new Set(),
    /** @type {(() => void)[]} each one copies one config value into its widget */
    fieldSyncers: [],
    /** @type {number | undefined} */
    saveTimer: undefined,
    dragDepth: 0,
  };

  /** @returns {Storage | null} */
  function openStorage() {
    // Reading localStorage itself throws when the browser blocks storage for file:// pages.
    try {
      return window.localStorage;
    } catch {
      return null;
    }
  }

  /**
   * @param {string} key
   * @param {Record<string, string | number>} [params]
   * @returns {string}
   */
  function t(key, params) {
    return uiText.translate(state.uiLanguage, key, params);
  }

  /**
   * @param {string} id
   * @returns {HTMLElement}
   */
  function byId(id) {
    const element = document.getElementById(id);
    if (!element) {
      throw new Error(`The page has no element #${id}.`);
    }
    return element;
  }

  /**
   * @template {keyof HTMLElementTagNameMap} TagName
   * @param {TagName} tagName
   * @param {Record<string, string>} [attributes]
   * @param {(Node | string)[]} [children]
   * @returns {HTMLElementTagNameMap[TagName]}
   */
  function createElement(tagName, attributes = {}, children = []) {
    const element = document.createElement(tagName);
    for (const [name, value] of Object.entries(attributes)) {
      element.setAttribute(name, value);
    }
    element.append(...children);
    return element;
  }

  /**
   * @param {string} symbolId
   * @param {string} className
   * @returns {SVGSVGElement}
   */
  function svgIcon(symbolId, className) {
    const svg = document.createElementNS(SVG_NAMESPACE, 'svg');
    svg.setAttribute('class', className);
    svg.setAttribute('aria-hidden', 'true');
    const use = document.createElementNS(SVG_NAMESPACE, 'use');
    use.setAttribute('href', `#${symbolId}`);
    svg.append(use);
    return svg;
  }

  /**
   * @param {string} fieldPath
   * @returns {string}
   */
  function domId(fieldPath) {
    return fieldPath.replaceAll('.', '-');
  }

  /**
   * @param {string} fieldPath
   * @returns {unknown}
   */
  function valueOf(fieldPath) {
    return form.getAtPath(state.config, fieldPath);
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @returns {void}
   */
  function setConfig(config) {
    state.config = config;
    state.fieldSyncers.forEach((sync) => sync());
    refreshSummary();
    scheduleSave();
  }

  /**
   * @param {string} fieldPath
   * @param {unknown} rawValue
   * @returns {void}
   */
  function changeField(fieldPath, rawValue) {
    const change = form.applyFieldChange(state.config, fieldPath, rawValue);
    setConfig(change.config);
    if (change.presetApplied) {
      showStatus(t('status.preset_applied', { audience: t(`enum.audience.${String(rawValue)}.label`) }), 'info');
    }
  }

  function scheduleSave() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(() => {
      if (storage) {
        form.saveDraft(storage, { config: state.config, uiLanguage: state.uiLanguage });
      }
    }, SAVE_DELAY_MS);
  }

  // ---------------------------------------------------------------- field widgets

  /**
   * @param {MysteryForgeFormField} field
   * @param {string} tagName
   * @returns {{wrapper: HTMLElement, helpId: string}}
   */
  function fieldWrapper(field, tagName) {
    const wrapper = document.createElement(tagName);
    wrapper.className = `field field--${field.widget}`;
    wrapper.id = `field-${domId(field.path)}`;
    wrapper.dataset.fieldPath = field.path;
    return { wrapper, helpId: `help-${domId(field.path)}` };
  }

  /**
   * @param {MysteryForgeFormField} field
   * @param {string} helpId
   * @returns {HTMLParagraphElement}
   */
  function helpText(field, helpId) {
    return createElement('p', { class: 'field__help', id: helpId }, [field.help]);
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLLabelElement}
   */
  function fieldLabel(field) {
    return createElement('label', { class: 'field__label', for: `input-${domId(field.path)}` }, [field.label]);
  }

  /**
   * A radio group: large cards with an icon or a style preview, or small segments.
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderChoice(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'fieldset');
    const legend = createElement('legend', { class: 'field__label' }, [field.label]);
    const isCards = field.widget === 'cards';
    const group = createElement('div', { class: isCards ? 'choice-cards' : 'segmented' });
    const choiceHelp = createElement('p', { class: 'field__choice-help', 'aria-live': 'polite' });
    /** @type {HTMLInputElement[]} */
    const inputs = [];
    for (const option of field.options) {
      const input = createElement('input', {
        type: 'radio',
        class: 'choice__input',
        name: field.path,
        value: option.value,
        id: `input-${domId(field.path)}-${option.value}`,
      });
      inputs.push(input);
      /** @type {(Node | string)[]} */
      const content = [input];
      if (isCards) {
        const iconId = `icon-${domId(field.path)}-${option.value}`;
        if (document.getElementById(iconId)) {
          content.push(svgIcon(iconId, 'choice-card__icon'));
        }
        if (field.path === 'visuals.style') {
          content.push(stylePreview(option.value));
        }
        content.push(
          createElement('span', { class: 'choice-card__title' }, [option.label]),
          createElement('span', { class: 'choice-card__help' }, [option.help]),
        );
      } else {
        content.push(createElement('span', { class: 'segment__label' }, [option.label]));
        if (field.path === 'generation.quality') {
          content.push(createElement('span', { class: 'segment__meta', 'data-quality-time': option.value }));
        }
      }
      group.append(
        createElement('label', isCards ? { class: 'choice-card' } : { class: 'segment', title: option.help }, content),
      );
    }
    wrapper.append(legend, helpText(field, helpId), group);
    if (!isCards) {
      wrapper.append(choiceHelp);
    }
    group.addEventListener('change', (event) => {
      changeField(field.path, /** @type {HTMLInputElement} */ (event.target).value);
    });
    state.fieldSyncers.push(() => {
      const current = String(valueOf(field.path));
      inputs.forEach((input) => {
        input.checked = input.value === current;
      });
      choiceHelp.textContent = field.options.find((option) => option.value === current)?.help ?? '';
    });
    return wrapper;
  }

  /**
   * A small page drawn in CSS that shows the colors and the type of one visual style.
   * @param {string} style
   * @returns {HTMLSpanElement}
   */
  function stylePreview(style) {
    return createElement('span', { class: `style-preview style-preview--${style}`, 'aria-hidden': 'true' }, [
      createElement('span', { class: 'style-preview__title' }, ['Aa']),
      createElement('span', { class: 'style-preview__line' }),
      createElement('span', { class: 'style-preview__line style-preview__line--short' }),
    ]);
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderSelect(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const select = createElement(
      'select',
      { id: `input-${domId(field.path)}`, class: 'select', 'aria-describedby': helpId },
      field.options.map((option) => createElement('option', { value: option.value }, [option.label])),
    );
    select.addEventListener('change', () => changeField(field.path, select.value));
    state.fieldSyncers.push(() => {
      select.value = String(valueOf(field.path));
    });
    wrapper.append(fieldLabel(field), helpText(field, helpId), select);
    return wrapper;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLInputElement}
   */
  function numberInput(field) {
    const input = createElement('input', {
      type: 'number',
      id: `input-${domId(field.path)}`,
      class: 'text-input text-input--number',
      min: String(field.minimum),
      max: String(field.maximum),
      step: '1',
      inputmode: 'numeric',
      'aria-describedby': `help-${domId(field.path)}`,
    });
    input.addEventListener('change', () => changeField(field.path, input.value));
    state.fieldSyncers.push(() => {
      input.value = String(valueOf(field.path));
    });
    return input;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderNumber(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    wrapper.append(fieldLabel(field), helpText(field, helpId), numberInput(field));
    return wrapper;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderStepper(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const input = numberInput(field);
    /**
     * @param {number} delta
     * @param {string} labelKey
     * @param {string} symbol
     * @returns {HTMLButtonElement}
     */
    function stepButton(delta, labelKey, symbol) {
      const button = createElement(
        'button',
        { type: 'button', class: 'stepper__button', 'aria-label': t(labelKey), 'data-step': String(delta) },
        [symbol],
      );
      button.addEventListener('click', () => changeField(field.path, Number(valueOf(field.path)) + delta));
      return button;
    }
    const decrease = stepButton(-1, 'form.decrease', '−');
    const increase = stepButton(1, 'form.increase', '+');
    state.fieldSyncers.push(() => {
      decrease.disabled = Number(valueOf(field.path)) <= field.minimum;
      increase.disabled = Number(valueOf(field.path)) >= field.maximum;
    });
    wrapper.append(
      fieldLabel(field),
      helpText(field, helpId),
      createElement('div', { class: 'stepper' }, [decrease, input, increase]),
    );
    return wrapper;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderRange(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const inputId = `input-${domId(field.path)}`;
    const input = createElement('input', {
      type: 'range',
      id: inputId,
      class: 'range__input',
      min: String(field.minimum),
      max: String(field.maximum),
      step: String(field.step),
      'aria-describedby': helpId,
    });
    const output = createElement('output', { class: 'range__value', for: inputId });
    input.addEventListener('input', () => changeField(field.path, input.value));
    state.fieldSyncers.push(() => {
      const minutes = Number(valueOf(field.path));
      input.value = String(minutes);
      output.textContent = form.formatMinutes(minutes);
      input.setAttribute('aria-valuetext', output.textContent);
      const filled = ((minutes - field.minimum) / (field.maximum - field.minimum)) * 100;
      input.style.setProperty('--range-fill', `${filled}%`);
    });
    const scale = createElement('div', { class: 'range__scale', 'aria-hidden': 'true' }, [
      createElement('span', {}, [form.formatMinutes(field.minimum)]),
      createElement('span', {}, [form.formatMinutes(field.maximum)]),
    ]);
    wrapper.append(
      createElement('div', { class: 'range__header' }, [fieldLabel(field), output]),
      helpText(field, helpId),
      input,
      scale,
    );
    return wrapper;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderToggle(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const input = createElement('input', {
      type: 'checkbox',
      role: 'switch',
      id: `input-${domId(field.path)}`,
      class: 'toggle__input',
      'aria-describedby': helpId,
    });
    input.addEventListener('change', () => changeField(field.path, input.checked));
    state.fieldSyncers.push(() => {
      input.checked = valueOf(field.path) === true;
    });
    wrapper.append(
      createElement('label', { class: 'toggle', for: input.id }, [
        createElement('span', { class: 'toggle__text' }, [
          createElement('span', { class: 'field__label' }, [field.label]),
          createElement('span', { class: 'field__help', id: helpId }, [field.help]),
        ]),
        input,
      ]),
    );
    return wrapper;
  }

  /**
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderText(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const isTextarea = field.widget === 'textarea';
    const attributes = {
      id: `input-${domId(field.path)}`,
      class: isTextarea ? 'text-input text-input--area' : 'text-input',
      maxlength: String(field.maxLength),
      placeholder: field.placeholder,
      'aria-describedby': helpId,
    };
    const input = isTextarea
      ? createElement('textarea', { ...attributes, rows: '4' })
      : createElement('input', { ...attributes, type: 'text' });
    input.addEventListener('input', () => changeField(field.path, input.value));
    state.fieldSyncers.push(() => {
      // Leave the field that the user types in alone, so that the caret does not jump.
      if (document.activeElement !== input) {
        input.value = String(valueOf(field.path));
      }
    });
    wrapper.append(fieldLabel(field), helpText(field, helpId), input);
    if (field.path === 'theme.idea') {
      const note = createElement('p', { class: 'field__note', id: 'surprise-note' }, [t('form.surprise')]);
      state.fieldSyncers.push(() => {
        note.hidden = !form.showsSurpriseNote(state.config);
      });
      wrapper.append(note);
    }
    return wrapper;
  }

  /**
   * A list of short texts shown as chips, with a text box to add one more.
   * @param {MysteryForgeFormField} field
   * @returns {HTMLElement}
   */
  function renderList(field) {
    const { wrapper, helpId } = fieldWrapper(field, 'div');
    const input = createElement('input', {
      type: 'text',
      id: `input-${domId(field.path)}`,
      class: 'text-input',
      maxlength: String(field.maxLength),
      placeholder: field.placeholder,
      'aria-describedby': helpId,
    });
    const addButton = createElement('button', { type: 'button', class: 'button button--small' }, [t('form.add')]);
    const chips = createElement('ul', { class: 'chips', 'aria-label': field.label });
    const count = createElement('p', { class: 'field__count', 'aria-live': 'polite' });

    function addItem() {
      const updated = form.addListItem(state.config, field.path, input.value);
      if (updated !== state.config) {
        input.value = '';
        setConfig(updated);
      }
      input.focus();
    }
    addButton.addEventListener('click', addItem);
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        addItem();
      }
    });
    state.fieldSyncers.push(() => {
      const items = /** @type {string[]} */ (valueOf(field.path));
      chips.replaceChildren(
        ...items.map((item, index) => {
          const remove = createElement(
            'button',
            { type: 'button', class: 'chip__remove', 'aria-label': t('form.remove', { item }) },
            [svgIcon('icon-close', 'chip__remove-icon')],
          );
          remove.addEventListener('click', () => {
            setConfig(form.removeListItem(state.config, field.path, index));
            input.focus();
          });
          return createElement('li', { class: 'chip' }, [createElement('span', {}, [item]), remove]);
        }),
      );
      const full = form.isListFull(state.config, field.path);
      input.disabled = full;
      addButton.disabled = full;
      count.textContent = full
        ? t('form.list_full', { max: field.maxItems })
        : t('form.list_count', { count: items.length, max: field.maxItems });
    });
    wrapper.append(
      fieldLabel(field),
      helpText(field, helpId),
      createElement('div', { class: 'chips-input' }, [input, addButton]),
      chips,
      count,
    );
    return wrapper;
  }

  /** @type {Record<MysteryForgeFieldWidget, (field: MysteryForgeFormField) => HTMLElement>} */
  const WIDGET_RENDERERS = {
    cards: renderChoice,
    segmented: renderChoice,
    select: renderSelect,
    stepper: renderStepper,
    range: renderRange,
    number: renderNumber,
    toggle: renderToggle,
    text: renderText,
    textarea: renderText,
    list: renderList,
  };

  // ---------------------------------------------------------------- sections

  /**
   * @param {string} panelId
   * @param {HTMLElement} summaryContent
   * @param {HTMLElement[]} body
   * @param {string} className
   * @returns {HTMLDetailsElement}
   */
  function collapsible(panelId, summaryContent, body, className) {
    const details = createElement('details', { class: className, id: panelId }, [
      createElement('summary', {}, [summaryContent]),
      ...body,
    ]);
    details.open = state.openPanels.has(panelId);
    details.addEventListener('toggle', () => {
      if (details.open) {
        state.openPanels.add(panelId);
      } else {
        state.openPanels.delete(panelId);
      }
    });
    return details;
  }

  /**
   * @param {MysteryForgeFormSection} section
   * @param {number} index
   * @returns {HTMLElement}
   */
  function renderSection(section, index) {
    const panelId = `section-${section.id}`;
    const titleId = `${panelId}-title`;
    const header = createElement('div', { class: 'panel__header' }, [
      createElement('span', { class: 'panel__number', 'aria-hidden': 'true' }, [String(index + 1).padStart(2, '0')]),
      createElement('div', {}, [
        createElement('h2', { class: 'panel__title', id: titleId }, [section.title]),
        createElement('p', { class: 'panel__intro' }, [section.intro]),
      ]),
    ]);
    const fields = createElement('div', { class: 'panel__fields' });
    const advanced = section.fields.filter((field) => field.advanced);
    fields.append(
      ...section.fields.filter((field) => !field.advanced).map((field) => WIDGET_RENDERERS[field.widget](field)),
    );
    if (advanced.length > 0) {
      fields.append(
        collapsible(
          `advanced-${section.id}`,
          createElement('span', {}, [t('section.advanced.title')]),
          advanced.map((field) => WIDGET_RENDERERS[field.widget](field)),
          'advanced',
        ),
      );
    }
    const className = `panel panel--${section.id}`;
    if (section.collapsed) {
      return collapsible(panelId, header, [fields], `${className} panel--collapsible`);
    }
    return createElement('section', { class: className, id: panelId, 'aria-labelledby': titleId }, [header, fields]);
  }

  function renderForm() {
    state.fieldSyncers = [];
    byId('config-form').replaceChildren(...form.buildFormModel(state.uiLanguage).map(renderSection));
    state.fieldSyncers.forEach((sync) => sync());
  }

  function renderStaticTexts() {
    document.documentElement.lang = state.uiLanguage;
    document.title = `${t('page.title')} · ${t('how.step1.title')}`;
    document.querySelectorAll('[data-text]').forEach((element) => {
      element.textContent = t(String(/** @type {HTMLElement} */ (element).dataset.text));
    });
    document.querySelectorAll('[data-ui-language]').forEach((button) => {
      button.setAttribute(
        'aria-pressed',
        String(/** @type {HTMLElement} */ (button).dataset.uiLanguage === state.uiLanguage),
      );
    });
  }

  /**
   * @param {MysteryForgeUiLanguage} language
   * @returns {void}
   */
  function setUiLanguage(language) {
    state.uiLanguage = language;
    renderStaticTexts();
    renderForm();
    refreshSummary();
    scheduleSave();
  }

  // ---------------------------------------------------------------- summary panel

  function refreshSummary() {
    const items = form.estimateItems(state.config, state.uiLanguage);
    byId('estimate-list').replaceChildren(
      ...items.map((item) =>
        createElement('div', { class: `estimate__item estimate__item--${item.id}`, 'data-estimate-id': item.id }, [
          createElement('dt', {}, [item.label]),
          createElement('dd', {}, [item.value]),
        ]),
      ),
    );
    const [puzzles, , , playTime] = items;
    byId('mobile-summary-numbers').textContent = `${puzzles?.value} ${puzzles?.label} · ${playTime?.value}`;

    const warnings = form.configWarnings(state.config);
    byId('warning-list').replaceChildren(
      ...(warnings.length === 0
        ? [createElement('li', { class: 'warnings__none' }, [svgIcon('icon-check', 'icon'), t('warnings.none')])]
        : warnings.map((warning) => {
            const link = createElement('a', { class: 'warning__link', href: `#field-${domId(warning.path)}` }, [
              t('warnings.show'),
            ]);
            link.addEventListener('click', () => {
              const target = document.getElementById(`field-${domId(warning.path)}`);
              const panel = target?.closest('details');
              if (panel) {
                panel.open = true;
              }
            });
            return createElement(
              'li',
              { class: `warning warning--${warning.severity}`, 'data-warning-id': warning.id },
              [
                svgIcon(warning.severity === 'warning' ? 'icon-warning' : 'icon-info', 'icon'),
                createElement('span', {}, [t(`warning.${warning.id}`, warning.params), ' ', link]),
              ],
            );
          })),
    );

    /** @type {HTMLTextAreaElement} */ (byId('prompt-text')).value = form.buildPrompt(state.config, state.uiLanguage);
    byId('next-step-3').textContent = t('next.step3', { fileName: form.configFileName(state.config) });
    byId('next-note').textContent = t('next.note', {
      time: form.generationTimeText(state.config, state.uiLanguage),
    });
    document.querySelectorAll('[data-quality-time]').forEach((element) => {
      const quality = String(/** @type {HTMLElement} */ (element).dataset.qualityTime);
      const config = form.setFieldValue(state.config, 'generation.quality', quality);
      element.textContent = form.generationTimeText(config, state.uiLanguage);
    });
  }

  /**
   * @param {string} message
   * @param {'success' | 'info' | 'error'} tone
   * @param {{label: string, run: () => void}} [action]
   * @returns {void}
   */
  function showStatus(message, tone, action) {
    const status = byId('status-message');
    status.className = `status status--${tone}`;
    /** @type {Node[]} */
    const content = [
      svgIcon(tone === 'error' ? 'icon-warning' : 'icon-check', 'icon'),
      createElement('span', {}, [message]),
    ];
    if (action) {
      const button = createElement('button', { type: 'button', class: 'status__action' }, [action.label]);
      button.addEventListener('click', action.run);
      content.push(button);
    }
    status.replaceChildren(...content);
  }

  function clearStatus() {
    const status = byId('status-message');
    status.className = 'status';
    status.replaceChildren();
  }

  /**
   * @param {string} fileName
   * @param {MysteryForgeConfigFinding[]} findings
   * @returns {void}
   */
  function showLoadErrors(fileName, findings) {
    clearStatus();
    byId('load-errors').replaceChildren(
      createElement('p', { class: 'load-errors__title' }, [
        svgIcon('icon-warning', 'icon'),
        t('status.load_failed', { fileName }),
      ]),
      createElement(
        'ul',
        { class: 'load-errors__list' },
        findings.map((finding) => createElement('li', {}, [form.describeFinding(finding, state.uiLanguage)])),
      ),
    );
  }

  function showNextSteps() {
    const nextSteps = byId('next-steps');
    nextSteps.hidden = false;
    nextSteps.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  // ---------------------------------------------------------------- actions

  function downloadConfig() {
    const fileName = form.configFileName(state.config);
    const blob = new Blob([form.configFileText(state.config)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = createElement('a', { href: url, download: fileName, hidden: '' });
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 10000);
    byId('load-errors').replaceChildren();
    showStatus(t('status.downloaded', { fileName }), 'success');
    showNextSteps();
  }

  async function copyPrompt() {
    const promptText = /** @type {HTMLTextAreaElement} */ (byId('prompt-text'));
    /** @type {HTMLDetailsElement} */ (byId('prompt-panel')).open = true;
    showNextSteps();
    try {
      await navigator.clipboard.writeText(promptText.value);
      showStatus(t('status.copied'), 'success');
    } catch {
      // Some browsers refuse the clipboard API on file:// pages. The selected text box is the way out.
      promptText.focus();
      promptText.select();
      const copied = document.execCommand('copy');
      showStatus(t(copied ? 'status.copied' : 'status.copy_failed'), copied ? 'success' : 'info');
    }
  }

  /**
   * @param {File} file
   * @returns {Promise<void>}
   */
  async function loadConfigFile(file) {
    const parsed = form.parseConfigFile(await file.text());
    if (parsed.config === null) {
      showLoadErrors(file.name, parsed.errors);
      return;
    }
    byId('load-errors').replaceChildren();
    setConfig(parsed.config);
    showStatus(t('status.loaded', { fileName: file.name }), 'success');
  }

  function resetConfig() {
    const previous = state.config;
    byId('load-errors').replaceChildren();
    setConfig(form.initialConfig(browserLanguages));
    showStatus(t('status.reset'), 'info', {
      label: t('action.undo'),
      run: () => {
        setConfig(previous);
        clearStatus();
      },
    });
  }

  /**
   * @param {DragEvent} event
   * @returns {boolean}
   */
  function carriesFiles(event) {
    return event.dataTransfer?.types.includes('Files') ?? false;
  }

  function wireEvents() {
    document.querySelectorAll('[data-ui-language]').forEach((button) => {
      button.addEventListener('click', () => {
        setUiLanguage(uiText.pickUiLanguage([String(/** @type {HTMLElement} */ (button).dataset.uiLanguage)]));
      });
    });
    byId('download-config').addEventListener('click', downloadConfig);
    byId('copy-prompt').addEventListener('click', () => void copyPrompt());
    byId('reset-config').addEventListener('click', resetConfig);
    const fileInput = /** @type {HTMLInputElement} */ (byId('config-file-input'));
    fileInput.addEventListener('change', () => {
      const file = fileInput.files?.[0];
      if (file) {
        void loadConfigFile(file).finally(() => {
          fileInput.value = '';
        });
      }
    });

    const overlay = byId('drop-overlay');
    document.addEventListener('dragenter', (event) => {
      if (carriesFiles(event)) {
        state.dragDepth += 1;
        overlay.hidden = false;
      }
    });
    document.addEventListener('dragleave', (event) => {
      if (carriesFiles(event)) {
        state.dragDepth = Math.max(0, state.dragDepth - 1);
        overlay.hidden = state.dragDepth > 0;
      }
    });
    document.addEventListener('dragover', (event) => {
      if (carriesFiles(event)) {
        event.preventDefault();
      }
    });
    document.addEventListener('drop', (event) => {
      if (!carriesFiles(event)) {
        return;
      }
      event.preventDefault();
      state.dragDepth = 0;
      overlay.hidden = true;
      const file = event.dataTransfer?.files[0];
      if (file) {
        void loadConfigFile(file);
      }
    });

    // Hide the phone bar while the summary itself is on screen.
    const mobileBar = byId('mobile-summary-bar');
    new IntersectionObserver((entries) => {
      mobileBar.classList.toggle(
        'is-hidden',
        entries.some((entry) => entry.isIntersecting),
      );
    }).observe(byId('summary'));
  }

  renderStaticTexts();
  renderForm();
  refreshSummary();
  wireEvents();
  if (draft) {
    showStatus(t('status.draft_restored'), 'info', { label: t('action.reset'), run: resetConfig });
  }
})();
