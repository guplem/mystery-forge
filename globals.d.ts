// Global namespaces that the classic browser scripts register. Classic scripts cannot use ES modules on file:// pages,
// so each file attaches its public functions to one global object, and the tests read them from there.

interface MysteryForgeAnswersApi {
  normalizeAnswer(text: string, language: string): string;
  answerHash(normalizedAnswer: string, salt: string): string;
  sha256Hex(text: string): string;
}

declare var MysteryForgeAnswers: MysteryForgeAnswersApi;

/** The JSON Schema subset of contracts/game-config.schema.json. A test fails when the schema uses another keyword. */
interface MysteryForgeJsonSchema {
  $schema?: string;
  title?: string;
  description?: string;
  type?: string;
  enum?: unknown[];
  minimum?: number;
  maximum?: number;
  maxLength?: number;
  maxItems?: number;
  items?: MysteryForgeJsonSchema;
  properties?: Record<string, MysteryForgeJsonSchema>;
  required?: string[];
  additionalProperties?: boolean;
  default?: unknown;
}

/** One problem in a config. `path` is dotted ("players.names.2"); the empty path is the whole config. */
interface MysteryForgeConfigFinding {
  path: string;
  keyword: string;
  message: string;
}

interface MysteryForgeConfigValidatorApi {
  validateConfig(schema: MysteryForgeJsonSchema, value: unknown): MysteryForgeConfigFinding[];
  applyDefaults(schema: MysteryForgeJsonSchema, value: unknown): unknown;
  listUnsupportedKeywords(schema: object): string[];
}

declare var MysteryForgeConfigValidator: MysteryForgeConfigValidatorApi;

/** Set by configurator/gameConfigSchema.js, which `npm run generate:schema` writes from the contract. */
declare var MysteryForgeGameConfigSchema: MysteryForgeJsonSchema;

type MysteryForgeDifficulty = 'easy' | 'medium' | 'hard' | 'expert';
type MysteryForgeReadingLoad = 'light' | 'medium' | 'heavy';

interface MysteryForgeEstimateInput {
  players: number;
  duration_minutes: number;
  difficulty: MysteryForgeDifficulty;
  audience: string;
  format: string;
  quality: string;
  reading_load: MysteryForgeReadingLoad;
}

interface MysteryForgeEstimate {
  puzzle_count: number;
  stage_count: number;
  parallel_width: number;
  solver_count: number;
  reading_words: number;
  printed_pages: number;
  generation_minutes: number;
  minutes_per_puzzle: number;
}

/** The fields of a config, after applyDefaults, that the estimate reads. */
interface MysteryForgeEstimateConfig {
  players: { count: number };
  duration_minutes: number;
  difficulty: MysteryForgeDifficulty;
  audience: string;
  format: string;
  generation: { quality: string };
  content: { reading_load: MysteryForgeReadingLoad };
}

interface MysteryForgeConfigEstimateApi {
  estimate(input: MysteryForgeEstimateInput): MysteryForgeEstimate;
  estimateFromConfig(config: MysteryForgeEstimateConfig): MysteryForgeEstimate;
}

declare var MysteryForgeConfigEstimate: MysteryForgeConfigEstimateApi;

/** The languages of the configurator page itself (not of the game). */
type MysteryForgeUiLanguage = 'en' | 'es' | 'ca';

interface MysteryForgeUiTextApi {
  UI_LANGUAGES: readonly MysteryForgeUiLanguage[];
  TEXTS: Record<MysteryForgeUiLanguage, Record<string, string>>;
  translate(language: string, key: string, params?: Record<string, string | number>): string;
  pickUiLanguage(browserLanguages: readonly string[]): MysteryForgeUiLanguage;
  requiredSchemaTextKeys(schema: MysteryForgeJsonSchema): string[];
}

declare var MysteryForgeUiText: MysteryForgeUiTextApi;

/** A complete config, after applyDefaults. The schema lists the allowed values of each string. */
interface MysteryForgeGameConfig {
  schema_version: number;
  audience: string;
  format: string;
  players: { count: number; names: string[] };
  host: string;
  duration_minutes: number;
  difficulty: MysteryForgeDifficulty;
  language: string;
  theme: { idea: string; tone: string; era: string };
  content: { death_allowed: boolean; scary_level: string; reading_load: MysteryForgeReadingLoad };
  personalization: { host_name: string; place: string; inside_jokes: string[]; dedication: string };
  puzzle_preferences: Record<string, string>;
  equipment: {
    printer: string;
    ink_saving: boolean;
    paper: string;
    scissors: boolean;
    tape_or_glue: boolean;
    envelopes: boolean;
  };
  assistance: { hints: boolean; paper_answer_check: boolean; companion_page: boolean };
  visuals: { style: string; images: string; readable_font: boolean };
  generation: { quality: string; pick_concept: string; seed: number };
  output: { folder: string };
}

