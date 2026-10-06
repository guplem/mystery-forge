// @ts-check
// Every text that the configurator page shows, in English and in Spanish (Spain). Keys that start with "field." and
// "enum." follow the property paths and the enum values of contracts/game-config.schema.json, and a test fails when
// one of them is missing in a language. Placeholders such as {fileName} are filled by translate().

(function registerUiText() {
  /** @type {readonly MysteryForgeUiLanguage[]} */
  const UI_LANGUAGES = ['en', 'es'];

  /**
   * The like / neutral / avoid texts of one puzzle category. All six categories share the same three choices.
   * @param {string} category
   * @param {[string, string, string, string, string, string]} texts
   * @returns {Record<string, string>}
   */
  function preferenceChoices(category, texts) {
    const prefix = `enum.puzzle_preferences.${category}`;
    return {
      [`${prefix}.like.label`]: texts[0],
      [`${prefix}.like.help`]: texts[1],
      [`${prefix}.neutral.label`]: texts[2],
      [`${prefix}.neutral.help`]: texts[3],
      [`${prefix}.avoid.label`]: texts[4],
      [`${prefix}.avoid.help`]: texts[5],
    };
  }

  /** @type {[string, string, string, string, string, string]} */
  const ENGLISH_PREFERENCE = [
    'Love it',
    'Use more of this kind.',
    'Fine',
    'Use a normal amount.',
    'Skip',
    'Leave this kind out.',
  ];
  /** @type {[string, string, string, string, string, string]} */
  const SPANISH_PREFERENCE = [
    'Me encanta',
    'Más de este tipo.',
    'Normal',
    'Una cantidad normal.',
    'Mejor no',
    'Sin este tipo.',
  ];

  /** @type {Record<string, string>} */
  const en = {
    'page.title': 'Mystery Forge',
    'page.tagline':
      'Design a printable mystery game for your table. Your AI agent writes it, you print it, and everyone plays.',
    'page.ui_language': 'Page language',
    'page.kicker': 'Case file No. 001',
    'summary.stamp': 'Confidential',
    'page.offline': 'This page works offline. Your choices stay on this computer.',
    'how.title': 'How it works',
    'how.step1.title': 'Configure',
    'how.step1.text': 'Choose who plays and what they enjoy. It takes about five minutes.',
    'how.step2.title': 'Generate with your AI agent',
    'how.step2.text': 'The agent writes the story and checks every puzzle.',
    'how.step3.title': 'Print and play',
    'how.step3.text': 'Print the pages, fill the envelopes, and open the case.',

    'section.players.title': 'Who is playing',
    'section.players.intro': 'Pick a group and we fill in sensible choices. You can change any of them later.',
    'section.game.title': 'The game',
    'section.game.intro': 'How the game feels, how long it lasts, and how hard it is.',
    'section.story.title': 'The story',
    'section.story.intro': 'Give the agent an idea, or let it surprise you.',
    'section.personal.title': 'Make it personal',
    'section.personal.intro': 'Optional touches that turn a good game into your game.',
    'section.puzzles.title': 'Puzzles you like',
    'section.puzzles.intro': 'Tell the agent which kinds of puzzles to use more, and which to skip.',
    'section.printing.title': 'Printing',
    'section.printing.intro': 'What you have at home to print and build the game.',
    'section.look.title': 'Look',
    'section.look.intro': 'The style of the printed pages.',
    'section.help.title': 'Help during the game',
    'section.help.intro': 'Ways for the players to get unstuck without spoilers.',
    'section.generation.title': 'Generation',
    'section.generation.intro': 'How the agent works while it builds your game.',
    'section.advanced.title': 'Advanced',

    'form.optional': 'Optional',
    'form.decrease': 'Fewer',
    'form.increase': 'More',
    'form.add': 'Add',
    'form.remove': 'Remove {item}',
    'form.list_full': 'The list is full: {max} at most.',
    'form.list_count': '{count} of {max}',
    'form.surprise': 'Leave it empty and the agent invents a surprise story for you.',

    'field.players.names.placeholder': 'Type a name and press Enter',
    'field.theme.idea.placeholder':
      'For example: a stolen painting at a seaside hotel, a missing cake at grandma’s birthday, or a ghost in the school library.',
    'field.personalization.host_name.placeholder': 'For example: Aunt Laura',
    'field.personalization.place.placeholder': 'For example: our cabin by the lake',
    'field.personalization.inside_jokes.placeholder': 'For example: the cat who hates Mondays',
    'field.personalization.dedication.placeholder': 'For example: Happy 40th birthday, Sam!',
    'field.output.folder.placeholder': 'Empty means your Desktop',

    'summary.title': 'Your game',
    'summary.note': 'Estimates. The agent adjusts them to the story.',
    'estimate.puzzles': 'Puzzles',
    'estimate.envelopes': 'Envelopes',
    'estimate.chapters': 'Chapters',
    'estimate.pages': 'Printed pages',
    'estimate.play_time': 'Play time',
    'estimate.generation': 'Generation time',
    'estimate.about': 'about {time}',
    'warnings.title': 'Worth a look',
    'warnings.none': 'Everything fits together.',
    'warnings.show': 'Show me',

    'warning.kids_death':
      'The game is for kids, but a death is allowed in the story. Turn off "A death in the story" for a gentler plot.',
    'warning.kids_spooky':
      'The game is for kids, but the scary level is "Spooky". "None" or "A little" suits kids better.',
    'warning.solo_game_master':
      'One player with a game master means nobody else plays. Choose "The game runs itself" or "The host plays too".',
    'warning.colors_go_gray': 'The "Kids" style uses bright colors. On a black and white printer they turn gray.',
    'warning.crafts_without_scissors': 'You like craft puzzles, but scissors are off. Most craft puzzles need cutting.',
    'warning.no_scissors': 'Without scissors the agent has fewer kinds of puzzles to choose from.',
    'warning.short_expert':
      'Expert puzzles in a very short game leave room for only a few puzzles. Try a longer game or an easier level.',
    'warning.many_players_no_game_master':
      'More than 8 players is a big group. A game master helps to keep everyone on track.',
    'warning.envelopes_without_envelopes':
      'The game uses envelopes, but you have none. You can fold paper and close it with a sticker.',
    'warning.no_help': 'There are no hints and no answer checks. Players who get stuck cannot get help.',
    'warning.all_puzzles_avoided':
      'You skip every kind of puzzle. The agent then uses its own choice. Mark at least one kind as "Fine".',
    'warning.more_names_than_players': 'You gave more names than players. The agent uses the first {count} names.',

    'action.download': 'Download config',
    'action.load': 'Load config',
    'action.copy_prompt': 'Copy prompt',
    'action.reset': 'Reset',
    'action.undo': 'Undo',
    'action.show_summary': 'Review and save',
    'load.hint': 'You can also drop a .mystery-config.json file anywhere on the page.',
    'drop.title': 'Drop your config file here',

    'status.downloaded': 'Saved {fileName}. Look in your Downloads folder.',
    'status.copied': 'Prompt copied. Paste it into your agent.',
    'status.copy_failed': 'Copy did not work here. Select the text in the box below and copy it.',
    'status.loaded': 'Loaded {fileName}.',
    'status.load_failed': '{fileName} is not a valid Mystery Forge config. Nothing changed.',
    'status.reset': 'All choices are back to the start.',
    'status.draft_restored': 'Your last draft is back.',
    'status.preset_applied': 'Set up for {audience}. You can change any choice below.',

    'error.json': 'The file is not valid JSON text.',
    'error.whole_file': 'The file',
    'error.required': '{field}: this value is missing.',
    'error.additionalProperties': '{field}: this setting is unknown.',
    'error.type': '{field}: the value has the wrong type.',
    'error.enum': '{field}: this choice is not allowed.',
    'error.minimum': '{field}: the value must be {limit} or more.',
    'error.maximum': '{field}: the value must be {limit} or less.',
    'error.maxLength': '{field}: the text must have {limit} characters or fewer.',
    'error.maxItems': '{field}: the list must have {limit} items or fewer.',

    'prompt.title': 'Prompt for your agent',
    'prompt.help': 'Select this text and paste it into Claude Code.',
    'prompt.intro': 'Create a printable mystery game with Mystery Forge.',
    'prompt.run_skill':
      'Run the create-game skill with the config below. Treat it as the config file {fileName}. Do not change it.',
    'prompt.questions': 'Ask me only the questions that the skill asks.',

    'next.title': 'Next steps',
    'next.step1': 'Install uv (a tool that runs Python programs) and Claude Code. You do this only once.',
    'next.step2': 'Open Claude Code in the generator folder of Mystery Forge.',
    'next.step3': 'Paste the prompt, or say: create a game with {fileName}',
    'next.note':
      'The run takes {time}. Stay for the first questions. Once you pick the story concept, you can walk away.',

    'field.schema_version.label': 'Config version',
    'field.schema_version.help': 'The version of the config format. The page sets it for you.',
    'enum.schema_version.1.label': 'Version 1',
    'enum.schema_version.1.help': 'The current config format.',

    'field.audience.label': 'Group',
    'field.audience.help': 'Who sits at the table. The group sets the difficulty, the reading load, and the mood.',
    'enum.audience.kids.label': 'Kids',
    'enum.audience.kids.help': 'Ages 7 to 11. Short texts, gentle story, big letters.',
    'enum.audience.family.label': 'Family',
    'enum.audience.family.help': 'Kids and grown-ups together. Fun for every age.',
    'enum.audience.teens.label': 'Teens',
    'enum.audience.teens.help': 'Ages 12 to 17. More mystery and a bit more challenge.',
    'enum.audience.adults.label': 'Adults',
    'enum.audience.adults.help': 'A dinner party or a game night. Darker plots allowed.',
    'enum.audience.puzzle_fans.label': 'Puzzle fans',
    'enum.audience.puzzle_fans.help': 'People who love escape rooms. Hard puzzles, less story.',

    'field.format.label': 'Format',
    'field.format.help': 'How the players move through the game.',
    'enum.format.envelopes.label': 'Open envelopes one by one',
    'enum.format.envelopes.help': 'Each solved puzzle tells you which envelope to open next.',
    'enum.format.case_file.label': 'Read a case file and accuse a suspect',
    'enum.format.case_file.help': 'Study the clues, find the culprit, and prove it.',
    'enum.format.both.label': 'Both (recommended)',
    'enum.format.both.help': 'Envelopes reveal the case file step by step. The richest experience.',

    'field.players.label': 'Players',
    'field.players.help': 'The people who play.',
    'field.players.count.label': 'Number of players',
    'field.players.count.help': 'From 1 to 12. More players means more puzzles at the same time.',
    'field.players.names.label': 'Player names',
    'field.players.names.help': 'The agent can put the names on character cards and in the story.',

    'field.host.label': 'Who runs the game',
    'field.host.help': 'The host is the person who prints and prepares the game.',
    'enum.host.self_running.label': 'The game runs itself',
    'enum.host.self_running.help': 'Everyone plays. The pages tell you what to do next.',
    'enum.host.host_plays.label': 'The host plays too',
    'enum.host.host_plays.help': 'The host sets up the table and then plays like everyone else.',
    'enum.host.game_master.label': 'A game master leads',
    'enum.host.game_master.help': 'The host knows the solution, reads the story aloud, and gives hints.',

    'field.duration_minutes.label': 'Play time',
    'field.duration_minutes.help': 'How long the game lasts at the table, from 30 minutes to 4 hours.',

    'field.difficulty.label': 'Difficulty',
    'field.difficulty.help': 'How hard the puzzles are.',
    'enum.difficulty.easy.label': 'Easy',
    'enum.difficulty.easy.help': 'Clear clues. Good for first-time players.',
    'enum.difficulty.medium.label': 'Medium',
    'enum.difficulty.medium.help': 'Some thinking needed. Good for most groups.',
    'enum.difficulty.hard.label': 'Hard',
    'enum.difficulty.hard.help': 'Clues hide well. For groups that play often.',
    'enum.difficulty.expert.label': 'Expert',
    'enum.difficulty.expert.help': 'Few clues and many steps. For real puzzle lovers.',

    'field.language.label': 'Language of the game',
    'field.language.help': 'The language of every printed page.',
    'enum.language.en.label': 'English',
    'enum.language.en.help': 'All pages in English.',
    'enum.language.es.label': 'Spanish',
    'enum.language.es.help': 'All pages in Spanish.',
    'enum.language.ca.label': 'Catalan',
    'enum.language.ca.help': 'All pages in Catalan.',
    'enum.language.fr.label': 'French',
    'enum.language.fr.help': 'All pages in French.',
    'enum.language.de.label': 'German',
    'enum.language.de.help': 'All pages in German.',
    'enum.language.it.label': 'Italian',
    'enum.language.it.help': 'All pages in Italian.',
    'enum.language.pt.label': 'Portuguese',
    'enum.language.pt.help': 'All pages in Portuguese.',

    'field.theme.label': 'Story',
    'field.theme.help': 'The story idea and its mood.',
    'field.theme.idea.label': 'Story idea',
    'field.theme.idea.help': 'A few words or a few lines. Places, characters, and a crime all help.',
    'field.theme.tone.label': 'Mood',
    'field.theme.tone.help': 'How the story feels.',
    'enum.theme.tone.surprise.label': 'Surprise me',
    'enum.theme.tone.surprise.help': 'The agent picks the mood that fits the idea.',
    'enum.theme.tone.cozy.label': 'Cozy',
    'enum.theme.tone.cozy.help': 'Warm and light, like a village mystery.',
    'enum.theme.tone.adventure.label': 'Adventure',
    'enum.theme.tone.adventure.help': 'Maps, treasure, and a race against time.',
    'enum.theme.tone.noir.label': 'Noir',
    'enum.theme.tone.noir.help': 'Rainy streets, secrets, and a tired detective.',
    'enum.theme.tone.spooky.label': 'Spooky',
    'enum.theme.tone.spooky.help': 'Creaky doors and strange shadows.',
    'enum.theme.tone.comedic.label': 'Funny',
    'enum.theme.tone.comedic.help': 'Silly suspects and plenty of jokes.',
    'enum.theme.tone.dramatic.label': 'Dramatic',
    'enum.theme.tone.dramatic.help': 'High stakes, betrayal, and big reveals.',
    'field.theme.era.label': 'Time period',
    'field.theme.era.help': 'When the story happens.',
    'enum.theme.era.any.label': 'Any',
    'enum.theme.era.any.help': 'The agent picks the time that fits the idea.',
    'enum.theme.era.historical.label': 'The past',
    'enum.theme.era.historical.help': 'Castles, steam trains, or the roaring twenties.',
    'enum.theme.era.modern.label': 'Today',
    'enum.theme.era.modern.help': 'Phones, offices, and modern cities.',
    'enum.theme.era.future.label': 'The future',
    'enum.theme.era.future.help': 'Space stations, robots, and new technology.',
    'enum.theme.era.fantasy.label': 'Fantasy',
    'enum.theme.era.fantasy.help': 'Magic, dragons, and invented worlds.',

    'field.content.label': 'Content',
    'field.content.help': 'Limits on what the story may contain.',
    'field.content.death_allowed.label': 'A death in the story',
    'field.content.death_allowed.help': 'On allows a classic murder mystery. Off keeps the crime to theft or a puzzle.',
    'field.content.scary_level.label': 'Scary level',
    'field.content.scary_level.help': 'How scary the story may get.',
    'enum.content.scary_level.none.label': 'None',
    'enum.content.scary_level.none.help': 'Nothing scary at all.',
    'enum.content.scary_level.mild.label': 'A little',
    'enum.content.scary_level.mild.help': 'A shiver here and there.',
    'enum.content.scary_level.spooky.label': 'Spooky',
    'enum.content.scary_level.spooky.help': 'A proper ghost story mood.',
    'field.content.reading_load.label': 'Reading',
    'field.content.reading_load.help': 'How much text the players read.',
    'enum.content.reading_load.light.label': 'Light',
    'enum.content.reading_load.light.help': 'Short texts. Good for kids and big groups.',
    'enum.content.reading_load.medium.label': 'Medium',
    'enum.content.reading_load.medium.help': 'Letters and notes of a page or so.',
    'enum.content.reading_load.heavy.label': 'Rich',
    'enum.content.reading_load.heavy.help': 'Diaries, reports, and long letters full of clues.',

    'field.personalization.label': 'Personal touches',
    'field.personalization.help': 'Personal touches that the story includes.',
    'field.personalization.host_name.label': 'Host name',
    'field.personalization.host_name.help': 'The story can mention the host by name.',
    'field.personalization.place.label': 'Place',
    'field.personalization.place.help': 'Where you play. The story can happen there.',
    'field.personalization.inside_jokes.label': 'Inside jokes',
    'field.personalization.inside_jokes.help': 'Short jokes or references that your group knows. Up to 5.',
    'field.personalization.dedication.label': 'Dedication',
    'field.personalization.dedication.help': 'A line for the cover, for example for a birthday.',

    'field.puzzle_preferences.label': 'Puzzle kinds',
    'field.puzzle_preferences.help': 'How much the players like each kind of puzzle.',
    'field.puzzle_preferences.words.label': 'Words',
    'field.puzzle_preferences.words.help': 'Anagrams, ciphers, and hidden messages.',
    'field.puzzle_preferences.numbers.label': 'Numbers',
    'field.puzzle_preferences.numbers.help': 'Lock codes, sums, and dates.',
    'field.puzzle_preferences.logic.label': 'Logic',
    'field.puzzle_preferences.logic.help': 'Grids of clues: who sat where, who owns what.',
    'field.puzzle_preferences.visual.label': 'Visual',
    'field.puzzle_preferences.visual.help': 'Hidden details in pictures, maps, and symbols.',
    'field.puzzle_preferences.crafts.label': 'Crafts',
    'field.puzzle_preferences.crafts.help': 'Fold, cut, and hold pages up to the light.',
    'field.puzzle_preferences.deduction.label': 'Deduction',
    'field.puzzle_preferences.deduction.help': 'Find who lies, compare alibis, spot the gap.',
    ...preferenceChoices('words', ENGLISH_PREFERENCE),
    ...preferenceChoices('numbers', ENGLISH_PREFERENCE),
    ...preferenceChoices('logic', ENGLISH_PREFERENCE),
    ...preferenceChoices('visual', ENGLISH_PREFERENCE),
    ...preferenceChoices('crafts', ENGLISH_PREFERENCE),
    ...preferenceChoices('deduction', ENGLISH_PREFERENCE),

    'field.equipment.label': 'Equipment',
    'field.equipment.help': 'What you have to print and build the game.',
    'field.equipment.printer.label': 'Printer',
    'field.equipment.printer.help': 'The agent picks colors that print well on it.',
    'enum.equipment.printer.color.label': 'Color',
    'enum.equipment.printer.color.help': 'Full color pages.',
    'enum.equipment.printer.black_and_white.label': 'Black and white',
    'enum.equipment.printer.black_and_white.help': 'The pages use only black and shades of gray.',
    'field.equipment.ink_saving.label': 'Save ink',
    'field.equipment.ink_saving.help': 'Light backgrounds that use less ink.',
    'field.equipment.paper.label': 'Paper size',
    'field.equipment.paper.help': 'The paper in your printer.',
    'enum.equipment.paper.A4.label': 'A4',
    'enum.equipment.paper.A4.help': 'The usual size in Europe and most of the world.',
    'enum.equipment.paper.Letter.label': 'Letter',
    'enum.equipment.paper.Letter.help': 'The usual size in the United States and Canada.',
    'field.equipment.scissors.label': 'Scissors',
    'field.equipment.scissors.help': 'Players may cut paper.',
    'field.equipment.tape_or_glue.label': 'Tape or glue',
    'field.equipment.tape_or_glue.help': 'Players may stick pieces together.',
    'field.equipment.envelopes.label': 'Envelopes',
    'field.equipment.envelopes.help': 'You have envelopes to hide the next parts of the game.',

    'field.assistance.label': 'Assistance',
    'field.assistance.help': 'Help for the players during the game.',
    'field.assistance.hints.label': 'Hints',
    'field.assistance.hints.help': 'Small nudges for each puzzle, one at a time.',
    'field.assistance.paper_answer_check.label': 'Paper answer check',
    'field.assistance.paper_answer_check.help': 'A printed page where players check an answer without a device.',
    'field.assistance.companion_page.label': 'Companion page',
    'field.assistance.companion_page.help': 'A page for a phone or a computer that checks answers and gives hints.',

    'field.visuals.label': 'Look',
    'field.visuals.help': 'The look of the printed pages.',
    'field.visuals.style.label': 'Style',
    'field.visuals.style.help': 'The colors, fonts, and decorations of the pages.',
    'enum.visuals.style.auto.label': 'Auto',
    'enum.visuals.style.auto.help': 'The agent picks the style that fits the story.',
    'enum.visuals.style.vintage.label': 'Vintage',
    'enum.visuals.style.vintage.help': 'Old paper, typewriter text, and stamps.',
    'enum.visuals.style.noir.label': 'Noir',
    'enum.visuals.style.noir.help': 'Black, white, and a touch of red.',
    'enum.visuals.style.modern.label': 'Modern',
    'enum.visuals.style.modern.help': 'Clean pages, like a police report of today.',
    'enum.visuals.style.victorian.label': 'Victorian',
    'enum.visuals.style.victorian.help': 'Ornate frames and elegant letters.',
    'enum.visuals.style.scifi.label': 'Sci-fi',
    'enum.visuals.style.scifi.help': 'Screens, grids, and glowing colors.',
    'enum.visuals.style.fantasy.label': 'Fantasy',
    'enum.visuals.style.fantasy.help': 'Parchment, runes, and old maps.',
    'enum.visuals.style.kids.label': 'Kids',
    'enum.visuals.style.kids.help': 'Bright colors and round, friendly shapes.',
    'enum.visuals.style.minimal.label': 'Minimal',
    'enum.visuals.style.minimal.help': 'Plain pages that print fast and clean.',
    'field.visuals.images.label': 'Images',
    'field.visuals.images.help': 'Drawings on the pages.',
    'enum.visuals.images.svg.label': 'Drawings',
    'enum.visuals.images.svg.help': 'Simple drawings that the agent makes for the story.',
    'enum.visuals.images.none.label': 'No images',
    'enum.visuals.images.none.help': 'Text only. Faster to make and to print.',
    'field.visuals.readable_font.label': 'Easy-to-read font',
    'field.visuals.readable_font.help': 'A large, plain font. Good for kids and for tired eyes.',

    'field.generation.label': 'Generation',
    'field.generation.help': 'How the agent works.',
    'field.generation.quality.label': 'Quality',
    'field.generation.quality.help': 'More checks make better puzzles but take longer.',
    'enum.generation.quality.fast.label': 'Fast',
    'enum.generation.quality.fast.help': 'Fewer checks. Good for a quick test.',
    'enum.generation.quality.best.label': 'Best',
    'enum.generation.quality.best.help': 'More test players check each puzzle.',
    'field.generation.pick_concept.label': 'Story concept',
    'field.generation.pick_concept.help': 'The agent first writes a few story concepts.',
    'enum.generation.pick_concept.ask.label': 'Let me choose',
    'enum.generation.pick_concept.ask.help': 'The agent shows the concepts and you pick one.',
    'enum.generation.pick_concept.agent.label': 'Agent chooses',
    'enum.generation.pick_concept.agent.help': 'The agent picks one. The story stays a surprise for you too.',
    'field.generation.seed.label': 'Seed',
    'field.generation.seed.help': 'A number that makes random choices repeatable. 0 means a new random seed.',

    'field.output.label': 'Output',
    'field.output.help': 'Where the agent saves the finished game.',
    'field.output.folder.label': 'Output folder',
    'field.output.folder.help': 'The folder for the finished game. Empty means your Desktop.',
  };

  /** @type {Record<string, string>} */
  const es = {
    'page.title': 'Mystery Forge',
    'page.tagline':
      'Diseña un juego de misterio para imprimir. Tu agente de IA lo escribe, tú lo imprimes y todos juegan.',
    'page.ui_language': 'Idioma de la página',
    'page.kicker': 'Expediente n.º 001',
    'summary.stamp': 'Confidencial',
    'page.offline': 'Esta página funciona sin conexión. Tus elecciones se quedan en este ordenador.',
    'how.title': 'Cómo funciona',
    'how.step1.title': 'Configura',
    'how.step1.text': 'Elige quién juega y qué le gusta. Se tarda unos cinco minutos.',
    'how.step2.title': 'Genera con tu agente de IA',
    'how.step2.text': 'El agente escribe la historia y comprueba cada enigma.',
    'how.step3.title': 'Imprime y juega',
    'how.step3.text': 'Imprime las páginas, llena los sobres y abre el caso.',

    'section.players.title': 'Quién juega',
    'section.players.intro': 'Elige un grupo y rellenamos opciones adecuadas. Puedes cambiar cualquiera después.',
    'section.game.title': 'El juego',
    'section.game.intro': 'Cómo se juega, cuánto dura y lo difícil que es.',
    'section.story.title': 'La historia',
    'section.story.intro': 'Dale una idea al agente o deja que te sorprenda.',
    'section.personal.title': 'Hazlo personal',
    'section.personal.intro': 'Detalles opcionales que convierten un buen juego en tu juego.',
    'section.puzzles.title': 'Enigmas que os gustan',
    'section.puzzles.intro': 'Dile al agente qué tipos de enigma usar más y cuáles evitar.',
    'section.printing.title': 'Impresión',
    'section.printing.intro': 'Lo que tienes en casa para imprimir y montar el juego.',
    'section.look.title': 'Aspecto',
    'section.look.intro': 'El estilo de las páginas impresas.',
    'section.help.title': 'Ayuda durante el juego',
    'section.help.intro': 'Formas de desatascarse sin destripar nada.',
    'section.generation.title': 'Generación',
    'section.generation.intro': 'Cómo trabaja el agente mientras crea tu juego.',
    'section.advanced.title': 'Avanzado',

    'form.optional': 'Opcional',
    'form.decrease': 'Menos',
    'form.increase': 'Más',
    'form.add': 'Añadir',
    'form.remove': 'Quitar {item}',
    'form.list_full': 'La lista está llena: {max} como máximo.',
    'form.list_count': '{count} de {max}',
    'form.surprise': 'Déjalo vacío y el agente inventará una historia sorpresa para ti.',

    'field.players.names.placeholder': 'Escribe un nombre y pulsa Intro',
    'field.theme.idea.placeholder':
      'Por ejemplo: un cuadro robado en un hotel junto al mar, la tarta desaparecida del cumpleaños de la abuela o un fantasma en la biblioteca del colegio.',
    'field.personalization.host_name.placeholder': 'Por ejemplo: la tía Laura',
    'field.personalization.place.placeholder': 'Por ejemplo: nuestra casa del pueblo',
    'field.personalization.inside_jokes.placeholder': 'Por ejemplo: el gato que odia los lunes',
    'field.personalization.dedication.placeholder': 'Por ejemplo: ¡Feliz 40 cumpleaños, Sam!',
    'field.output.folder.placeholder': 'Vacío significa tu Escritorio',

    'summary.title': 'Tu juego',
    'summary.note': 'Son estimaciones. El agente las ajusta a la historia.',
    'estimate.puzzles': 'Enigmas',
    'estimate.envelopes': 'Sobres',
    'estimate.chapters': 'Capítulos',
    'estimate.pages': 'Páginas impresas',
    'estimate.play_time': 'Tiempo de juego',
    'estimate.generation': 'Tiempo de generación',
    'estimate.about': 'unas {time}',
    'warnings.title': 'Conviene revisar',
    'warnings.none': 'Todo encaja.',
    'warnings.show': 'Ver',

    'warning.kids_death':
      'El juego es para niños, pero la historia permite una muerte. Desactiva «Una muerte en la historia» para una trama más suave.',
    'warning.kids_spooky':
      'El juego es para niños, pero el nivel de miedo es «Terror». «Nada» o «Un poco» encajan mejor con niños.',
    'warning.solo_game_master':
      'Un jugador con director de juego significa que nadie más juega. Elige «El juego se dirige solo» o «El anfitrión también juega».',
    'warning.colors_go_gray':
      'El estilo «Infantil» usa colores vivos. En una impresora en blanco y negro se ven grises.',
    'warning.crafts_without_scissors':
      'Te gustan los enigmas manuales, pero las tijeras están desactivadas. Casi todos necesitan recortar.',
    'warning.no_scissors': 'Sin tijeras, el agente tiene menos tipos de enigma entre los que elegir.',
    'warning.short_expert':
      'Enigmas de nivel experto en una partida muy corta dejan sitio para muy pocos. Prueba una partida más larga o un nivel más fácil.',
    'warning.many_players_no_game_master':
      'Más de 8 jugadores es un grupo grande. Un director de juego ayuda a que nadie se pierda.',
    'warning.envelopes_without_envelopes':
      'El juego usa sobres, pero no tienes. Puedes doblar un papel y cerrarlo con una pegatina.',
    'warning.no_help': 'No hay pistas ni comprobación de respuestas. Quien se atasque no podrá pedir ayuda.',
    'warning.all_puzzles_avoided':
      'Evitas todos los tipos de enigma. Entonces el agente elige por su cuenta. Marca al menos un tipo como «Normal».',
    'warning.more_names_than_players':
      'Has puesto más nombres que jugadores. El agente usa los {count} primeros nombres.',

    'action.download': 'Descargar configuración',
    'action.load': 'Cargar configuración',
    'action.copy_prompt': 'Copiar instrucción',
    'action.reset': 'Empezar de nuevo',
    'action.undo': 'Deshacer',
    'action.show_summary': 'Revisar y guardar',
    'load.hint': 'También puedes soltar un archivo .mystery-config.json en cualquier parte de la página.',
    'drop.title': 'Suelta aquí tu archivo de configuración',

    'status.downloaded': 'Guardado {fileName}. Búscalo en tu carpeta de Descargas.',
    'status.copied': 'Instrucción copiada. Pégala en tu agente.',
    'status.copy_failed': 'Aquí no se ha podido copiar. Selecciona el texto del cuadro de abajo y cópialo.',
    'status.loaded': 'Cargado {fileName}.',
    'status.load_failed': '{fileName} no es una configuración válida de Mystery Forge. No ha cambiado nada.',
    'status.reset': 'Todas las opciones han vuelto al principio.',
    'status.draft_restored': 'Hemos recuperado tu último borrador.',
    'status.preset_applied': 'Preparado para «{audience}». Puedes cambiar cualquier opción abajo.',

    'error.json': 'El archivo no contiene un texto JSON válido.',
    'error.whole_file': 'El archivo',
    'error.required': '{field}: falta este valor.',
    'error.additionalProperties': '{field}: este ajuste no existe.',
    'error.type': '{field}: el valor no es del tipo correcto.',
    'error.enum': '{field}: esta opción no está permitida.',
    'error.minimum': '{field}: el valor debe ser {limit} o más.',
    'error.maximum': '{field}: el valor debe ser {limit} o menos.',
    'error.maxLength': '{field}: el texto debe tener {limit} caracteres o menos.',
    'error.maxItems': '{field}: la lista debe tener {limit} elementos o menos.',

    'prompt.title': 'Instrucción para tu agente',
    'prompt.help': 'Selecciona este texto y pégalo en Claude Code.',
    'prompt.intro': 'Crea un juego de misterio para imprimir con Mystery Forge.',
    'prompt.run_skill':
      'Ejecuta la skill create-game con la configuración de abajo. Trátala como el archivo de configuración {fileName}. No la cambies.',
    'prompt.questions': 'Pregúntame solo lo que pregunte la skill.',

    'next.title': 'Siguientes pasos',
    'next.step1': 'Instala uv (una herramienta que ejecuta programas de Python) y Claude Code. Solo se hace una vez.',
    'next.step2': 'Abre Claude Code en la carpeta generator de Mystery Forge.',
    'next.step3': 'Pega la instrucción o di: crea un juego con {fileName}',
    'next.note':
      'El proceso tarda {time}. Quédate para las primeras preguntas. Cuando elijas el concepto de la historia, ya puedes irte.',

    'field.schema_version.label': 'Versión de la configuración',
    'field.schema_version.help': 'La versión del formato de configuración. La página la pone por ti.',
    'enum.schema_version.1.label': 'Versión 1',
    'enum.schema_version.1.help': 'El formato de configuración actual.',

    'field.audience.label': 'Grupo',
    'field.audience.help': 'Quién se sienta a la mesa. El grupo ajusta la dificultad, la lectura y el tono.',
    'enum.audience.kids.label': 'Niños',
    'enum.audience.kids.help': 'De 7 a 11 años. Textos cortos, historia amable y letra grande.',
    'enum.audience.family.label': 'Familia',
    'enum.audience.family.help': 'Pequeños y mayores juntos. Divertido para todas las edades.',
    'enum.audience.teens.label': 'Adolescentes',
    'enum.audience.teens.help': 'De 12 a 17 años. Más misterio y un poco más de reto.',
    'enum.audience.adults.label': 'Adultos',
    'enum.audience.adults.help': 'Una cena con amigos o una noche de juegos. Se permiten tramas más oscuras.',
    'enum.audience.puzzle_fans.label': 'Fans de los enigmas',
    'enum.audience.puzzle_fans.help': 'Gente que adora las salas de escape. Enigmas difíciles y menos historia.',

    'field.format.label': 'Formato',
    'field.format.help': 'Cómo avanzan los jugadores por el juego.',
    'enum.format.envelopes.label': 'Abrir sobres uno a uno',
    'enum.format.envelopes.help': 'Cada enigma resuelto te dice qué sobre abrir después.',
    'enum.format.case_file.label': 'Leer un expediente y acusar a un sospechoso',
    'enum.format.case_file.help': 'Estudia las pistas, encuentra al culpable y demuéstralo.',
    'enum.format.both.label': 'Las dos cosas (recomendado)',
    'enum.format.both.help': 'Los sobres revelan el expediente paso a paso. La experiencia más completa.',

    'field.players.label': 'Jugadores',
    'field.players.help': 'Las personas que juegan.',
    'field.players.count.label': 'Número de jugadores',
    'field.players.count.help': 'De 1 a 12. Con más jugadores hay más enigmas a la vez.',
    'field.players.names.label': 'Nombres de los jugadores',
    'field.players.names.help': 'El agente puede poner los nombres en las fichas de personaje y en la historia.',

    'field.host.label': 'Quién dirige el juego',
    'field.host.help': 'El anfitrión es la persona que imprime y prepara el juego.',
    'enum.host.self_running.label': 'El juego se dirige solo',
    'enum.host.self_running.help': 'Todos juegan. Las páginas os dicen qué hacer después.',
    'enum.host.host_plays.label': 'El anfitrión también juega',
    'enum.host.host_plays.help': 'El anfitrión prepara la mesa y luego juega como los demás.',
    'enum.host.game_master.label': 'Un director de juego',
    'enum.host.game_master.help': 'El anfitrión conoce la solución, lee la historia en voz alta y da pistas.',

    'field.duration_minutes.label': 'Tiempo de juego',
    'field.duration_minutes.help': 'Lo que dura la partida en la mesa, de 30 minutos a 4 horas.',

    'field.difficulty.label': 'Dificultad',
    'field.difficulty.help': 'Lo difíciles que son los enigmas.',
    'enum.difficulty.easy.label': 'Fácil',
    'enum.difficulty.easy.help': 'Pistas claras. Ideal para quien juega por primera vez.',
    'enum.difficulty.medium.label': 'Media',
    'enum.difficulty.medium.help': 'Hay que pensar un poco. Ideal para casi todos los grupos.',
    'enum.difficulty.hard.label': 'Difícil',
    'enum.difficulty.hard.help': 'Las pistas se esconden bien. Para grupos que juegan a menudo.',
    'enum.difficulty.expert.label': 'Experto',
    'enum.difficulty.expert.help': 'Pocas pistas y muchos pasos. Para amantes de los enigmas.',

    'field.language.label': 'Idioma del juego',
    'field.language.help': 'El idioma de todas las páginas impresas.',
    'enum.language.en.label': 'Inglés',
    'enum.language.en.help': 'Todas las páginas en inglés.',
    'enum.language.es.label': 'Español',
    'enum.language.es.help': 'Todas las páginas en español.',
    'enum.language.ca.label': 'Catalán',
    'enum.language.ca.help': 'Todas las páginas en catalán.',
    'enum.language.fr.label': 'Francés',
    'enum.language.fr.help': 'Todas las páginas en francés.',
    'enum.language.de.label': 'Alemán',
    'enum.language.de.help': 'Todas las páginas en alemán.',
    'enum.language.it.label': 'Italiano',
    'enum.language.it.help': 'Todas las páginas en italiano.',
    'enum.language.pt.label': 'Portugués',
    'enum.language.pt.help': 'Todas las páginas en portugués.',

    'field.theme.label': 'Historia',
    'field.theme.help': 'La idea de la historia y su tono.',
    'field.theme.idea.label': 'Idea para la historia',
    'field.theme.idea.help': 'Unas palabras o unas líneas. Lugares, personajes y un crimen ayudan mucho.',
    'field.theme.tone.label': 'Tono',
    'field.theme.tone.help': 'Qué sensación transmite la historia.',
    'enum.theme.tone.surprise.label': 'Sorpréndeme',
    'enum.theme.tone.surprise.help': 'El agente elige el tono que encaja con la idea.',
    'enum.theme.tone.cozy.label': 'Acogedor',
    'enum.theme.tone.cozy.help': 'Cálido y ligero, como un misterio de pueblo.',
    'enum.theme.tone.adventure.label': 'Aventura',
    'enum.theme.tone.adventure.help': 'Mapas, tesoros y una carrera contra el reloj.',
    'enum.theme.tone.noir.label': 'Negro',
    'enum.theme.tone.noir.help': 'Calles con lluvia, secretos y un detective cansado.',
    'enum.theme.tone.spooky.label': 'Inquietante',
    'enum.theme.tone.spooky.help': 'Puertas que crujen y sombras extrañas.',
    'enum.theme.tone.comedic.label': 'Divertido',
    'enum.theme.tone.comedic.help': 'Sospechosos absurdos y muchas bromas.',
    'enum.theme.tone.dramatic.label': 'Dramático',
    'enum.theme.tone.dramatic.help': 'Mucho en juego, traiciones y grandes revelaciones.',
    'field.theme.era.label': 'Época',
    'field.theme.era.help': 'Cuándo ocurre la historia.',
    'enum.theme.era.any.label': 'Cualquiera',
    'enum.theme.era.any.help': 'El agente elige la época que encaja con la idea.',
    'enum.theme.era.historical.label': 'El pasado',
    'enum.theme.era.historical.help': 'Castillos, trenes de vapor o los felices años veinte.',
    'enum.theme.era.modern.label': 'Hoy',
    'enum.theme.era.modern.help': 'Móviles, oficinas y ciudades modernas.',
    'enum.theme.era.future.label': 'El futuro',
    'enum.theme.era.future.help': 'Estaciones espaciales, robots y nueva tecnología.',
    'enum.theme.era.fantasy.label': 'Fantasía',
    'enum.theme.era.fantasy.help': 'Magia, dragones y mundos inventados.',

    'field.content.label': 'Contenido',
    'field.content.help': 'Límites sobre lo que puede contener la historia.',
    'field.content.death_allowed.label': 'Una muerte en la historia',
    'field.content.death_allowed.help':
      'Activado permite un asesinato clásico. Desactivado deja el crimen en un robo o un enigma.',
    'field.content.scary_level.label': 'Nivel de miedo',
    'field.content.scary_level.help': 'Cuánto miedo puede dar la historia.',
    'enum.content.scary_level.none.label': 'Nada',
    'enum.content.scary_level.none.help': 'Nada de miedo.',
    'enum.content.scary_level.mild.label': 'Un poco',
    'enum.content.scary_level.mild.help': 'Algún escalofrío de vez en cuando.',
    'enum.content.scary_level.spooky.label': 'Terror',
    'enum.content.scary_level.spooky.help': 'Ambiente de auténtica historia de fantasmas.',
    'field.content.reading_load.label': 'Lectura',
    'field.content.reading_load.help': 'Cuánto texto leen los jugadores.',
    'enum.content.reading_load.light.label': 'Ligera',
    'enum.content.reading_load.light.help': 'Textos cortos. Ideal para niños y grupos grandes.',
    'enum.content.reading_load.medium.label': 'Media',
    'enum.content.reading_load.medium.help': 'Cartas y notas de una página más o menos.',
    'enum.content.reading_load.heavy.label': 'Abundante',
    'enum.content.reading_load.heavy.help': 'Diarios, informes y cartas largas llenas de pistas.',

    'field.personalization.label': 'Toques personales',
    'field.personalization.help': 'Detalles personales que incluye la historia.',
    'field.personalization.host_name.label': 'Nombre del anfitrión',
    'field.personalization.host_name.help': 'La historia puede nombrar al anfitrión.',
    'field.personalization.place.label': 'Lugar',
    'field.personalization.place.help': 'Dónde jugáis. La historia puede ocurrir allí.',
    'field.personalization.inside_jokes.label': 'Bromas internas',
    'field.personalization.inside_jokes.help': 'Bromas o referencias cortas que conoce tu grupo. Hasta 5.',
    'field.personalization.dedication.label': 'Dedicatoria',
    'field.personalization.dedication.help': 'Una línea para la portada, por ejemplo para un cumpleaños.',

    'field.puzzle_preferences.label': 'Tipos de enigma',
    'field.puzzle_preferences.help': 'Cuánto les gusta a los jugadores cada tipo de enigma.',
    'field.puzzle_preferences.words.label': 'Palabras',
    'field.puzzle_preferences.words.help': 'Anagramas, cifrados y mensajes ocultos.',
    'field.puzzle_preferences.numbers.label': 'Números',
    'field.puzzle_preferences.numbers.help': 'Códigos de candado, sumas y fechas.',
    'field.puzzle_preferences.logic.label': 'Lógica',
    'field.puzzle_preferences.logic.help': 'Tablas de pistas: quién se sentó dónde, quién tiene qué.',
    'field.puzzle_preferences.visual.label': 'Visuales',
    'field.puzzle_preferences.visual.help': 'Detalles ocultos en dibujos, mapas y símbolos.',
    'field.puzzle_preferences.crafts.label': 'Manualidades',
    'field.puzzle_preferences.crafts.help': 'Doblar, recortar y mirar páginas a contraluz.',
    'field.puzzle_preferences.deduction.label': 'Deducción',
    'field.puzzle_preferences.deduction.help': 'Descubrir quién miente, comparar coartadas y ver el fallo.',
    ...preferenceChoices('words', SPANISH_PREFERENCE),
    ...preferenceChoices('numbers', SPANISH_PREFERENCE),
    ...preferenceChoices('logic', SPANISH_PREFERENCE),
    ...preferenceChoices('visual', SPANISH_PREFERENCE),
    ...preferenceChoices('crafts', SPANISH_PREFERENCE),
    ...preferenceChoices('deduction', SPANISH_PREFERENCE),

    'field.equipment.label': 'Material',
    'field.equipment.help': 'Lo que tienes para imprimir y montar el juego.',
    'field.equipment.printer.label': 'Impresora',
    'field.equipment.printer.help': 'El agente elige colores que se impriman bien en ella.',
    'enum.equipment.printer.color.label': 'Color',
    'enum.equipment.printer.color.help': 'Páginas a todo color.',
    'enum.equipment.printer.black_and_white.label': 'Blanco y negro',
    'enum.equipment.printer.black_and_white.help': 'Las páginas usan solo negro y tonos de gris.',
    'field.equipment.ink_saving.label': 'Ahorrar tinta',
    'field.equipment.ink_saving.help': 'Fondos claros que gastan menos tinta.',
    'field.equipment.paper.label': 'Tamaño de papel',
    'field.equipment.paper.help': 'El papel de tu impresora.',
    'enum.equipment.paper.A4.label': 'A4',
    'enum.equipment.paper.A4.help': 'El tamaño habitual en Europa y casi todo el mundo.',
    'enum.equipment.paper.Letter.label': 'Carta',
    'enum.equipment.paper.Letter.help': 'El tamaño habitual en Estados Unidos y Canadá.',
    'field.equipment.scissors.label': 'Tijeras',
    'field.equipment.scissors.help': 'Los jugadores pueden recortar papel.',
    'field.equipment.tape_or_glue.label': 'Celo o pegamento',
    'field.equipment.tape_or_glue.help': 'Los jugadores pueden pegar piezas.',
    'field.equipment.envelopes.label': 'Sobres',
    'field.equipment.envelopes.help': 'Tienes sobres para esconder las siguientes partes del juego.',

    'field.assistance.label': 'Ayuda',
    'field.assistance.help': 'Ayuda para los jugadores durante el juego.',
    'field.assistance.hints.label': 'Pistas',
    'field.assistance.hints.help': 'Pequeños empujones para cada enigma, de uno en uno.',
    'field.assistance.paper_answer_check.label': 'Comprobación en papel',
    'field.assistance.paper_answer_check.help': 'Una página impresa para comprobar respuestas sin ningún aparato.',
    'field.assistance.companion_page.label': 'Página de apoyo',
    'field.assistance.companion_page.help':
      'Una página para el móvil o el ordenador que comprueba respuestas y da pistas.',

    'field.visuals.label': 'Aspecto',
    'field.visuals.help': 'El aspecto de las páginas impresas.',
    'field.visuals.style.label': 'Estilo',
    'field.visuals.style.help': 'Los colores, las letras y los adornos de las páginas.',
    'enum.visuals.style.auto.label': 'Automático',
    'enum.visuals.style.auto.help': 'El agente elige el estilo que encaja con la historia.',
    'enum.visuals.style.vintage.label': 'Antiguo',
    'enum.visuals.style.vintage.help': 'Papel viejo, letra de máquina de escribir y sellos.',
    'enum.visuals.style.noir.label': 'Negro',
    'enum.visuals.style.noir.help': 'Blanco, negro y un toque de rojo.',
    'enum.visuals.style.modern.label': 'Moderno',
    'enum.visuals.style.modern.help': 'Páginas limpias, como un informe policial de hoy.',
    'enum.visuals.style.victorian.label': 'Victoriano',
    'enum.visuals.style.victorian.help': 'Marcos recargados y letras elegantes.',
    'enum.visuals.style.scifi.label': 'Ciencia ficción',
    'enum.visuals.style.scifi.help': 'Pantallas, cuadrículas y colores luminosos.',
    'enum.visuals.style.fantasy.label': 'Fantasía',
    'enum.visuals.style.fantasy.help': 'Pergamino, runas y mapas antiguos.',
    'enum.visuals.style.kids.label': 'Infantil',
    'enum.visuals.style.kids.help': 'Colores vivos y formas redondas y amables.',
    'enum.visuals.style.minimal.label': 'Minimalista',
    'enum.visuals.style.minimal.help': 'Páginas sencillas que se imprimen rápido y limpias.',
    'field.visuals.images.label': 'Imágenes',
    'field.visuals.images.help': 'Dibujos en las páginas.',
    'enum.visuals.images.svg.label': 'Dibujos',
    'enum.visuals.images.svg.help': 'Dibujos sencillos que el agente crea para la historia.',
    'enum.visuals.images.none.label': 'Sin imágenes',
    'enum.visuals.images.none.help': 'Solo texto. Más rápido de crear y de imprimir.',
    'field.visuals.readable_font.label': 'Letra fácil de leer',
    'field.visuals.readable_font.help': 'Una letra grande y sencilla. Ideal para niños y para ojos cansados.',

    'field.generation.label': 'Generación',
    'field.generation.help': 'Cómo trabaja el agente.',
    'field.generation.quality.label': 'Calidad',
    'field.generation.quality.help': 'Más comprobaciones dan mejores enigmas, pero tardan más.',
    'enum.generation.quality.fast.label': 'Rápida',
    'enum.generation.quality.fast.help': 'Menos comprobaciones. Ideal para una prueba rápida.',
    'enum.generation.quality.best.label': 'La mejor',
    'enum.generation.quality.best.help': 'Más jugadores de prueba revisan cada enigma.',
    'field.generation.pick_concept.label': 'Concepto de la historia',
    'field.generation.pick_concept.help': 'Primero el agente escribe varios conceptos de historia.',
    'enum.generation.pick_concept.ask.label': 'Quiero elegir',
    'enum.generation.pick_concept.ask.help': 'El agente te enseña los conceptos y tú eliges uno.',
    'enum.generation.pick_concept.agent.label': 'Elige el agente',
    'enum.generation.pick_concept.agent.help': 'El agente elige uno. La historia también será una sorpresa para ti.',
    'field.generation.seed.label': 'Semilla',
    'field.generation.seed.help':
      'Un número que hace repetibles las elecciones al azar. 0 significa una semilla nueva.',

    'field.output.label': 'Salida',
    'field.output.help': 'Dónde guarda el agente el juego terminado.',
    'field.output.folder.label': 'Carpeta de salida',
    'field.output.folder.help': 'La carpeta para el juego terminado. Vacío significa tu Escritorio.',
  };

  /** @type {Record<MysteryForgeUiLanguage, Record<string, string>>} */
  const TEXTS = { en, es };

  /**
   * Return the text of a key in a language, with each {name} placeholder filled from `params`. An unknown language
   * falls back to English, and an unknown key returns the key itself, so a gap shows on the page instead of a crash.
   * @param {string} language
   * @param {string} key
   * @param {Record<string, string | number>} [params]
   * @returns {string}
   */
  function translate(language, key, params = {}) {
    const texts = TEXTS[/** @type {MysteryForgeUiLanguage} */ (language)] ?? en;
    const template = texts[key] ?? key;
    return template.replace(/\{(\w+)\}/g, (placeholder, name) => (name in params ? String(params[name]) : placeholder));
  }

  /**
   * Return the first browser language that the page supports, else English.
   * @param {readonly string[]} browserLanguages
   * @returns {MysteryForgeUiLanguage}
   */
  function pickUiLanguage(browserLanguages) {
    for (const browserLanguage of browserLanguages) {
      const base = browserLanguage.toLowerCase().split('-')[0];
      const match = UI_LANGUAGES.find((language) => language === base);
      if (match) {
        return match;
      }
    }
    return 'en';
  }

  /**
   * Return the keys that each language must define: a label and a help text for each property path of the schema,
   * and for each enum value.
   * @param {MysteryForgeJsonSchema} schema
   * @returns {string[]}
   */
  function requiredSchemaTextKeys(schema) {
    /** @type {string[]} */
    const keys = [];
    /**
     * @param {MysteryForgeJsonSchema} node
     * @param {string} prefix
     */
    function visit(node, prefix) {
      for (const [name, child] of Object.entries(node.properties ?? {})) {
        const fieldPath = prefix ? `${prefix}.${name}` : name;
        keys.push(`field.${fieldPath}.label`, `field.${fieldPath}.help`);
        for (const value of child.enum ?? []) {
          keys.push(`enum.${fieldPath}.${String(value)}.label`, `enum.${fieldPath}.${String(value)}.help`);
        }
        visit(child, fieldPath);
      }
    }
    visit(schema, '');
    return keys;
  }

  globalThis.MysteryForgeUiText = { UI_LANGUAGES, TEXTS, translate, pickUiLanguage, requiredSchemaTextKeys };
})();
