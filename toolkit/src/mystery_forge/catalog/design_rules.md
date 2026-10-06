# Design rules for a mystery game

Read these rules before you plan a story or a puzzle. They make a game fair, varied, and fun. Code checks many of them, but a check only catches a mistake after you make it.

## 1. The five core rules

1. **Choose the answer first.** Take the answer from the story, then build the puzzle toward it. Never write a puzzle and then look for its answer.
2. **Give each puzzle one central insight** (one "aha"), two at most. Write it down before you write the material.
3. **Clue every step.** The title, the flavor text, or a prop must point to the method. A tester must be able to explain why each step is the only sensible step.
4. **Let code build what code can build.** Use the catalog builder for every built mechanic. Never write cipher text, grids, letter counts, or arithmetic by hand.
5. **Put every fact in the kit.** Players never need outside knowledge (trivia, a Morse table) unless the kit supplies it.

## 2. Structure and pacing

- **Default shape: staged envelopes.** Use 3 or 4 stages. Inside a stage, 2 to 4 puzzles run in parallel. One gate answer opens the next envelope.
- **Stage 1** has 2 easy puzzles that players solve in under 5 minutes each. The first puzzle also teaches how the answer check works.
- **The middle stages** rise in difficulty and change the kind of puzzle each time. Open a stage with the mid-game twist.
- **The last stage** has one hard climax, then a meta puzzle or the final accusation that uses earlier answers.
- **Parallel width:** give each stage at least (players / 2) puzzles that players can solve at the same time, so nobody waits.
- **Reuse documents.** One document that feeds 2 or 3 puzzles feels designed. Make at least 40% of the puzzles combine 2 or more documents.
- **Every puzzle has an in-world reason.** Say why this thing is hidden this way ("the smuggler coded his telegrams").
- **Every solve gives story**, such as a paragraph, a new document, or a new envelope, not only a code.
- **Model the game as a graph.** Each puzzle needs answers or items from earlier puzzles. No cycles. Every puzzle is reachable. Every item is used.

| Flow shape       | Use it for                                  | Main risk                                  |
| ---------------- | ------------------------------------------- | ------------------------------------------ |
| Linear chain     | 1 or 2 players, kids, short games           | One stuck puzzle stops everyone            |
| Open parallel    | 3 to 6 players                              | Players lose the story thread              |
| Staged envelopes | The default for print and play              | Players peek at the next envelope          |
| Hub and spoke    | Detective cases with locations in any order | Clues that depend on the visit order break |
| Meta funnel      | Groups and puzzle fans                      | The meta mechanism has no clue             |

**Players and structure:**

- **1 player:** a linear chain or 2 tracks. Add more answer confirmations. Avoid puzzles that need discussion, such as a connection wall.
- **2 players:** 2 tracks per stage and a shared final puzzle.
- **3 or 4 players:** 2 or 3 tracks per stage, plus 1 group puzzle per stage that needs items from every track.
- **5 or 6 players:** 3 tracks. Add split puzzles: half the information sits in each of two documents, so two players must talk.
- **More players:** add more documents to search, not harder puzzles.

## 3. Time budget

Baseline minutes per puzzle for a group of 3 or 4 adults. The catalog gives a value per mechanic and level.

| Difficulty               | Minutes  |
| ------------------------ | -------- |
| Warm-up                  | 2 to 4   |
| Easy                     | 4 to 8   |
| Medium                   | 8 to 15  |
| Hard                     | 15 to 25 |
| Expert                   | 25 to 60 |
| Meta or final accusation | 10 to 30 |

- **Solo players** take about 1.3 times longer. **Kids from 8 to 12** take about 1.5 times longer.
- **Planned length** = the sum of the minutes on the critical path, plus 15 to 20% for reading, setup, and envelopes.
- **Parallel puzzles count once per stage**, at the slowest track.

## 4. Variety

