// @ts-check
// The DOM glue of the companion page. It holds no game decision: companionLogic.js decides, this file draws the
// views and saves the state. The browser test (toolkit/tests/test_companion_browser.py) covers this file.

(function startCompanionApp() {
  const logic = globalThis.MysteryForgeCompanionLogic;
  const dataElement = /** @type {HTMLElement} */ (document.getElementById('companion-data'));
  /** @type {MysteryForgeCompanionData} */
  const data = JSON.parse(dataElement.textContent ?? '{}');
  const appElement = /** @type {HTMLElement} */ (document.getElementById('app'));
  const key = logic.storageKey(data.salt);

  /** @typedef {'start' | 'check' | 'hints' | 'accuse' | 'solutions'} TabId */
  /** @typedef {{message: string, yes: string, strong: boolean, onYes: () => void}} ConfirmRequest */

  let storageWorks = true;
  let state = loadState();
  const session = {
    /** @type {TabId} */
    tab: 'start',
    /** @type {string | null} */
    checkCode: null,
    draftAnswer: '',
    /** @type {{code: string, check: MysteryForgeAnswerCheck} | null} */
    lastCheck: null,
    solutionsOpen: false,
    /** @type {string[]} */
    shownSolutions: [],
    /** @type {Record<string, string>} */
    draftChoices: {},
    accuseIncomplete: false,
    /** @type {ConfirmRequest | null} */
    confirm: null,
  };

  /** @returns {MysteryForgeCompanionState} */
  function loadState() {
    try {
      return logic.stateFromStorage(window.localStorage.getItem(key));
    } catch {
      storageWorks = false;
      return logic.freshState();
    }
  }

  /** @param {MysteryForgeCompanionState} nextState */
  function saveState(nextState) {
    state = nextState;
    try {
      window.localStorage.setItem(key, logic.stateToStorage(state));
    } catch {
      storageWorks = false;
    }
  }

  /**
   * @param {string} name
   * @param {Record<string, string | number>} [values]
   * @returns {string}
   */
  function ui(name, values = {}) {
    return logic.fillText(data.ui[name] ?? name, values);
  }

  /**
   * @param {string} tag
   * @param {{className?: string, text?: string, attrs?: Record<string, string>}} [options]
   * @param {(Node | null)[]} [children]
   * @returns {HTMLElement}
   */
  function el(tag, options = {}, children = []) {
    const element = document.createElement(tag);
    if (options.className) {
      element.className = options.className;
    }
    if (options.text !== undefined) {
      element.textContent = options.text;
    }
    for (const [name, value] of Object.entries(options.attrs ?? {})) {
      element.setAttribute(name, value);
    }
    for (const child of children) {
      if (child !== null) {
        element.append(child);
      }
    }
    return element;
  }

  /**
   * @param {string} label
   * @param {string} className
   * @param {() => void} onClick
   * @param {Record<string, string>} [attrs]
   * @returns {HTMLElement}
   */
  function button(label, className, onClick, attrs = {}) {
    const element = el('button', { className, text: label, attrs: { type: 'button', ...attrs } });
    element.addEventListener('click', onClick);
    return element;
  }

  /** @param {ConfirmRequest} request */
  function askConfirm(request) {
    session.confirm = request;
    render();
  }

  /** @param {boolean} accepted */
  function closeConfirm(accepted) {
    const request = session.confirm;
    session.confirm = null;
    if (accepted && request !== null) {
      request.onYes();
    }
    render();
  }

  /** @param {TabId} tab */
  function showTab(tab) {
    session.tab = tab;
    render();
    window.scrollTo(0, 0);
  }

  function solvedCodes() {
    return state.solved;
  }

  function openStages() {
    return logic.unlockedStages(data, solvedCodes());
  }

  function openPuzzles() {
    return logic.visiblePuzzles(data, openStages());
  }

  function hasSealedStages() {
    return openStages().length < data.stages.length;
  }

  // ---------- Header, navigation, and the confirm dialog ----------

  function renderTopBar() {
    const timer = el('span', { className: 'topbar-timer', attrs: { 'data-timer-text': '', 'aria-hidden': 'true' } });
    return el('header', { className: 'topbar' }, [
      el('span', { className: 'topbar-kicker', text: ui('page_label') }),
      el('span', { className: 'topbar-title', text: data.title }),
      timer,
    ]);
  }

  /** @returns {[TabId, string, string][]} */
  function tabs() {
    /** @type {[TabId, string, string][]} */
    const list = [
      ['start', ui('tab_start'), 'M4 5h16v14H4zM4 9h16'],
      ['check', ui('tab_check'), 'M5 12l4 4 10-10'],
      [
        'hints',
        ui('tab_hints'),
        'M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z',
      ],
    ];
    if (data.deduction !== null) {
      list.push(['accuse', ui('tab_accuse'), 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM16 16l5 5']);
    }
    list.push(['solutions', ui('tab_solutions'), 'M12 3l9 16H3zM12 10v4M12 17v.5']);
    return list;
  }

  function renderNav() {
    const nav = el('nav', { className: 'tabs', attrs: { 'aria-label': data.title } });
    for (const [id, label, iconPath] of tabs()) {
      const tabButton = button('', `tab${session.tab === id ? ' is-active' : ''}`, () => showTab(id), {
        'data-tab': id,
        'aria-current': session.tab === id ? 'page' : 'false',
      });
      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('viewBox', '0 0 24 24');
      icon.setAttribute('aria-hidden', 'true');
      icon.setAttribute('class', 'tab-icon');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', iconPath);
      icon.append(path);
      tabButton.append(icon, el('span', { className: 'tab-label', text: label }));
      nav.append(tabButton);
    }
    return nav;
  }

  function renderConfirm() {
    const request = session.confirm;
    if (request === null) {
      return null;
    }
    const noButton = button(ui('confirm_no'), 'button button-quiet', () => closeConfirm(false), { id: 'confirm-no' });
    const yesButton = button(
      request.yes,
      `button ${request.strong ? 'button-danger' : 'button-primary'}`,
      () => closeConfirm(true),
      {
        id: 'confirm-yes',
      },
    );
    const dialog = el(
      'div',
      {
        className: `dialog paper${request.strong ? ' dialog-strong' : ''}`,
        attrs: {
          role: 'alertdialog',
          'aria-modal': 'true',
          'aria-labelledby': 'confirm-message',
          id: 'confirm-dialog',
        },
      },
      [
        el('p', { className: 'dialog-message', text: request.message, attrs: { id: 'confirm-message' } }),
        el('div', { className: 'dialog-actions' }, [noButton, yesButton]),
      ],
    );
    const overlay = el('div', { className: 'overlay' }, [dialog]);
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay) {
        closeConfirm(false);
      }
    });
    return overlay;
  }

  // ---------- Start ----------

  function renderTimerCard() {
    const running = state.timer.startedAt !== null;
    const started = running || state.timer.elapsedMs > 0;
    const label = running ? ui('timer_pause') : started ? ui('timer_resume') : ui('timer_start');
    const toggle = button(
      label,
      `button ${running ? 'button-quiet' : 'button-primary'} timer-toggle`,
      () => {
        const now = Date.now();
        saveState(running ? logic.pauseTimer(state, now) : logic.startTimer(state, now));
        render();
      },
      { id: 'timer-toggle' },
    );
    return el('section', { className: `timer-card${running ? ' is-running' : ''}` }, [
      el('p', { className: 'timer-label', attrs: { 'data-timer-label': '' } }),
      el('p', { className: 'timer-digits', attrs: { 'data-timer-text': '', id: 'timer-text', role: 'timer' } }),
      el('p', { className: 'timer-length', text: ui('game_length', { minutes: data.duration_minutes }) }),
      toggle,
    ]);
  }

  function renderEnvelopes() {
    const open = openStages();
    const list = el('ul', { className: 'envelopes' });
    for (const stage of data.stages) {
      const isOpen = open.includes(stage.id);
      list.append(
        el('li', { className: `envelope${isOpen ? ' is-open' : ''}`, attrs: { 'data-stage': stage.id } }, [
          el('span', { className: 'envelope-flap', attrs: { 'aria-hidden': 'true' } }),
          el('span', { className: 'envelope-name', text: stage.envelope }),
          el('span', {
            className: `chip ${isOpen ? 'chip-open' : 'chip-sealed'}`,
            text: isOpen ? ui('envelope_open') : ui('envelope_sealed'),
          }),
          // A sealed envelope shows only its letter: its label could hint at what comes next.
          isOpen ? el('span', { className: 'envelope-label', text: stage.label }) : null,
        ]),
      );
    }
    return el('section', { className: 'section' }, [
      el('h2', { className: 'section-title', text: ui('envelopes_heading') }),
      list,
    ]);
  }

  function renderEnding() {
    if (data.deduction !== null || !logic.isGameFinished(data, solvedCodes())) {
      return null;
    }
    const epilogue = logic.epilogueForPercent(data, 100);
    return el('section', { className: 'paper ending reveal-in', attrs: { id: 'ending' } }, [
      el('p', { className: 'stamp', text: ui('final_solved') }),
      el('h2', { className: 'paper-title', text: epilogue ? epilogue.title : ui('ending_heading') }),
      epilogue ? el('p', { text: epilogue.text }) : null,
    ]);
  }

  function renderHelp() {
    const steps = el('ol', { className: 'help-steps' });
    for (const name of ['help_1', 'help_2', 'help_3', 'help_4', 'help_5']) {
      steps.append(el('li', { text: ui(name) }));
    }
    return el('details', { className: 'help paper' }, [el('summary', { text: ui('tab_help') }), steps]);
  }

  function renderStart() {
    const reset = button(ui('reset'), 'button button-link', () =>
      askConfirm({
        message: ui('reset_confirm'),
        yes: ui('reset'),
        strong: true,
        onYes: () => {
          saveState(logic.freshState());
          session.lastCheck = null;
          session.draftChoices = {};
          session.shownSolutions = [];
          session.solutionsOpen = false;
        },
      }),
    );
    return el('div', { className: 'view' }, [
      el('div', { className: 'hero' }, [
        el('p', { className: 'kicker', text: ui('page_label') }),
        el('h1', { className: 'hero-title', text: data.title }),
        data.tagline ? el('p', { className: 'hero-tagline', text: data.tagline }) : null,
      ]),
      storageWorks ? null : el('p', { className: 'notice', text: ui('storage_off'), attrs: { id: 'storage-off' } }),
      renderEnding(),
      el('section', { className: 'paper intro', attrs: { id: 'intro' } }, [
        el('p', { className: 'paper-kicker', text: ui('read_aloud') }),
        el('p', { className: 'intro-text', text: data.intro }),
      ]),
      renderTimerCard(),
      renderEnvelopes(),
      renderHelp(),
      el('p', { className: 'reset-row' }, [reset]),
    ]);
  }

  // ---------- Check an answer ----------

  /**
   * @param {MysteryForgeCompanionPuzzle[]} puzzles
   * @returns {string | null}
   */
  function selectedCheckCode(puzzles) {
    if (puzzles.some((puzzle) => puzzle.code === session.checkCode)) {
      return session.checkCode;
    }
    const unsolved = puzzles.find((puzzle) => !solvedCodes().includes(puzzle.code));
    return (unsolved ?? puzzles[0])?.code ?? null;
  }

  /** @param {string} code */
  function submitAnswer(code) {
    if (session.draftAnswer.trim() === '') {
      return;
    }
    const check = logic.checkAnswer(data, code, session.draftAnswer);
    // Keep this puzzle selected: after a correct answer, its result card holds the call to open the next envelope.
    session.checkCode = code;
    session.lastCheck = { code, check };
    if (check.result === 'correct') {
      saveState(logic.withSolved(state, code));
      session.draftAnswer = '';
    }
    render();
    const input = document.getElementById('answer-input');
    if (input instanceof HTMLInputElement && check.result !== 'correct') {
      input.focus();
      input.select();
    }
    // On a phone, the result card sits below the keyboard and the form; bring it into view.
    document.getElementById('answer-result')?.scrollIntoView({ block: 'nearest' });
  }

  /**
   * @param {MysteryForgeAnswerCheck} check
   * @returns {HTMLElement}
   */
  function renderResult(check) {
    if (check.result === 'wrong') {
      return el('div', { className: 'result result-wrong', attrs: { id: 'answer-result', 'data-result': 'wrong' } }, [
        el('p', { className: 'result-title', text: ui('result_wrong') }),
      ]);
    }
    if (check.result === 'near') {
      return el('div', { className: 'result result-near', attrs: { id: 'answer-result', 'data-result': 'near' } }, [
        el('p', { className: 'result-title', text: ui('result_near') }),
        el('p', { className: 'result-message', text: check.message ?? '' }),
      ]);
    }
    const stage = data.stages.find((candidate) => candidate.id === check.unlocksStage);
    const finished = logic.isGameFinished(data, solvedCodes());
    return el('div', { className: 'result result-correct', attrs: { id: 'answer-result', 'data-result': 'correct' } }, [
      el('p', { className: 'stamp stamp-ok', text: ui('result_correct') }),
      stage
        ? el('div', { className: 'unlock', attrs: { id: 'unlock-call' } }, [
            el('span', { className: 'unlock-envelope', attrs: { 'aria-hidden': 'true' } }),
            el('p', { className: 'unlock-title', text: ui('unlock_call', { envelope: stage.envelope }) }),
            stage.opening_text ? el('p', { className: 'unlock-text', text: stage.opening_text }) : null,
          ])
        : null,
      finished && data.deduction !== null
        ? button(ui('accuse_heading'), 'button button-primary', () => showTab('accuse'))
        : null,
      finished && data.deduction === null
        ? button(ui('ending_heading'), 'button button-primary', () => showTab('start'))
        : null,
    ]);
  }

  function renderCheck() {
    const puzzles = openPuzzles();
    const view = el('div', { className: 'view' }, [el('h2', { className: 'view-title', text: ui('check_heading') })]);
    const code = selectedCheckCode(puzzles);
    if (code === null) {
      view.append(el('p', { className: 'empty', text: ui('no_puzzles') }));
      return view;
    }
    const picker = el('div', {
      className: 'puzzle-picker',
      attrs: { role: 'group', 'aria-label': ui('check_puzzle_label') },
    });
    for (const puzzle of puzzles) {
      const solved = solvedCodes().includes(puzzle.code);
      const pick = button(
        '',
        `puzzle-chip${puzzle.code === code ? ' is-selected' : ''}${solved ? ' is-solved' : ''}`,
        () => {
          session.checkCode = puzzle.code;
          session.lastCheck = null;
          render();
        },
        { 'data-puzzle': puzzle.code, 'aria-pressed': String(puzzle.code === code) },
      );
      pick.append(
        el('span', { className: 'puzzle-code', text: puzzle.code }),
        el('span', { className: 'puzzle-title', text: puzzle.title }),
      );
      if (solved) {
        pick.append(el('span', { className: 'puzzle-solved', text: `✓ ${ui('result_solved')}` }));
      }
      picker.append(pick);
    }
    view.append(el('p', { className: 'field-label', text: ui('check_puzzle_label') }), picker);
    if (hasSealedStages()) {
      view.append(el('p', { className: 'locked-note', text: ui('locked_note') }));
    }
    const puzzle = /** @type {MysteryForgeCompanionPuzzle} */ (puzzles.find((candidate) => candidate.code === code));
    const input = /** @type {HTMLInputElement} */ (
      el('input', {
        className: 'answer-input',
        attrs: {
          id: 'answer-input',
          type: 'text',
          autocomplete: 'off',
          autocapitalize: 'off',
          spellcheck: 'false',
          enterkeyhint: 'done',
        },
      })
    );
    input.value = session.draftAnswer;
    input.addEventListener('input', () => {
      session.draftAnswer = input.value;
    });
    const form = el('form', { className: 'answer-form paper', attrs: { id: 'answer-form' } }, [
      el('label', {
        className: 'paper-kicker',
        text: `${puzzle.code} · ${ui('check_answer_label')}`,
        attrs: { for: 'answer-input' },
      }),
      el('p', { className: 'answer-format', text: puzzle.answer_format }),
      input,
      el('button', {
        className: 'button button-primary button-wide',
        text: ui('check_submit'),
        attrs: { type: 'submit', id: 'answer-submit' },
      }),
    ]);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      submitAnswer(puzzle.code);
    });
    view.append(form);
    const live = el('div', { className: 'result-slot', attrs: { 'aria-live': 'polite' } });
    if (session.lastCheck !== null && session.lastCheck.code === puzzle.code) {
      live.append(renderResult(session.lastCheck.check));
    }
    view.append(live);
    return view;
  }

  // ---------- Hints ----------

  /** @param {MysteryForgeCompanionPuzzle} puzzle */
  function renderHintCard(puzzle) {
    const revealed = logic.revealedHintCount(data, state, puzzle.code);
    const nextLevel = logic.nextHintLevel(data, state, puzzle.code);
    const answerShown = logic.isAnswerShown(data, state, puzzle.code);
    const list = el('ol', { className: 'hint-list' });
    for (const hint of puzzle.hints.slice(0, revealed)) {
      list.append(
        el('li', { className: 'hint reveal-in', attrs: { 'data-hint-level': String(hint.level) } }, [
          el('span', { className: 'hint-label', text: ui('hint_label', { level: hint.level }) }),
          el('span', { className: 'hint-text', text: hint.text }),
        ]),
      );
    }
    const solved = solvedCodes().includes(puzzle.code);
    const card = el('article', { className: 'paper hint-card', attrs: { 'data-hint-card': puzzle.code } }, [
      el('p', { className: 'paper-kicker' }, [
        el('span', { className: 'code-badge', text: puzzle.code }),
        el('span', { className: 'card-title', text: puzzle.title }),
        solved ? el('span', { className: 'chip chip-solved', text: `✓ ${ui('result_solved')}` }) : null,
      ]),
      revealed > 0 ? list : null,
    ]);
    if (answerShown) {
      card.append(
        el('p', { className: 'answer-box reveal-in', attrs: { 'data-answer': puzzle.code } }, [
          document.createTextNode(ui('solution_answer', { answer: '' })),
          el('strong', { text: puzzle.solution.answer }),
        ]),
      );
    } else if (nextLevel !== null) {
      card.append(
        button(
          ui('hint_show', { level: nextLevel }),
          'button button-primary',
          () =>
            askConfirm({
              message: ui('hint_confirm', { level: nextLevel, code: puzzle.code }),
              yes: ui('confirm_yes'),
              strong: false,
              onYes: () => saveState(logic.withHintStep(data, state, puzzle.code)),
            }),
          { 'data-hint-button': puzzle.code },
        ),
      );
    } else {
      card.append(
        button(
          ui('answer_show'),
          'button button-danger-quiet',
          () =>
            askConfirm({
              message: ui('answer_confirm', { code: puzzle.code }),
              yes: ui('confirm_yes'),
              strong: true,
              onYes: () => saveState(logic.withHintStep(data, state, puzzle.code)),
            }),
          { 'data-hint-button': puzzle.code },
        ),
      );
    }
    return card;
  }

  function renderHints() {
    const view = el('div', { className: 'view' }, [
      el('h2', { className: 'view-title', text: ui('hints_heading') }),
      el('p', { className: 'view-intro', text: ui('hints_intro') }),
    ]);
    const puzzles = openPuzzles();
    if (puzzles.length === 0) {
      view.append(el('p', { className: 'empty', text: ui('no_puzzles') }));
    }
    for (const puzzle of puzzles) {
      view.append(renderHintCard(puzzle));
    }
    if (hasSealedStages()) {
      view.append(el('p', { className: 'locked-note', text: ui('locked_note') }));
    }
    return view;
  }

  // ---------- Accusation ----------

  /**
   * @param {{questions: MysteryForgeCompanionQuestion[]}} deduction
   * @param {Record<string, string>} choices
   */
  function renderAccusationResult(deduction, choices) {
    const score = logic.scoreAccusation(data, choices);
    const answersList = el('ol', { className: 'verdicts' });
    for (const question of deduction.questions) {
      const right = score.correctQuestions.includes(question.id);
      const chosen = question.options.find((option) => option.id === choices[question.id]);
      const correctId = logic.correctOptionId(data, question.id);
      const correct = question.options.find((option) => option.id === correctId);
      answersList.append(
        el('li', { className: `verdict ${right ? 'is-right' : 'is-wrong'}` }, [
          el('span', { className: 'verdict-mark', text: right ? ui('question_right') : ui('question_wrong') }),
          el('span', { className: 'verdict-prompt', text: question.prompt }),
          el('span', { className: 'verdict-choice', text: chosen ? chosen.text : '' }),
          !right && correct ? el('span', { className: 'verdict-correct', text: `→ ${correct.text}` }) : null,
        ]),
      );
    }
    const reveal = el('ol', { className: 'reveal-steps' });
    for (const step of data.reveal) {
      reveal.append(el('li', { text: step }));
    }
    return el('div', { className: 'view', attrs: { id: 'accuse-result' } }, [
      el('h2', { className: 'view-title', text: ui('accuse_heading') }),
      el('section', { className: 'paper score-card reveal-in' }, [
        el('p', {
          className: 'score-points',
          text: ui('score', { points: score.points, max: score.maxPoints }),
          attrs: { id: 'accuse-score' },
        }),
        el('p', { className: 'score-percent', text: `${score.percent}%` }),
        score.epilogue
          ? el('p', { className: 'stamp stamp-rank', text: score.epilogue.title, attrs: { id: 'accuse-rank' } })
          : null,
        score.epilogue
          ? el('p', { className: 'epilogue-text', text: score.epilogue.text, attrs: { id: 'accuse-epilogue' } })
          : null,
      ]),
      answersList,
      data.reveal.length > 0
        ? el('section', { className: 'paper reveal-card' }, [
            el('h3', { className: 'paper-title', text: ui('reveal_heading') }),
            reveal,
          ])
        : null,
    ]);
  }

  /** @param {{questions: MysteryForgeCompanionQuestion[]}} deduction */
  function renderAccusationForm(deduction) {
    const form = el('form', { className: 'accuse-form', attrs: { id: 'accuse-form' } });
    for (const question of deduction.questions) {
      const fieldset = el('fieldset', { className: 'paper question' }, [
        el('legend', { className: 'question-prompt', text: question.prompt }),
      ]);
      for (const option of question.options) {
        const radio = /** @type {HTMLInputElement} */ (
          el('input', { attrs: { type: 'radio', name: `question-${question.id}`, value: option.id } })
        );
        radio.checked = session.draftChoices[question.id] === option.id;
        radio.addEventListener('change', () => {
          session.draftChoices = { ...session.draftChoices, [question.id]: option.id };
          session.accuseIncomplete = false;
        });
        fieldset.append(
          el('label', { className: 'option' }, [radio, el('span', { className: 'option-text', text: option.text })]),
        );
      }
      form.append(fieldset);
    }
    form.append(
      el('p', {
        className: `notice notice-quiet${session.accuseIncomplete ? '' : ' is-hidden'}`,
        text: ui('accuse_incomplete'),
        attrs: { id: 'accuse-incomplete' },
      }),
      el('button', {
        className: 'button button-primary button-wide',
        text: ui('accuse_submit'),
        attrs: { type: 'submit', id: 'accuse-submit' },
      }),
    );
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!logic.isAccusationComplete(data, session.draftChoices)) {
        session.accuseIncomplete = true;
        render();
        return;
      }
      const choices = session.draftChoices;
      askConfirm({
        message: ui('accuse_confirm'),
        yes: ui('accuse_submit'),
        strong: false,
        onYes: () => {
          saveState(logic.withAccusation(state, choices));
          window.scrollTo(0, 0);
        },
      });
    });
    return el('div', { className: 'view' }, [
      el('h2', { className: 'view-title', text: ui('accuse_heading') }),
      el('p', { className: 'view-intro', text: ui('accuse_intro') }),
      logic.isGameFinished(data, solvedCodes())
        ? null
        : el('p', { className: 'notice notice-quiet', text: ui('accuse_early') }),
      form,
    ]);
  }

  function renderAccuse() {
    if (data.deduction === null) {
      return renderStart();
    }
    return state.accusation === null
      ? renderAccusationForm(data.deduction)
      : renderAccusationResult(data.deduction, state.accusation);
  }

  // ---------- Solutions ----------

  function renderSolutions() {
    if (!session.solutionsOpen) {
      return el('div', { className: 'view warning-view', attrs: { id: 'solutions-warning' } }, [
        el('p', { className: 'warning-sign', text: '!', attrs: { 'aria-hidden': 'true' } }),
        el('h2', { className: 'view-title', text: ui('solutions_warning_title') }),
        el('p', { className: 'warning-text', text: ui('solutions_warning_text') }),
        button(
          ui('solutions_enter'),
          'button button-danger button-wide',
          () => {
            session.solutionsOpen = true;
            render();
          },
          { id: 'solutions-enter' },
        ),
      ]);
    }
    const view = el('div', { className: 'view' }, [el('h2', { className: 'view-title', text: ui('tab_solutions') })]);
    for (const puzzle of openPuzzles()) {
      const shown = session.shownSolutions.includes(puzzle.code);
      const card = el('article', { className: 'paper solution-card', attrs: { 'data-solution-card': puzzle.code } }, [
        el('p', { className: 'paper-kicker' }, [
          el('span', { className: 'code-badge', text: puzzle.code }),
          el('span', { className: 'card-title', text: puzzle.title }),
        ]),
      ]);
      if (shown) {
        const steps = el('ol', { className: 'solution-steps reveal-in' });
        for (const step of puzzle.solution.steps) {
          steps.append(el('li', { text: step }));
        }
        card.append(
          steps,
          el('p', { className: 'answer-box reveal-in' }, [
            document.createTextNode(ui('solution_answer', { answer: '' })),
            el('strong', { text: puzzle.solution.answer }),
          ]),
        );
      } else {
        card.append(
          button(
            ui('solution_show', { code: puzzle.code }),
            'button button-danger-quiet',
            () => {
              session.shownSolutions = [...session.shownSolutions, puzzle.code];
              render();
            },
            { 'data-solution-button': puzzle.code },
          ),
        );
      }
      view.append(card);
    }
    if (hasSealedStages()) {
      view.append(el('p', { className: 'locked-note', text: ui('locked_note') }));
    }
    return view;
  }

  // ---------- Render loop ----------

  /** @type {Record<TabId, () => HTMLElement>} */
  const VIEWS = {
    start: renderStart,
    check: renderCheck,
    hints: renderHints,
    accuse: renderAccuse,
    solutions: renderSolutions,
  };

  function updateTimers() {
    const display = logic.timerDisplay(data, state.timer, Date.now());
    for (const element of document.querySelectorAll('[data-timer-text]')) {
      element.textContent = display.overtime ? `+${display.text}` : display.text;
      element.classList.toggle('is-overtime', display.overtime);
    }
    for (const element of document.querySelectorAll('[data-timer-label]')) {
      element.textContent = display.overtime ? ui('timer_overtime') : ui('timer_label');
    }
  }

  function render() {
    const main = el('main', { className: `main main-${session.tab}`, attrs: { id: 'main' } }, [VIEWS[session.tab]()]);
    appElement.replaceChildren(renderTopBar(), main, renderNav());
    const overlay = renderConfirm();
    if (overlay !== null) {
      appElement.append(overlay);
      document.getElementById('confirm-no')?.focus();
    }
    document.body.classList.toggle('has-dialog', overlay !== null);
    updateTimers();
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && session.confirm !== null) {
      closeConfirm(false);
    }
  });
  window.setInterval(updateTimers, 1000);
  render();
})();
