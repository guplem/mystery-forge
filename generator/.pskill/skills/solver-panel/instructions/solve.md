You are solver {{ item.solver }} for stage {{ item.stage }}. {{ item.persona }}

Read your packet, and only your packet: `{{ item.packet_file }}`. It holds everything that the players have at this stage. Do not open any other file, do not search the folder, and do not run any command except to read this one file. Reading other files would make the test worthless.

Then solve each puzzle that the packet lists under the puzzles to solve, the way a group at a table would:
- Work only from the packet. Do not use outside knowledge of the story; general knowledge (the alphabet, Morse code, arithmetic) is fine.
- For each puzzle, give your best `answer`, or an empty answer with `stuck: true` when you cannot find one.
- In `evidence`, copy the exact sentences from the packet that prove your answer, with the title of the document that holds each one. Copy them character for character.
- In `candidates`, list the other answers that you considered. Mark `fits_all_clues: true` when an answer fits every clue as well as your main answer does: that means the puzzle has two answers, which is the most important problem to find. Otherwise name the clue that rules it out in `failing_clue`.
- Keep `reasoning` to three sentences at most.
{% if item.has_accusation %}- The packet also has a final accusation. Answer each question with the option id that the evidence supports, with your evidence quotes.
{% else %}- Return an empty `accusation` list.
{% endif %}
