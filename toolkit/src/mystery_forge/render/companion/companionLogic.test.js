// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

// Classic browser scripts, not modules: load them for their side effect, by a computed path that tsc does not resolve.
require(path.join(__dirname, 'answers.js'));
require(path.join(__dirname, 'companionLogic.js'));
const answers = globalThis.MysteryForgeAnswers;
const logic = globalThis.MysteryForgeCompanionLogic;

const SALT = 'test-salt';

/**
 * @param {string} text
 * @returns {string}
 */
function hashed(text) {
  return answers.answerHash(answers.normalizeAnswer(text, 'en'), SALT);
}

/** @returns {MysteryForgeCompanionData} */
function sampleData() {
  return {
    format_version: 1,
    title: 'The Lens of Gull Rock',
    tagline: 'The light went dark.',
    intro: 'Read me aloud.',
    language: 'en',
    salt: SALT,
    duration_minutes: 30,
    panel_verified: true,
    final_puzzle: 'B1',
    ui: { score: '{points} of {max} points' },
    stages: [
      { id: 'A', label: 'Desk', envelope: 'Envelope A', opens_with: 'start', opening_text: '' },
      { id: 'B', label: 'Box', envelope: 'Envelope B', opens_with: 'A1', opening_text: 'Inside the box.' },
    ],
    puzzles: [
      {
        code: 'A1',
        title: 'Coded line',
        stage: 'A',
        answer_format: 'one word',
        answer_hashes: [hashed('boathouse')],
        near_misses: [{ hash: hashed('yxlxqeorpb'), message: 'Count back, not forward.' }],
        unlocks: 'B',
        hints: [
          { level: 1, text: 'Look down.' },
          { level: 2, text: 'Three steps.' },
        ],
        solution: { steps: ['Shift back.'], answer: 'boathouse' },
      },
      {
        code: 'A2',
        title: 'Lock',
        stage: 'A',
        answer_format: 'a 4-digit code',
        answer_hashes: [hashed('0726')],
        near_misses: [],
        unlocks: null,
        hints: [{ level: 1, text: 'Receipt.' }],
        solution: { steps: ['Read it.'], answer: '0726' },
      },
      {
        code: 'B1',
        title: 'Tide',
        stage: 'B',
        answer_format: 'two words',
        answer_hashes: [hashed('low tide'), hashed('at low tide')],
        near_misses: [],
        unlocks: null,
        hints: [{ level: 1, text: 'The sea.' }],
        solution: { steps: ['Tide table.'], answer: 'low tide' },
      },
    ],
    deduction: {
      questions: [
        {
          id: 'who',
          prompt: 'Who?',
          options: [
            { id: 'ana', text: 'Ana' },
            { id: 'felix', text: 'Felix' },
          ],
          correct_hash: answers.answerHash('who:felix', SALT),
          points: 50,
        },
        {
          id: 'why',
          prompt: 'Why?',
          options: [
            { id: 'debt', text: 'Debt' },
            { id: 'prank', text: 'Prank' },
          ],
          correct_hash: answers.answerHash('why:debt', SALT),
          points: 25,
        },
      ],
    },
    epilogues: [
      { min_score_percent: 75, title: 'Case closed', text: 'Solved.' },
      { min_score_percent: 40, title: 'Close', text: 'Partly.' },
      { min_score_percent: 10, title: 'Dark', text: 'Unsolved.' },
    ],
    reveal: ['By boat.'],
  };
}

test('checkAnswer accepts the answer in any spelling and names the stage that it opens', () => {
  assert.deepEqual(logic.checkAnswer(sampleData(), 'A1', ' Boat-House '), { result: 'correct', unlocksStage: 'B' });
  assert.deepEqual(logic.checkAnswer(sampleData(), 'B1', 'At LOW tide!'), { result: 'correct' });
});

test('checkAnswer gives the message of a near miss', () => {
  assert.deepEqual(logic.checkAnswer(sampleData(), 'A1', 'YXLXQEORPB'), {
    result: 'near',
    message: 'Count back, not forward.',
  });
});

test('checkAnswer says wrong for another answer, for the answer of another puzzle, and for an unknown code', () => {
  assert.deepEqual(logic.checkAnswer(sampleData(), 'A1', 'lighthouse'), { result: 'wrong' });
  assert.deepEqual(logic.checkAnswer(sampleData(), 'A2', 'boathouse'), { result: 'wrong' });
  assert.deepEqual(logic.checkAnswer(sampleData(), 'Z9', 'boathouse'), { result: 'wrong' });
});

test('unlockedStages opens the first stage at the start and each later stage with its puzzle', () => {
  assert.deepEqual(logic.unlockedStages(sampleData(), []), ['A']);
  assert.deepEqual(logic.unlockedStages(sampleData(), ['A2']), ['A']);
  assert.deepEqual(logic.unlockedStages(sampleData(), ['A1']), ['A', 'B']);
});