- No 2 puzzles in a row with the same player action.
- At most 2 lookup ciphers (a table of symbols or letters, such as Morse or Caesar) per game.
- Ciphers are at most 25% of the puzzles.
- Each stage uses at least 3 different categories.
- Include at least 1 physical or spatial puzzle when the config allows scissors.
- Reskin at least half of the puzzles with the drawn motif. A chess game uses chess notation as coordinates.
- Keep cipher texts short. Insight is the fun. Grind (decoding 200 letters) is not.

## 5. Puzzle craft

- **The title is a hint.** Write "Bird Watching" for a bird ring code, never "Puzzle 4".
- **Confirmation:** partial results must look right, such as real words or a clear pattern. Players then know that they are on track.
- **State the last step when players cannot guess it.** For example, "read the shaded letters". Do this always for kids and families.
- **Match the method to the story object.** A lock log becomes a code-breaker puzzle. A train timetable becomes an alibi check.
- **Never over-explain.** The material must not describe the full method. The hints do that.
- **Never put the answer in a title, flavor text, or caption.** Code scans for it, also reversed and with spaces.
- **Use one name for each thing.** A name, a number, or an id must be the same in every document. Take it from the fact registry.
- **Check your own dates.** Code computes weekdays and date math. Never write a weekday for a real date by hand.

## 6. Answers and answer checks

- **Answer slots show their shape**, such as letter-count blanks or "4 digits". This catches near misses without a computer.
- **Prefer chain confirmation.** Use an answer as the key of the next puzzle. A wrong answer then gives nonsense.
- **List 2 to 5 near misses per puzzle** (a shift off by one, the wrong suspect with a strong motive, a reversed order). Each near miss gets a short custom message.
- **Never print an answer on the same page as its puzzle**, and never on the back of game material.

## 7. Hint ladder

Every puzzle has 3 hints and a separate answer card.

| Level  | Gives                           | Example                                                      |
| ------ | ------------------------------- | ------------------------------------------------------------ |
| Hint 1 | What you need and where to look | "You need the receipt and the train ticket from envelope B." |
| Hint 2 | A nudge to the method           | "Every letter moved by the same number of steps."            |
| Hint 3 | The method                      | "Shift each letter back by 3. D becomes A."                  |
| Answer | The answer and a short why      | "LIGHTHOUSE. The shifted note reads ..."                     |

- Hint 1 never names the method. Hint 2 never gives the answer. Hint 3 never gives the full answer.
- Each hint stands alone. A player who reads only hint 2 still understands it.
- A hint cites only material that the solution uses.
- For long work (a cipher, a sudoku), add a check to hint 3, such as "if your third letter is not a vowel, check row 2 again".
- A hint never contains a later answer.

## 8. Fair play rules for cases

1. The culprit appears in stage 1 material.
2. No supernatural answer, unless the setting states the rules of its magic and their limits up front.
3. No unknown poison or device that needs an explanation after the reveal.
4. No luck and no intuition. Every deduction step has a document behind it.
5. Every clue is in the kit.
6. The players' own character is never the culprit, unless the frame sets up that twist fairly.
7. No secret twins or doubles, unless the story sets them up.
8. The solution cites a document for every step.
9. A personal motive. No faceless agency, unless the genre is espionage.
10. One secret passage at most, and the floor plan shows it.

## 9. Deduction that has one answer

- **Hold the truth first.** The story file holds the timeline (who, where, when), the objects, the relations, and the crime (who, how, why).
- **Means, motive, opportunity.** Every suspect has at least 1 of the 3, so nobody is out at a glance. Innocent suspects each have a strong motive. Only the culprit has all 3, plus a lock clue: a fact that only the culprit could know or do.
- **Exclusion clue.** Each innocent suspect has one: an alibi from 2 independent sources, or a physical impossibility.
- **Two-clue rule.** Each critical fact appears in 2 independent documents, in case players miss one. The lock clue may appear once.
- **Planned lies only.** Each lie has a liar and a document that contradicts it. The prose must add no other contradiction.
- **Nobody is in two places at once** by accident. State all travel and transfer times.
- **Accusation:** ask who, how, and why, plus key evidence. Suggested points: who 40, how 20, why 20, evidence 20. Give a short rebuttal for every wrong suspect, so a wrong guess still teaches.

