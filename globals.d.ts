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