test('visiblePuzzles shows only the puzzles of the open stages', () => {
  const codes = (/** @type {string[]} */ stages) => logic.visiblePuzzles(sampleData(), stages).map((p) => p.code);
  assert.deepEqual(codes(['A']), ['A1', 'A2']);
  assert.deepEqual(codes(['A', 'B']), ['A1', 'A2', 'B1']);
});

test('isGameFinished is true once the final puzzle is solved, and never without a final puzzle', () => {
  assert.equal(logic.isGameFinished(sampleData(), ['A1']), false);
  assert.equal(logic.isGameFinished(sampleData(), ['A1', 'B1']), true);
  assert.equal(logic.isGameFinished({ ...sampleData(), final_puzzle: null }, ['B1']), false);
});

test('scoreAccusation adds the points of the right answers and picks the epilogue that the score reaches', () => {
  const full = logic.scoreAccusation(sampleData(), { who: 'felix', why: 'debt' });
  assert.deepEqual(full, {
    points: 75,
    maxPoints: 75,
    percent: 100,
    epilogue: { min_score_percent: 75, title: 'Case closed', text: 'Solved.' },
    correctQuestions: ['who', 'why'],
  });
  const partial = logic.scoreAccusation(sampleData(), { who: 'felix', why: 'prank' });
  assert.equal(partial.percent, 66);
  assert.equal(partial.epilogue?.title, 'Close');
  assert.deepEqual(partial.correctQuestions, ['who']);
});

test('scoreAccusation gives no epilogue when the score reaches none, and zero points without a deduction', () => {
  const none = logic.scoreAccusation(sampleData(), {});
  assert.equal(none.points, 0);
  assert.equal(none.epilogue, null);
  const noDeduction = logic.scoreAccusation({ ...sampleData(), deduction: null }, {});
  assert.deepEqual([noDeduction.points, noDeduction.maxPoints, noDeduction.percent], [0, 0, 0]);
});

test('epilogueForPercent picks the highest threshold that the percent reaches', () => {
  assert.equal(logic.epilogueForPercent(sampleData(), 100)?.title, 'Case closed');
  assert.equal(logic.epilogueForPercent(sampleData(), 40)?.title, 'Close');
  assert.equal(logic.epilogueForPercent(sampleData(), 5), null);
});

test('isAccusationComplete needs a valid option for every question', () => {
  assert.equal(logic.isAccusationComplete(sampleData(), { who: 'felix' }), false);
  assert.equal(logic.isAccusationComplete(sampleData(), { who: 'felix', why: 'nope' }), false);
  assert.equal(logic.isAccusationComplete(sampleData(), { who: 'ana', why: 'prank' }), true);
  assert.equal(logic.isAccusationComplete({ ...sampleData(), deduction: null }, {}), false);
});

test('formatTimer shows minutes and seconds, and hours only when needed', () => {
  assert.equal(logic.formatTimer(0), '00:00');
  assert.equal(logic.formatTimer(65.9), '01:05');
  assert.equal(logic.formatTimer(3600 + 62), '1:01:02');
  assert.equal(logic.formatTimer(-5), '00:00');
});

test('the timer counts while it runs, keeps its time when paused, and ignores a repeated start or pause', () => {
  let state = logic.freshState();
  assert.equal(logic.timerElapsedMs(state.timer, 5000), 0);
  state = logic.startTimer(state, 1000);
  assert.equal(logic.startTimer(state, 9000), state);
  assert.equal(logic.timerElapsedMs(state.timer, 4000), 3000);
  assert.equal(logic.timerElapsedMs(state.timer, 500), 0);
  state = logic.pauseTimer(state, 6000);
  assert.equal(logic.pauseTimer(state, 9000), state);
  assert.deepEqual(state.timer, { elapsedMs: 5000, startedAt: null });
  assert.equal(logic.timerElapsedMs(state.timer, 99000), 5000);
});

test('timerDisplay counts down from the game length, then counts the extra time', () => {
  const data = sampleData();
  assert.deepEqual(logic.timerDisplay(data, { elapsedMs: 0, startedAt: null }, 0), { text: '30:00', overtime: false });
  assert.deepEqual(logic.timerDisplay(data, { elapsedMs: 61500, startedAt: null }, 0), {
    text: '28:59',
    overtime: false,
  });
  assert.deepEqual(logic.timerDisplay(data, { elapsedMs: 1800000 + 75000, startedAt: null }, 0), {
    text: '01:15',
    overtime: true,
  });
});

test('withSolved adds a code once', () => {
  const state = logic.withSolved(logic.freshState(), 'A1');
  assert.deepEqual(state.solved, ['A1']);
  assert.equal(logic.withSolved(state, 'A1'), state);
});

