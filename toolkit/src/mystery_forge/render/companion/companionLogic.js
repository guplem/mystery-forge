// @ts-check
// The decisions of the companion page: answer checks, stage progress, hints, the timer, the accusation score, and the
// saved state. Every function is pure; companionApp.js only wires them to the DOM.
// The page data comes from toolkit/src/mystery_forge/render/companion_data.py.

(function registerCompanionLogic() {
  const STATE_VERSION = 1;
  // About five lines of the intro on a phone: a longer intro pushes the clock and the envelopes off the first screen.
  const LONG_INTRO_CHARACTERS = 240;

  /** @returns {MysteryForgeCompanionState} */
  function freshState() {
    return {
      version: STATE_VERSION,
      solved: [],
      hintSteps: {},
      timer: { elapsedMs: 0, startedAt: null },
      accusation: null,
    };
  }

  /**
   * @param {string} salt
   * @returns {string}
   */
  function storageKey(salt) {
    return `mystery-forge-companion:${salt}`;
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {string} code
   * @returns {MysteryForgeCompanionPuzzle | undefined}
   */
  function findPuzzle(data, code) {
    return data.puzzles.find((puzzle) => puzzle.code === code);
  }

  /**
   * Compare the hash of the normalized input with the stored hashes; the page never holds an answer in plain text
   * outside the solutions.
   * @param {MysteryForgeCompanionData} data
   * @param {string} puzzleCode
   * @param {string} input
   * @returns {MysteryForgeAnswerCheck}
   */
  function checkAnswer(data, puzzleCode, input) {
    const puzzle = findPuzzle(data, puzzleCode);
    if (puzzle === undefined) {
      return { result: 'wrong' };
    }
    const answers = globalThis.MysteryForgeAnswers;
    const hash = answers.answerHash(answers.normalizeAnswer(input, data.language), data.salt);
    if (puzzle.answer_hashes.includes(hash)) {
      return puzzle.unlocks === null ? { result: 'correct' } : { result: 'correct', unlocksStage: puzzle.unlocks };
    }
    const nearMiss = puzzle.near_misses.find((candidate) => candidate.hash === hash);
    return nearMiss === undefined ? { result: 'wrong' } : { result: 'near', message: nearMiss.message };
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {string[]} solvedCodes
   * @returns {string[]}
   */
  function unlockedStages(data, solvedCodes) {
    return data.stages
      .filter((stage) => stage.opens_with === 'start' || solvedCodes.includes(stage.opens_with))
      .map((stage) => stage.id);
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {string[]} unlockedStageIds
   * @returns {MysteryForgeCompanionPuzzle[]}
   */
  function visiblePuzzles(data, unlockedStageIds) {
    return data.puzzles.filter((puzzle) => unlockedStageIds.includes(puzzle.stage));
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {string[]} solvedCodes
   * @returns {boolean}
   */
  function isGameFinished(data, solvedCodes) {
    return data.final_puzzle !== null && solvedCodes.includes(data.final_puzzle);
  }

  /**
   * Return the epilogue with the highest threshold that the percent reaches. `data.epilogues` comes sorted from the
   * highest threshold down.
   * @param {MysteryForgeCompanionData} data
   * @param {number} percent
   * @returns {MysteryForgeCompanionEpilogue | null}
   */
  function epilogueForPercent(data, percent) {
    return data.epilogues.find((epilogue) => percent >= epilogue.min_score_percent) ?? null;
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {Record<string, string>} choices
   * @returns {boolean}
   */
  function isAccusationComplete(data, choices) {
    if (data.deduction === null) {
      return false;
    }
    return data.deduction.questions.every((question) =>
      question.options.some((option) => option.id === choices[question.id]),
    );
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionQuestion} question
   * @param {string | undefined} optionId
   * @returns {boolean}
   */
  function isCorrectOption(data, question, optionId) {
    return globalThis.MysteryForgeAnswers.answerHash(`${question.id}:${optionId}`, data.salt) === question.correct_hash;
  }

  /**
   * The page shows the right option only after the group locks in its accusation.
   * @param {MysteryForgeCompanionData} data
   * @param {string} questionId
   * @returns {string | null}
   */
  function correctOptionId(data, questionId) {
    const question = data.deduction?.questions.find((candidate) => candidate.id === questionId);
    if (question === undefined) {
      return null;
    }
    return question.options.find((option) => isCorrectOption(data, question, option.id))?.id ?? null;
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {Record<string, string>} choices
   * @returns {MysteryForgeAccusationScore}
   */
  function scoreAccusation(data, choices) {
    const questions = data.deduction === null ? [] : data.deduction.questions;
    const correctQuestions = questions
      .filter((question) => isCorrectOption(data, question, choices[question.id]))
      .map((question) => question.id);
    const maxPoints = questions.reduce((sum, question) => sum + question.points, 0);
    const points = questions
      .filter((question) => correctQuestions.includes(question.id))
      .reduce((sum, question) => sum + question.points, 0);
    // Round down, so that a score just below a threshold never reaches its epilogue.
    const percent = maxPoints === 0 ? 0 : Math.floor((points * 100) / maxPoints);
    return { points, maxPoints, percent, epilogue: epilogueForPercent(data, percent), correctQuestions };
  }

  /**
   * @param {number} seconds
   * @returns {string}
   */
  function formatTimer(seconds) {
    const whole = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(whole / 3600);
    const minutes = String(Math.floor((whole % 3600) / 60)).padStart(2, '0');
    const rest = String(whole % 60).padStart(2, '0');
    return hours > 0 ? `${hours}:${minutes}:${rest}` : `${minutes}:${rest}`;
  }

  /**
   * @param {MysteryForgeCompanionTimer} timer
   * @param {number} nowMs
   * @returns {number}
   */
  function timerElapsedMs(timer, nowMs) {
    // A clock that moved back (a changed system time) must not make the time run backwards.
    return timer.elapsedMs + (timer.startedAt === null ? 0 : Math.max(0, nowMs - timer.startedAt));
  }

  /**
   * @param {MysteryForgeCompanionState} state
   * @param {number} nowMs
   * @returns {MysteryForgeCompanionState}
   */
  function startTimer(state, nowMs) {
    if (state.timer.startedAt !== null) {
      return state;
    }
    return { ...state, timer: { elapsedMs: state.timer.elapsedMs, startedAt: nowMs } };
  }

  /**
   * @param {MysteryForgeCompanionState} state
   * @param {number} nowMs
   * @returns {MysteryForgeCompanionState}
   */
  function pauseTimer(state, nowMs) {
    if (state.timer.startedAt === null) {
      return state;
    }
    return { ...state, timer: { elapsedMs: timerElapsedMs(state.timer, nowMs), startedAt: null } };
  }

  /**
   * Count down from the game length; after it, count the extra time up from zero.
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionTimer} timer
   * @param {number} nowMs
   * @returns {{text: string, overtime: boolean}}
   */
  function timerDisplay(data, timer, nowMs) {
    const remaining = data.duration_minutes * 60 - Math.floor(timerElapsedMs(timer, nowMs) / 1000);
    return { text: formatTimer(Math.abs(remaining)), overtime: remaining < 0 };
  }

  /**
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {MysteryForgeCompanionState}
   */
  function withSolved(state, code) {
    return state.solved.includes(code) ? state : { ...state, solved: [...state.solved, code] };
  }

  /**
   * The hint steps of a puzzle are its hints, one level at a time, and then its answer as the last step.
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {number}
   */
  function stepsLeft(data, state, code) {
    const puzzle = findPuzzle(data, code);
    return puzzle === undefined ? 0 : puzzle.hints.length + 1 - (state.hintSteps[code] ?? 0);
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {number | null}
   */
  function nextHintLevel(data, state, code) {
    return stepsLeft(data, state, code) > 1 ? (state.hintSteps[code] ?? 0) + 1 : null;
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {number}
   */
  function revealedHintCount(data, state, code) {
    const puzzle = findPuzzle(data, code);
    return puzzle === undefined ? 0 : Math.min(state.hintSteps[code] ?? 0, puzzle.hints.length);
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {boolean}
   */
  function isAnswerShown(data, state, code) {
    const puzzle = findPuzzle(data, code);
    return puzzle !== undefined && (state.hintSteps[code] ?? 0) > puzzle.hints.length;
  }

  /**
   * @param {MysteryForgeCompanionData} data
   * @param {MysteryForgeCompanionState} state
   * @param {string} code
   * @returns {MysteryForgeCompanionState}
   */
  function withHintStep(data, state, code) {
    if (stepsLeft(data, state, code) <= 0) {
      return state;
    }
    return { ...state, hintSteps: { ...state.hintSteps, [code]: (state.hintSteps[code] ?? 0) + 1 } };
  }

  /**
   * @param {MysteryForgeCompanionState} state
   * @param {Record<string, string>} choices
   * @returns {MysteryForgeCompanionState}
   */
  function withAccusation(state, choices) {
    return { ...state, accusation: { ...choices } };
  }

  /**
   * @param {unknown} value
   * @returns {value is Record<string, unknown>}
   */
  function isRecord(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  /**
   * @param {unknown} value
   * @returns {boolean}
   */
  function isCount(value) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0;
  }

  /**
   * @param {unknown} value
   * @returns {boolean}
   */
  function isTimer(value) {
    return (
      isRecord(value) && isCount(value.elapsedMs) && (value.startedAt === null || typeof value.startedAt === 'number')
    );
  }

  /**
   * @param {unknown} value
   * @returns {value is MysteryForgeCompanionState}
   */
  function isState(value) {
    return (
      isRecord(value) &&
      value.version === STATE_VERSION &&
      Array.isArray(value.solved) &&
      value.solved.every((code) => typeof code === 'string') &&
      isRecord(value.hintSteps) &&
      Object.values(value.hintSteps).every(isCount) &&
      isTimer(value.timer) &&
      (value.accusation === null ||
        (isRecord(value.accusation) && Object.values(value.accusation).every((id) => typeof id === 'string')))
    );
  }

  /**
   * Read the saved state. Storage text that another version or a broken write left behind gives a fresh state, so the
   * page always starts.
   * @param {string | null} text
   * @returns {MysteryForgeCompanionState}
   */
  function stateFromStorage(text) {
    if (text === null) {
      return freshState();
    }
    try {
      const parsed = JSON.parse(text);
      return isState(parsed) ? parsed : freshState();
    } catch {
      return freshState();
    }
  }

  /**
   * @param {MysteryForgeCompanionState} state
   * @returns {string}
   */
  function stateToStorage(state) {
    return JSON.stringify(state);
  }

  /**
   * @param {string} template
   * @param {Record<string, string | number>} values
   * @returns {string}
   */
  function fillText(template, values) {
    return template.replace(/\{(\w+)\}/g, (field, name) => (name in values ? String(values[name]) : field));
  }

  /**
   * Whether a phone folds the intro to its first lines, so that the clock and the envelopes come first.
   * @param {string} intro
   * @returns {boolean}
   */
  function isLongIntro(intro) {
    return intro.length > LONG_INTRO_CHARACTERS;
  }

  globalThis.MysteryForgeCompanionLogic = {
    freshState,
    storageKey,
    checkAnswer,
    unlockedStages,
    visiblePuzzles,
    isGameFinished,
    epilogueForPercent,
    isAccusationComplete,
    scoreAccusation,
    correctOptionId,
    formatTimer,
    timerElapsedMs,
    startTimer,
    pauseTimer,
    timerDisplay,
    withSolved,
    nextHintLevel,
    revealedHintCount,
    isAnswerShown,
    withHintStep,
    withAccusation,
    stateFromStorage,
    stateToStorage,
    fillText,
    isLongIntro,
  };
})();