type MysteryForgeFieldWidget =
  'cards' | 'segmented' | 'select' | 'stepper' | 'range' | 'number' | 'toggle' | 'text' | 'textarea' | 'list';

interface MysteryForgeFieldOption {
  value: string;
  label: string;
  help: string;
}

/** One form field: the schema node of `path` plus its texts in the page language. A limit that the schema lacks is 0. */
interface MysteryForgeFormField {
  path: string;
  widget: MysteryForgeFieldWidget;
  label: string;
  help: string;
  placeholder: string;
  options: MysteryForgeFieldOption[];
  minimum: number;
  maximum: number;
  step: number;
  maxLength: number;
  maxItems: number;
  advanced: boolean;
}

interface MysteryForgeFormSection {
  id: string;
  title: string;
  intro: string;
  collapsed: boolean;
  fields: MysteryForgeFormField[];
}

/** A combination of choices that works badly. The text is `warning.<id>` in uiText, filled from `params`. */
interface MysteryForgeConfigWarning {
  id: string;
  severity: 'warning' | 'info';
  path: string;
  params: Record<string, string | number>;
}

interface MysteryForgeEstimateItem {
  id: string;
  label: string;
  value: string;
}

/** The part of the Web Storage API that the draft helpers use, so that the tests can pass a fake. */
interface MysteryForgeDraftStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

interface MysteryForgeDraft {
  config: MysteryForgeGameConfig;
  uiLanguage: MysteryForgeUiLanguage;
}

interface MysteryForgeParsedConfig {
  config: MysteryForgeGameConfig | null;
  errors: MysteryForgeConfigFinding[];
}

interface MysteryForgeConfigFormApi {
  SECTIONS: readonly { id: string; collapsed: boolean; fields: readonly string[] }[];
  AUDIENCE_PRESETS: Readonly<Record<string, Readonly<Record<string, unknown>>>>;
  buildFormModel(language: string): MysteryForgeFormSection[];
  initialConfig(browserLanguages: readonly string[]): MysteryForgeGameConfig;
  followPageLanguage(
    config: MysteryForgeGameConfig,
    oldUiLanguage: string,
    newUiLanguage: string,
    browserLanguages: readonly string[],
  ): { config: MysteryForgeGameConfig; followed: boolean };
  getAtPath(config: MysteryForgeGameConfig, path: string): unknown;
  setFieldValue(config: MysteryForgeGameConfig, path: string, rawValue: unknown): MysteryForgeGameConfig;
  addListItem(config: MysteryForgeGameConfig, path: string, text: string): MysteryForgeGameConfig;
  removeListItem(config: MysteryForgeGameConfig, path: string, index: number): MysteryForgeGameConfig;
  isListFull(config: MysteryForgeGameConfig, path: string): boolean;
  textLength(config: MysteryForgeGameConfig, path: string): number;
  applyAudiencePreset(config: MysteryForgeGameConfig, audience: string): MysteryForgeGameConfig;
  applyFieldChange(
    config: MysteryForgeGameConfig,
    path: string,
    rawValue: unknown,
  ): { config: MysteryForgeGameConfig; presetApplied: boolean };
  configWarnings(config: MysteryForgeGameConfig): MysteryForgeConfigWarning[];
  showsSurpriseNote(config: MysteryForgeGameConfig): boolean;
  formatMinutes(minutes: number): string;
  estimateItems(config: MysteryForgeGameConfig, language: string): MysteryForgeEstimateItem[];
  summaryBarText(config: MysteryForgeGameConfig, language: string): string;
  generationTimeText(config: MysteryForgeGameConfig, language: string): string;
  configFileName(config: MysteryForgeGameConfig, today?: Date): string;
  configFileText(config: MysteryForgeGameConfig): string;
  buildPrompt(config: MysteryForgeGameConfig, language: string, today?: Date): string;
  parseConfigFile(text: string): MysteryForgeParsedConfig;
  describeFinding(finding: MysteryForgeConfigFinding, language: string): string;
  saveDraft(storage: MysteryForgeDraftStorage, draft: MysteryForgeDraft): boolean;
  loadDraft(storage: MysteryForgeDraftStorage): MysteryForgeDraft | null;
  clearDraft(storage: MysteryForgeDraftStorage): void;
}

declare var MysteryForgeConfigForm: MysteryForgeConfigFormApi;

/** One envelope of the companion page data (toolkit/src/mystery_forge/render/companion_data.py). */
interface MysteryForgeCompanionStage {
  id: string;
  label: string;
  envelope: string;
  /** "start", or the code of the puzzle whose answer opens this envelope. */
  opens_with: string;
  opening_text: string;
}