test('hints open one level at a time, then the answer, then nothing more', () => {
  const data = sampleData();
  let state = logic.freshState();
  assert.equal(logic.nextHintLevel(data, state, 'A1'), 1);
  assert.equal(logic.revealedHintCount(data, state, 'A1'), 0);
  assert.equal(logic.isAnswerShown(data, state, 'A1'), false);
  state = logic.withHintStep(data, state, 'A1');
  assert.equal(logic.nextHintLevel(data, state, 'A1'), 2);
  state = logic.withHintStep(data, state, 'A1');
  assert.equal(logic.nextHintLevel(data, state, 'A1'), null);
  assert.equal(logic.revealedHintCount(data, state, 'A1'), 2);
  assert.equal(logic.isAnswerShown(data, state, 'A1'), false);
  state = logic.withHintStep(data, state, 'A1');
  assert.equal(logic.isAnswerShown(data, state, 'A1'), true);
  assert.equal(logic.revealedHintCount(data, state, 'A1'), 2);
  assert.equal(logic.withHintStep(data, state, 'A1'), state);
  assert.equal(logic.nextHintLevel(data, state, 'A2'), 1);
});

test('the hint functions treat an unknown puzzle code as having nothing to show', () => {
  const state = logic.freshState();
  assert.equal(logic.nextHintLevel(sampleData(), state, 'Z9'), null);
  assert.equal(logic.revealedHintCount(sampleData(), state, 'Z9'), 0);
  assert.equal(logic.isAnswerShown(sampleData(), state, 'Z9'), false);
});

test('withAccusation stores a copy of the choices', () => {
  const choices = { who: 'felix' };
  const state = logic.withAccusation(logic.freshState(), choices);
  choices.who = 'ana';
  assert.deepEqual(state.accusation, { who: 'felix' });
});

test('the state survives a round trip through storage text', () => {
  let state = logic.withSolved(logic.freshState(), 'A1');
  state = logic.withHintStep(sampleData(), state, 'A2');
  state = logic.startTimer(state, 1234);
  state = logic.withAccusation(state, { who: 'felix' });
  assert.deepEqual(logic.stateFromStorage(logic.stateToStorage(state)), state);
});

test('stateFromStorage returns a fresh state for missing, corrupt, or foreign storage text', () => {
  const fresh = logic.freshState();
  const valid = JSON.parse(logic.stateToStorage(fresh));
  /** @type {(string | null)[]} */
  const broken = [
    null,
    '',
    '{not json',
    'null',
    '[]',
    '42',
    JSON.stringify({ ...valid, version: 2 }),
    JSON.stringify({ ...valid, solved: 'A1' }),
    JSON.stringify({ ...valid, solved: [1] }),
    JSON.stringify({ ...valid, hintSteps: null }),
    JSON.stringify({ ...valid, hintSteps: [] }),
    JSON.stringify({ ...valid, hintSteps: { A1: 'two' } }),
    JSON.stringify({ ...valid, hintSteps: { A1: -1 } }),
    JSON.stringify({ ...valid, timer: null }),
    JSON.stringify({ ...valid, timer: { elapsedMs: 'x', startedAt: null } }),
    JSON.stringify({ ...valid, timer: { elapsedMs: -1, startedAt: null } }),
    JSON.stringify({ ...valid, timer: { elapsedMs: 0, startedAt: 'now' } }),
    JSON.stringify({ ...valid, accusation: 'felix' }),
    JSON.stringify({ ...valid, accusation: { who: 3 } }),
  ];
  for (const text of broken) {
    assert.deepEqual(logic.stateFromStorage(text), fresh, String(text));
  }
});

test('storageKey depends on the salt, so two games never share progress', () => {
  assert.notEqual(logic.storageKey('one'), logic.storageKey('two'));
  assert.ok(logic.storageKey('one').includes('one'));
});

test('fillText replaces each named field and leaves an unknown field as it is', () => {
  assert.equal(logic.fillText('{points} of {max} points', { points: 50, max: 75 }), '50 of 75 points');
  assert.equal(logic.fillText('Open {envelope}', {}), 'Open {envelope}');
});

test('correctOptionId finds the option whose hash matches, and null for an unknown question', () => {
  assert.equal(logic.correctOptionId(sampleData(), 'who'), 'felix');
  assert.equal(logic.correctOptionId(sampleData(), 'why'), 'debt');
  assert.equal(logic.correctOptionId(sampleData(), 'when'), null);
  assert.equal(logic.correctOptionId({ ...sampleData(), deduction: null }, 'who'), null);
});

test('correctOptionId gives null when no option matches the stored hash', () => {
  const data = sampleData();
  const broken = { questions: data.deduction ? [{ ...data.deduction.questions[0], correct_hash: 'x' }] : [] };
  assert.equal(logic.correctOptionId({ ...data, deduction: /** @type {any} */ (broken) }, 'who'), null);
});
