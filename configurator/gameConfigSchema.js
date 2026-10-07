// GENERATED from contracts/game-config.schema.json by `npm run generate:schema`. Do not edit.
globalThis.MysteryForgeGameConfigSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "mystery-forge game config",
  "description": "The choices for one game. The configurator page writes this file and the generator reads it. A missing field takes its default value.",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version"
  ],
  "properties": {
    "schema_version": {
      "description": "The version of this config format. Only version 1 exists.",
      "type": "integer",
      "enum": [
        1
      ]
    },
    "audience": {
      "description": "Who plays the game.",
      "type": "string",
      "enum": [
        "kids",
        "family",
        "teens",
        "adults",
        "puzzle_fans"
      ],
      "default": "family"
    },
    "format": {
      "description": "The game form: sealed envelopes that players open in order, a detective case file, or both together.",
      "type": "string",
      "enum": [
        "envelopes",
        "case_file",
        "both"
      ],
      "default": "both"
    },
    "players": {
      "description": "The people who play.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "count": {
          "description": "How many people play.",
          "type": "integer",
          "minimum": 1,
          "maximum": 12,
          "default": 4
        },
        "names": {
          "description": "The names of the players, for character cards and personal touches. It can stay empty.",
          "type": "array",
          "maxItems": 12,
          "items": {
            "type": "string",
            "maxLength": 40
          },
          "default": []
        }
      }
    },
    "host": {
      "description": "The role of the host: the game runs itself, the host plays too, or the host leads as a game master and does not play.",
      "type": "string",
      "enum": [
        "self_running",
        "host_plays",
        "game_master"
      ],
      "default": "self_running"
    },
    "duration_minutes": {
      "description": "The target play time, in minutes.",
      "type": "integer",
      "minimum": 30,
      "maximum": 240,
      "default": 90
    },
    "difficulty": {
      "description": "How hard the puzzles are.",
      "type": "string",
      "enum": [
        "easy",
        "medium",
        "hard",
        "expert"
      ],
      "default": "medium"
    },
    "language": {
      "description": "The language of every printed text, as a two-letter code. The first seven have checked tables of the fixed texts; for the others, the generator translates those tables once per game.",
      "type": "string",
      "enum": [
        "en",
        "es",
        "ca",
        "fr",
        "de",
        "it",
        "pt",
        "af",
        "ar",
        "bg",
        "bn",
        "cs",
        "cy",
        "da",
        "el",
        "et",
        "eu",
        "fa",
        "fi",
        "ga",
        "gl",
        "he",
        "hi",
        "hr",
        "hu",
        "id",
        "is",
        "ja",
        "ko",
        "lt",
        "lv",
        "ms",
        "nb",
        "nl",
        "pl",
        "ro",
        "ru",
        "sk",
        "sl",
        "sr",
        "sv",
        "sw",
        "ta",
        "th",
        "tl",
        "tr",
        "uk",
        "ur",
        "vi",
        "zh"
      ],
      "default": "en"
    },
    "theme": {
      "description": "The story idea and its mood.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "idea": {
          "description": "A free description of the story. Empty means that the generator picks a surprise idea.",
          "type": "string",
          "maxLength": 500,
          "default": ""
        },
        "tone": {
          "description": "The mood of the story. Surprise lets the generator choose.",
          "type": "string",
          "enum": [
            "surprise",
            "cozy",
            "adventure",
            "noir",
            "spooky",
            "comedic",
            "dramatic"
          ],
          "default": "surprise"
        },
        "era": {
          "description": "The time period of the story. Any lets the generator choose.",
          "type": "string",
          "enum": [
            "any",
            "historical",
            "modern",
            "future",
            "fantasy"
          ],
          "default": "any"
        }
      }
    },
    "content": {
      "description": "Limits on what the story may contain.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "death_allowed": {
          "description": "True allows a death in the story, for example a murder mystery.",
          "type": "boolean",
          "default": true
        },
        "scary_level": {
          "description": "How scary the story may be.",
          "type": "string",
          "enum": [
            "none",
            "mild",
            "spooky"
          ],
          "default": "mild"
        },
        "reading_load": {
          "description": "How much text the players read.",
          "type": "string",
          "enum": [
            "light",
            "medium",
            "heavy"
          ],
          "default": "medium"
        }
      }
    },
    "personalization": {
      "description": "Personal touches that the story includes.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "host_name": {
          "description": "The name of the host. It can stay empty.",
          "type": "string",
          "maxLength": 60,
          "default": ""
        },
        "place": {
          "description": "The place where the game is played, for example a house or a town. It can stay empty.",
          "type": "string",
          "maxLength": 120,
          "default": ""
        },
        "inside_jokes": {
          "description": "Short jokes or references that the players know. The story may use them.",
          "type": "array",
          "maxItems": 5,
          "items": {
            "type": "string",
            "maxLength": 200
          },
          "default": []
        },
        "dedication": {
          "description": "A dedication for the cover, for example for a birthday. It can stay empty.",
          "type": "string",
          "maxLength": 200,
          "default": ""
        }
      }
    },
    "puzzle_preferences": {
      "description": "How much the players like each kind of puzzle.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "words": {
          "description": "Word puzzles, for example anagrams and ciphers.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        },
        "numbers": {
          "description": "Number puzzles, for example codes and sums.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        },
        "logic": {
          "description": "Logic puzzles, for example grids of clues.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        },
        "visual": {
          "description": "Visual puzzles, for example hidden details in a picture.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        },
        "crafts": {
          "description": "Craft puzzles, for example folding or cutting paper.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        },
        "deduction": {
          "description": "Deduction puzzles, for example finding who lies.",
          "type": "string",
          "enum": [
            "like",
            "neutral",
            "avoid"
          ],
          "default": "neutral"
        }
      }
    },
    "equipment": {
      "description": "What the host has to print and build the game.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "printer": {
          "description": "The kind of printer.",
          "type": "string",
          "enum": [
            "color",
            "black_and_white"
          ],
          "default": "color"
        },
        "ink_saving": {
          "description": "True uses light backgrounds that need less ink.",
          "type": "boolean",
          "default": false
        },
        "paper": {
          "description": "The paper size.",
          "type": "string",
          "enum": [
            "A4",
            "Letter"
          ],
          "default": "A4"
        },
        "scissors": {
          "description": "True means that the players can cut paper.",
          "type": "boolean",
          "default": true
        },
        "tape_or_glue": {
          "description": "True means that the players can use tape or glue.",
          "type": "boolean",
          "default": false
        },
        "envelopes": {
          "description": "True means that the host has envelopes.",
          "type": "boolean",
          "default": true
        }
      }
    },
    "assistance": {
      "description": "Help for the players during the game.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "hints": {
          "description": "True adds hints for each puzzle.",
          "type": "boolean",
          "default": true
        },
        "paper_answer_check": {
          "description": "True adds a printed page where players check their answers without a device.",
          "type": "boolean",
          "default": true
        },
        "companion_page": {
          "description": "True adds a web page that checks answers and gives hints.",
          "type": "boolean",
          "default": true
        }
      }
    },
    "visuals": {
      "description": "The look of the printed pages.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "style": {
          "description": "The visual style. Auto lets the generator choose a style that fits the theme.",
          "type": "string",
          "enum": [
            "auto",
            "vintage",
            "noir",
            "modern",
            "victorian",
            "scifi",
            "fantasy",
            "kids",
            "minimal"
          ],
          "default": "auto"
        },
        "images": {
          "description": "The kind of images: drawings in SVG (a vector image format), or no images.",
          "type": "string",
          "enum": [
            "svg",
            "none"
          ],
          "default": "svg"
        },
        "readable_font": {
          "description": "True uses a large, plain font that is easy to read.",
          "type": "boolean",
          "default": false
        }
      }
    },
    "generation": {
      "description": "How the generator works.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "quality": {
          "description": "Fast uses fewer checks. Best uses more checks and takes longer.",
          "type": "string",
          "enum": [
            "fast",
            "best"
          ],
          "default": "best"
        },
        "pick_concept": {
          "description": "Who picks the story concept: the generator asks the user, or the agent picks it.",
          "type": "string",
          "enum": [
            "ask",
            "agent"
          ],
          "default": "ask"
        },
        "seed": {
          "description": "A number that makes random choices repeatable. 0 means a new random seed.",
          "type": "integer",
          "minimum": 0,
          "maximum": 2147483647,
          "default": 0
        }
      }
    },
    "output": {
      "description": "Where the generator writes the finished game.",
      "type": "object",
      "additionalProperties": false,
      "default": {},
      "properties": {
        "folder": {
          "description": "The folder for the finished game. Empty means the Desktop.",
          "type": "string",
          "maxLength": 400,
          "default": ""
        }
      }
    }
  }
};