interface MysteryForgeCompanionPuzzle {
  code: string;
  title: string;
  stage: string;
  answer_format: string;
  answer_hashes: string[];
  near_misses: { hash: string; message: string }[];
  /** The stage that this puzzle's answer opens, or null. */
  unlocks: string | null;
  hints: { level: number; text: string }[];
  solution: { steps: string[]; answer: string };
  /** The story payoff that the page shows on a correct answer; empty when the puzzle has none. */
  reveal_text: string;
}

interface MysteryForgeCompanionQuestion {
  id: string;
  prompt: string;
  options: { id: string; text: string }[];
  /** answerHash(`<question id>:<correct option id>`, salt). */
  correct_hash: string;
  points: number;
}

interface MysteryForgeCompanionEpilogue {
  min_score_percent: number;
  title: string;
  text: string;
}

interface MysteryForgeCompanionData {
  format_version: number;
  title: string;
  tagline: string;
  intro: string;
  language: string;
  salt: string;
  duration_minutes: number;
  panel_verified: boolean;
  final_puzzle: string | null;
  ui: Record<string, string>;
  stages: MysteryForgeCompanionStage[];
  puzzles: MysteryForgeCompanionPuzzle[];
  deduction: { questions: MysteryForgeCompanionQuestion[] } | null;
  /** Sorted from the highest min_score_percent down. */
  epilogues: MysteryForgeCompanionEpilogue[];
  reveal: string[];
}

interface MysteryForgeCompanionTimer {
  elapsedMs: number;
  /** The epoch time in ms of the last start, or null while the timer is paused. */
  startedAt: number | null;
}

/** What the companion page keeps in localStorage. */
interface MysteryForgeCompanionState {
  version: number;
  solved: string[];
  /** Per puzzle code: how many hint steps the group opened. The step after the last hint is the answer. */
  hintSteps: Record<string, number>;
  timer: MysteryForgeCompanionTimer;
  /** The locked-in accusation: option id per question id, or null before the group locks it in. */
  accusation: Record<string, string> | null;
}

interface MysteryForgeAnswerCheck {
  result: 'correct' | 'near' | 'wrong';
  message?: string;
  unlocksStage?: string;
  revealText?: string;
}

interface MysteryForgeAccusationScore {
  points: number;
  maxPoints: number;
  percent: number;
  epilogue: MysteryForgeCompanionEpilogue | null;
  correctQuestions: string[];
}

interface MysteryForgeCompanionLogicApi {
  freshState(): MysteryForgeCompanionState;
  storageKey(salt: string): string;
  checkAnswer(data: MysteryForgeCompanionData, puzzleCode: string, input: string): MysteryForgeAnswerCheck;
  unlockedStages(data: MysteryForgeCompanionData, solvedCodes: string[]): string[];
  visiblePuzzles(data: MysteryForgeCompanionData, unlockedStageIds: string[]): MysteryForgeCompanionPuzzle[];
  isGameFinished(data: MysteryForgeCompanionData, solvedCodes: string[]): boolean;
  epilogueForPercent(data: MysteryForgeCompanionData, percent: number): MysteryForgeCompanionEpilogue | null;
  isAccusationComplete(data: MysteryForgeCompanionData, choices: Record<string, string>): boolean;
  scoreAccusation(data: MysteryForgeCompanionData, choices: Record<string, string>): MysteryForgeAccusationScore;
  correctOptionId(data: MysteryForgeCompanionData, questionId: string): string | null;
  formatTimer(seconds: number): string;
  timerElapsedMs(timer: MysteryForgeCompanionTimer, nowMs: number): number;
  startTimer(state: MysteryForgeCompanionState, nowMs: number): MysteryForgeCompanionState;
  pauseTimer(state: MysteryForgeCompanionState, nowMs: number): MysteryForgeCompanionState;
  timerDisplay(
    data: MysteryForgeCompanionData,
    timer: MysteryForgeCompanionTimer,
    nowMs: number,
  ): { text: string; overtime: boolean };
  withSolved(state: MysteryForgeCompanionState, code: string): MysteryForgeCompanionState;
  nextHintLevel(data: MysteryForgeCompanionData, state: MysteryForgeCompanionState, code: string): number | null;
  revealedHintCount(data: MysteryForgeCompanionData, state: MysteryForgeCompanionState, code: string): number;
  isAnswerShown(data: MysteryForgeCompanionData, state: MysteryForgeCompanionState, code: string): boolean;
  withHintStep(
    data: MysteryForgeCompanionData,
    state: MysteryForgeCompanionState,
    code: string,
  ): MysteryForgeCompanionState;
  withAccusation(state: MysteryForgeCompanionState, choices: Record<string, string>): MysteryForgeCompanionState;
  stateFromStorage(text: string | null): MysteryForgeCompanionState;
  stateToStorage(state: MysteryForgeCompanionState): string;
  fillText(template: string, values: Record<string, string | number>): string;
  isLongIntro(intro: string): boolean;
}

declare var MysteryForgeCompanionLogic: MysteryForgeCompanionLogicApi;
