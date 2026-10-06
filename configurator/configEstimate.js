// @ts-check
// The game size estimate that the configurator shows before the user saves a config. This is the JavaScript copy of
// estimate_game_size() in toolkit/src/mystery_forge/brief.py; contracts/estimate-vectors.json keeps both copies equal.
// The formula uses decimal factors (1.4, 1.25, 0.6, 0.1). Binary floats round them (6 x 1.4 x 1.25 gives 10.4999...),
// so both copies compute in exact integers: minutes in hundredths and the speedup in tenths.

(function registerConfigEstimate() {
  /** @type {Record<MysteryForgeDifficulty, number>} */
  const BASE_MINUTES_PER_PUZZLE = { easy: 6, medium: 9, hard: 13, expert: 18 };
  /** @type {Record<MysteryForgeReadingLoad, number>} */
  const READING_WORDS_PER_MINUTE = { light: 60, medium: 100, heavy: 150 };

  /**
   * Integer division that rounds down. Both operands are small integers, so the float division is exact enough.
   * @param {number} numerator
   * @param {number} denominator
   * @returns {number}
   */
  function floorDiv(numerator, denominator) {
    return Math.floor(numerator / denominator);
  }

  /**
   * Estimate the puzzle count, the stages, the pages, and the generation time for a game.
   * @param {MysteryForgeEstimateInput} input
   * @returns {MysteryForgeEstimate}
   */
  function estimate(input) {
    const width = Math.min(4, Math.max(1, Math.ceil(input.players / 2)));
    const speedupTenths = 10 + 6 * (width - 1);
    const kidsPercent = input.audience === 'kids' ? 140 : 100;
    const soloPercent = input.players === 1 ? 125 : 100;
    const minutesPerPuzzleHundredths = floorDiv(
      BASE_MINUTES_PER_PUZZLE[input.difficulty] * kidsPercent * soloPercent,
      100,
    );
    const overhead = 5 + floorDiv(input.duration_minutes, 10) + (input.format !== 'envelopes' ? 10 : 0);
    const available = Math.max(10, input.duration_minutes - overhead);
    const puzzleCount = Math.min(24, Math.max(3, floorDiv(available * speedupTenths * 10, minutesPerPuzzleHundredths)));
    const stageCount = Math.min(6, Math.max(2, Math.ceil(puzzleCount / (width + 1))));
    const best = input.quality === 'best';
    return {
      puzzle_count: puzzleCount,
      stage_count: stageCount,
      parallel_width: width,
      solver_count: best ? 5 : 3,
      reading_words: input.duration_minutes * READING_WORDS_PER_MINUTE[input.reading_load],
      printed_pages: 4 + stageCount + puzzleCount + Math.ceil(puzzleCount / 2),
      generation_minutes: 20 + puzzleCount * (best ? 6 : 3) + stageCount * (best ? 8 : 4),
      minutes_per_puzzle: floorDiv(minutesPerPuzzleHundredths + 50, 100),
    };
  }

  /**
   * Estimate from a config after applyDefaults, the way derive_brief() in the toolkit does.
   * @param {MysteryForgeEstimateConfig} config
   * @returns {MysteryForgeEstimate}
   */
  function estimateFromConfig(config) {
    return estimate({
      players: config.players.count,
      duration_minutes: config.duration_minutes,
      difficulty: config.difficulty,
      audience: config.audience,
      format: config.format,
      quality: config.generation.quality,
      reading_load: config.content.reading_load,
    });
  }

  globalThis.MysteryForgeConfigEstimate = { estimate, estimateFromConfig };
})();
