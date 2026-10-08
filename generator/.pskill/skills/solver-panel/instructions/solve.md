You are solver {{ item.solver }} for stage {{ item.stage }}. {{ item.persona }}

Read your packet, and only your packet: `{{ item.packet_file }}`. It holds everything that the players have at this stage. Do not open any other file, do not search the folder, and do not run any command except to read this one file. Reading other files would make the test worthless.

Then solve each puzzle that the packet lists under the puzzles to solve, the way a group at a table would:
- Work only from the packet. Do not use outside knowledge of the story; general knowledge (the alphabet, Morse code, arithmetic) is fine.
- For each puzzle, give your best `answer`, or an empty answer with `stuck: true` when you cannot find one.
- In `evidence`, copy the exact sentences from the packet that prove your answer, with the title of the document that holds each one. Copy them character for character.
- In `candidates`, list the other answers that you considered. Mark `fits_all_clues: true` when an answer fits every clue as well as your main answer does: that means the puzzle has two answers, which is the most important problem to find. Otherwise name the clue that rules it out in `failing_clue`.
- Keep `reasoning` to three sentences at most.
- In `aha`, name in one sentence the insight that unlocked the puzzle. Set `all_steps_stated: true` when the material told you every step of the method, so that you only had to follow instructions; set it to false when you had to discover something yourself.
- In `gaps`, list each step that no document supports: a fact or a link that you had to invent, or a letter or number that you found only by elimination or from the shape of the answer. Leave it empty when every step had evidence. A gap is a flaw of the game, not of your solve, so report it even when you are sure of the answer. These are not gaps: an inference that combines two documents (that is the game), a document that the list of the puzzle's material does not name, and a story meaning of the answer that the documents do not confirm yet.
{% if item.kids | default(false) %}- This game is for children of 8 to 12. In `gaps`, also list each rule or piece of knowledge that a 9-year-old would need and that no page states, such as how an old phone keypad works or what Morse code is. A child must be able to start every puzzle without a hint.
{% endif %}- Write your answer to a file with the Write tool and submit it from that file (`... submit <run> --task <n> < answer.yaml`): a long shell command fails on Windows.
{% if item.story_only %}- Your packet has no puzzle: return an empty `answers` list. It tests whether players can skip the puzzles. Answer an accusation question only when the documents prove the option, with your evidence quotes; otherwise leave `option` empty. Do not guess.
{% elif item.has_accusation %}- The packet also has a final accusation. Answer each question with the option id that the evidence supports, with your evidence quotes.
{% else %}- Return an empty `accusation` list.
{% endif %}