## 10. Red herrings

- Every red herring has a planned resolution in the kit. The odd man in the photo was the delivery driver, and the delivery receipt shows it.
- Red herrings come from the story (an unrelated secret, a debt), not from random noise.
- Use 1 or 2 per stage, plus one strong "obvious suspect" per case. Use fewer for kids.
- In an envelope escape, every thing that looks like a puzzle must be a puzzle. In a case file, extra documents are fine.

## 11. Story variety

- **Use every drawn card:** the setting, era, goal, twist, frame, tone, and motif.
- **Never use a blocklisted name, phrase, or plot.** The list is in `ingredients.yaml` under `cliches`.
- **Take names from lists that match the era and the place.** Never invent names freely.
- **Cast:** 4 to 6 suspects. Give each a job, an age, a voice, and one secret.
- **Specific details:** each document has 3 or more concrete, checkable details, such as a brand, a street, a price, or a time. Invent brands and companies. Never use real ones.
- **Voice cards:** write a one-line voice for each author (a tired officer, a chatty teenager, a careful accountant). Each document sounds like its author.
- **Audience:** follow the audience rules in `ingredients.yaml` (word limits, themes to avoid, crimes allowed).

## 12. Known AI mistakes and their fixes

| Mistake                   | Example                                                 | Fix                                                               |
| ------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------- |
| Wrong letter counts       | An anagram that misses a letter, an acrostic off by one | Use the verifier. Never count letters yourself.                   |
| Wrong encoding            | A Caesar text with 2 wrong letters                      | Use the builder.                                                  |
| Logic with 0 or 2 answers | A logic grid with 3 solutions                           | Use the builder with its solver.                                  |
| Ambiguous answers         | A riddle that fits "shadow" and "silence"               | Add letter-count blanks and a line that excludes the near answer. |
| Famous puzzle reused      | A well-known riddle with a changed answer               | Write a new puzzle about a story object.                          |
| Missing material          | "Use the map", and no map exists                        | Reference documents by id only.                                   |
| Facts that drift          | Age 52 in one document, 54 in another                   | Take every fact from the story registry.                          |
| Invented real-world facts | A wrong weekday for a real date                         | Let code compute dates. Prefer in-world facts.                    |
| Answer leak               | The answer word in a title                              | Code scans for it. Rename the title.                              |
| Unclued extraction        | "Take the 3rd letter", with no reason                   | Give the number an in-world source.                               |
| Monotony                  | 6 ciphers in a row                                      | Follow the variety rules.                                         |
| Bad pictures              | AI art with the wrong count of objects                  | Use builder art for every picture that carries a clue.            |

## 13. Accessibility

- **Never use color alone** to carry meaning. Add patterns, labels, or shapes.
- **Readable text:** body text at 11 pt or more (12 pt or more for kids), left aligned, never justified. No long italic or capital-letter passages.
- **Handwriting fonts** only for short notes, under 80 words. Print a readable copy too.
- **Dyslexia:** do not use letter-order puzzles (anagrams) as gates in kids' games.
- **Low vision:** small text and spot-the-difference puzzles get a large print version.
- **Motor:** every puzzle that needs scissors has a no-cut fallback.
- **Language:** sound-based puzzles (rebus, sound-alike words) work only in English.
- **No audio:** write every sound clue as a transcript.

## 14. Print rules

- **Black and white first.** Every element must read in greyscale. Color is decoration only.
- **Text sizes:** 9 pt body at least, 7 pt fine print, 6 pt only for microtext puzzles.
- **Grey fills** of 15% or more. Lighter greys vanish on laser printers.
- **Cut and fold marks:** dashed cut lines with a scissors icon, valley folds as dashes, mountain folds as dash-dot lines.
- **Alignment puzzles** (masks, overlays, fold-ins) need registration marks and a "print at 100%" note.
- **Separate files for spoilers.** Hints and solutions never share a page with the game material.
