"""The fixed texts of the outputs (labels, headings, warnings) in every game language, plus date formatting.

The agent writes the story texts in the game language. Every text that the toolkit itself prints comes from here, so
a Spanish game never shows an English label. English is the fallback for an unknown language. A test checks that
every language has every key.
"""

from datetime import datetime
from string import Formatter
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

LANGUAGES: Final[tuple[str, ...]] = ("en", "es", "ca", "fr", "de", "it", "pt")

STRINGS: Final[dict[str, dict[str, str]]] = {
    "en": {
        "envelope_label": "Envelope {stage}",
        "continued": "continued",
        "materials_title": "Game materials",
        "file_manual": "1 - START HERE (manual)",
        "file_materials": "2 - PRINT THIS (game materials)",
        "file_hints": "3 - Hints",
        "file_solutions": "4 - Solutions",
        "file_companion": "Game companion",
        "folder_spoilers": "HOST ONLY - spoilers",
        "file_export_warnings": "0 - READ FIRST (warnings)",
        "export_warnings_title": "Read this before you play",
        "export_warnings_intro": (
            "Mystery Forge tests every game with automatic checks and with AI test players. Some tests of this game "
            "did not pass. The game is probably still playable, but the parts below can be unclear, too hard, or "
            "wrong."
        ),
        "export_warnings_fix": (
            "To fix them, double-click Start Mystery Forge, type 4, and ask the AI to fix the warnings of this game."
        ),
        "export_warning_puzzle": "Puzzle {code}: {problems}",
        "export_warning_accusation": "Accusation form: {problems}",
        "export_warning_checks_failing": "some automatic checks failed.",
        "export_warning_checks_stale": "the automatic checks did not run after the last change.",
        "export_warning_panel_stale": "the test players did not try it after the last change.",
        "export_warning_ambiguous": "the test players found more than one answer that fits.",
        "export_warning_gold_suspect": "the test players think that the expected answer may be wrong.",
        "export_warning_too_hard": "the test players could not solve it.",
        "export_warning_guessable": "the test players could guess the answer without the clues.",
        "export_warning_incomplete": "the test players think that something they need is missing.",
        "export_warning_trivial": "the test players found it too easy.",
        "export_warning_insufficient_solvers": "too few test players finished the test.",
        "export_warning_puzzles_not_needed": "the test players could answer it without solving the puzzles.",
        "made_with": "Made with Mystery Forge",
        "page_label": "Page {number} of {count}",
        "copy_label": "Copy {number} of {count}",
        "puzzle_badge": "Puzzle",
        "print_cut": "Cut along the dashed line.",
        "print_fold": "Fold along the dash-dot line.",
        "cover_kicker": "A printable mystery",
        "cover_players": "{count} players",
        "cover_players_solo": "1 player",
        "accusation_intro_solo": (
            "Answer every question. "
            "Tick one box for each question and name the document that proves it. Then count your points."
        ),
        "manual_play_accusation_solo": "At the end, fill in the accusation form.",
        "cover_duration": "About {minutes} minutes",
        "cover_detectives": "Detectives: {names}",
        "cover_do_not_read": "Do not read ahead. Open each envelope only when the game tells you to.",
        "stop": "STOP",
        "stage_open_at_start": "Open this envelope at the start of the game.",
        "stage_open_when": (
            "Do not open this envelope yet. Open it only when the answer check tells you to, after you solve puzzle "
            "{code}."
        ),
        "stage_turn_page": "After you open the envelope, turn this page around and read the text aloud.",
        "stage_read_aloud": "Read aloud",
        "register_title": "Answer register",
        "register_answer": "Answer",
        "register_paragraph": "Paragraph",
        "results_title": "Result paragraphs",
        "results_intro": "Read only the paragraph that the answer register sends you to.",
        "register_wrong": "Nothing happens. Try again.",
        "register_intro": (
            "Write your answer in capital letters, with no spaces and no accents, then find it in this list. "
            "Numbers come first, then words from A to Z. Read the result paragraph with the number next to it. "
            "If your answer is not in the list, it is not correct."
        ),
        "register_correct_open": "Correct! Open {envelope} now.",
        "register_correct_keep": "Correct! Write this answer down: a later puzzle needs it.",
        "register_correct_accusation": "Correct! This was the last puzzle: turn to the accusation.",
        "register_correct_notes": "Correct! Write it in your notes.",
        "register_story_card": "Before you go on, read story card {number} at the end of {envelope}.",
        "story_cards_title": "Story cards",
        "story_cards_intro": (
            "Read a card only when the answer register sends you to it. Turn the page around to read it."
        ),
        "print_cut_strips": "When you open this envelope, cut the strips apart along the dashed lines.",
        "manual_need_label_tape": "Tape or glue for the envelope labels (or write the letter on each envelope)",
        "manual_print_box_title": "Print at 100%",
        "manual_print_box_chrome": "Chrome: More settings > Scale > Default",
        "manual_print_box_edge": "Edge: More settings > Scale > Actual size",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Page Sizing & Handling > Actual size",
        "citation_revealed_by": "Revealed by puzzle {code}",
        "accusation_title": "Accusation form",
        "accusation_intro": (
            "Answer every question together. Tick one box for each question and name the document that proves it. Then "
            "count your points."
        ),
        "accusation_proof": "Which document proves it?",
        "accusation_points": "{points} points",
        "accusation_detectives": "Detectives",
        "accusation_total": "Your points: ______ of {total}",
        "labels_title": "Envelope labels",
        "labels_intro": "Cut out each label and stick it on its envelope.",
        "label_open_start": "Open at the start",
        "label_open_after": "Open only after puzzle {code}",
        "notes_title": "Detective notes",
        "notes_intro": "Write down what you learn. Use a pencil.",
        "notes_suspect": "Suspect",
        "notes_motive": "Motive",
        "notes_opportunity": "Opportunity",
        "notes_alibi": "Alibi",
        "notes_where": "Who was where?",
        "notes_free": "Notes",
        "warning_title": "Spoiler warning",
        "hints_title": "Hint cards",
        "hints_warning_text": (
            "These cards help you when you are stuck. Read only one card at a time, and always start with Hint 1."
        ),
        "hints_how_to": (
            "Cut out each card along the dashed lines. Fold it along the dash-dot line, with the print outside. The "
            "text on the back stays hidden until you turn the card over."
        ),
        "hints_companion": (
            "Do you have a phone or a computer? The Game companion page gives the same hints, one at a time."
        ),
        "hint_label": "Hint {level}",
        "answer_label": "Answer",
        "hint_turn": "Turn over to read",
        "solutions_title": "Solutions",
        "solutions_warning_text": (
            "This file holds every answer and the whole story. Read it only at the end of the game, or to check one "
            "answer."
        ),
        "solution_answer": "Answer",
        "solution_accepted": "Also accepted",
        "solution_steps": "How to solve it",
        "deduction_title": "The accusation",
        "exclusions_title": "Why not the others?",
        "truth_title": "The whole truth",
        "reveal_title": "How you could have known",
        "epilogues_title": "Endings",
        "epilogue_threshold": "{percent}% of the points or more",
        "field_from": "From",
        "field_to": "To",
        "field_cc": "Cc",
        "field_date": "Date",
        "field_time": "Time",
        "field_subject": "Subject",
        "field_case_number": "Case no.",
        "field_officer": "Officer",
        "field_station": "Station",
        "field_seat": "Seat",
        "field_passenger": "Passenger",
        "field_price": "Price",
        "field_number": "No.",
        "field_name": "Name",
        "field_role": "Occupation",
        "field_birth_date": "Born",
        "field_expires": "Valid until",
        "field_total": "Total",
        "field_reward": "Reward",
        "field_scale": "Scale",
        "field_legend": "Legend",
        "field_interviewer": "Interviewer",
        "field_place": "Place",
        "field_issuer": "Issued by",
        "field_form_number": "Form",
        "word_telegram": "Telegram",
        "word_transcript": "Transcript",
        "word_report": "Report",
        "word_confidential": "Confidential",
        "word_ticket": "Ticket",
        "word_identity": "Identity card",
        "word_receipt": "Receipt",
        "word_thanks": "Thank you",
        "manual_title": "Start here",
        "manual_checklist_title": "Printing checklist",
        "manual_file": "File",
        "manual_pages": "Pages",
        "manual_print_column": "Print?",
        "manual_print_yes": "Yes",
        "manual_print_optional": "Only if you play without a phone or computer",
        "manual_print_companion_file": "No: open it on a phone or computer",
        "manual_print_actual_size": (
            "Print at 100% (actual size), single-sided, on {paper} paper. Do not use “fit to page”."
        ),
        "manual_print_bw": "This game is made for a black-and-white printer.",
        "manual_print_color": "Color looks best, but a black-and-white printer works too.",
        "manual_print_skip_spoilers": (
            "Do not print the hints and the solutions if you have a phone or a computer at the table: use the Game "
            "companion page instead."
        ),
        "manual_need_title": "What you need",
        "manual_need_envelopes": "{count} envelopes",
        "manual_need_folders": "{count} folders or paper clips, one for each part",
        "manual_need_pencils": "Pencils and an eraser",
        "manual_need_paper": "Some scrap paper",
        "manual_need_scissors": "Scissors",
        "manual_need_tape": "Tape or glue",
        "manual_need_mirror": "A small mirror (or a bright window: hold the page against it and read it from the back)",
        "manual_need_light": "A bright window or a lamp, to hold pages against the light",
        "manual_setup_title": "Setup",
        "manual_setup_split": "Do not read the game materials. Split the stack at each page that says STOP.",
        "manual_setup_outside": "The pages before the first STOP page stay outside the envelopes: {pages}.",
        "manual_setup_outside_piles": "The pages before the first STOP page stay on the table: {pages}.",
        "manual_outside_cover": "the cover",
        "manual_outside_labels": "the envelope labels",
        "manual_outside_register": "the answer register",
        "manual_outside_notes": "the detective notes",
        "list_separator": ", ",
        "list_two": "{first} and {last}",
        "list_many": "{items}, and {last}",
        "manual_setup_envelopes": (
            "Put each part in its own envelope, with its STOP page on top. Stick the matching label on each envelope "
            "and close it."
        ),
        "manual_setup_piles": "Put each part face down in its own pile, with its STOP page on top.",
        "manual_setup_spoilers": "Keep the hints and the solutions out of sight until you need them.",
        "manual_play_title": "How to play",
        "manual_play_open_first": "Open Envelope A. Read this introduction aloud:",
        "manual_play_solve": (
            "Read the documents and solve the puzzles. The code in the corner of a page (such as A1) tells you which "
            "puzzle it belongs to."
        ),
        "manual_play_check_register": (
            "When you have an answer, find it in the answer register and read the paragraph that it sends you to."
        ),
        "manual_play_check_companion": "Or type the answer on the Game companion page.",
        "manual_play_next": (
            "A correct answer tells you when to open the next envelope. Never open an envelope before that."
        ),
        "manual_play_accusation": "At the end, fill in the accusation form together.",
        "manual_hints_title": "Hints and solutions",
        "manual_hints_text": (
            "Stuck? Take the hint cards with the code of your puzzle and read Hint 1 first. Read the next card only if "
            "you still need it. The last card gives the answer."
        ),
        "manual_hints_companion": "The Game companion page shows the same hints, one at a time.",
        "manual_solutions_text": "The solutions explain every puzzle and the whole story. Read them at the end.",
        "manual_scoring_title": "Accusation and scoring",
        "manual_scoring_text": (
            "Each question of the accusation form gives points, {total} in all. Count your points and find your ending "
            "in the solutions:"
        ),
        "manual_rank_points": "Points",
        "manual_rank_ending": "Ending",
        "manual_rank_range": "{low} to {high}",
        "manual_host_title": "Game master guide",
        "manual_host_intro": (
            "You run the game and do not play. You may read everything before the game starts. Plan your time with "
            "this table (minutes from the start):"
        ),
        "manual_host_stage": "Envelope",
        "manual_host_puzzles": "Puzzles",
        "manual_host_minutes": "Minutes",
        "manual_host_by": "Done by minute",
        "manual_host_stuck": "If a group is stuck for 10 minutes, give them the next hint.",
        "manual_host_answers": (
            "Check each answer with the answer register or the Game companion page before you hand out the next "
            "envelope."
        ),
        "manual_personal_title": "For this game",
        "manual_host_name": "Your host: {name}",
        "manual_player_names": "Detectives: {names}",
    },
    "es": {
        "envelope_label": "Sobre {stage}",
        "continued": "continuación",
        "materials_title": "Material del juego",
        "file_manual": "1 - EMPIEZA AQUÍ (manual)",
        "file_materials": "2 - IMPRIME ESTO (materiales del juego)",
        "file_hints": "3 - Pistas",
        "file_solutions": "4 - Soluciones",
        "file_companion": "Compañero de juego",
        "folder_spoilers": "SOLO ANFITRIÓN - spoilers",
        "file_export_warnings": "0 - LEE ESTO PRIMERO (avisos)",
        "export_warnings_title": "Lee esto antes de jugar",
        "export_warnings_intro": (
            "Mystery Forge prueba cada juego con comprobaciones automáticas y con jugadores de prueba de IA. Algunas "
            "pruebas de este juego no se superaron. Lo más probable es que el juego funcione, pero las partes de "
            "abajo pueden ser confusas, demasiado difíciles o incorrectas."
        ),
        "export_warnings_fix": (
            "Para corregirlas, haz doble clic en Start Mystery Forge, escribe 4 y pide a la IA que corrija los "
            "avisos de este juego."
        ),
        "export_warning_puzzle": "Enigma {code}: {problems}",
        "export_warning_accusation": "Formulario de acusación: {problems}",
        "export_warning_checks_failing": "algunas comprobaciones automáticas fallaron.",
        "export_warning_checks_stale": "las comprobaciones automáticas no se repitieron tras el último cambio.",
        "export_warning_panel_stale": "los jugadores de prueba no lo probaron tras el último cambio.",
        "export_warning_ambiguous": "los jugadores de prueba encontraron más de una respuesta posible.",
        "export_warning_gold_suspect": "los jugadores de prueba creen que la respuesta esperada puede ser incorrecta.",
        "export_warning_too_hard": "los jugadores de prueba no lo pudieron resolver.",
        "export_warning_guessable": "los jugadores de prueba pudieron adivinar la respuesta sin las pistas.",
        "export_warning_incomplete": "los jugadores de prueba creen que falta algo que necesitan.",
        "export_warning_trivial": "a los jugadores de prueba les pareció demasiado fácil.",
        "export_warning_insufficient_solvers": "muy pocos jugadores de prueba terminaron la prueba.",
        "export_warning_puzzles_not_needed": "los jugadores de prueba lo pudieron responder sin resolver los enigmas.",
        "made_with": "Hecho con Mystery Forge",
        "page_label": "Página {number} de {count}",
        "copy_label": "Copia {number} de {count}",
        "puzzle_badge": "Enigma",
        "print_cut": "Recorta por la línea discontinua.",
        "print_fold": "Dobla por la línea de puntos y rayas.",
        "cover_kicker": "Un misterio para imprimir",
        "cover_players": "{count} jugadores",
        "cover_players_solo": "1 jugador",
        "accusation_intro_solo": (
            "Responde a cada pregunta. "
            "Marca una casilla en cada pregunta y anota el documento que lo demuestra. Después cuenta tus puntos."
        ),
        "manual_play_accusation_solo": "Al final, rellena el formulario de acusación.",
        "cover_duration": "Unos {minutes} minutos",
        "cover_detectives": "Detectives: {names}",
        "cover_do_not_read": "No leas por adelantado. Abre cada sobre solo cuando el juego te lo indique.",
        "stop": "ALTO",
        "stage_open_at_start": "Abre este sobre al empezar la partida.",
        "stage_open_when": (
            "No abras este sobre todavía. Ábrelo solo cuando la comprobación de respuestas te lo indique, después de "
            "resolver el enigma {code}."
        ),
        "stage_turn_page": "Cuando abras el sobre, gira esta página y lee el texto en voz alta.",
        "stage_read_aloud": "Leed en voz alta",
        "register_title": "Registro de respuestas",
        "register_answer": "Respuesta",
        "register_paragraph": "Párrafo",
        "results_title": "Párrafos de resultado",
        "results_intro": "Lee solo el párrafo al que te envía el registro de respuestas.",
        "register_wrong": "No pasa nada. Inténtalo de nuevo.",
        "register_intro": (
            "Escribe tu respuesta en mayúsculas, sin espacios y sin acentos (la Ñ se escribe N), y búscala en "
            "esta lista. Primero van los números y después las palabras de la A a la Z. Lee el párrafo de "
            "resultado con el número que tiene al lado. Si tu respuesta no está en la lista, no es correcta."
        ),
        "register_correct_open": "¡Correcto! Abre ahora el {envelope}.",
        "register_correct_keep": "¡Correcto! Apunta esta respuesta: un enigma posterior la necesita.",
        "register_correct_accusation": "¡Correcto! Era el último enigma: pasad a la acusación.",
        "register_correct_notes": "¡Correcto! Apúntalo en tus notas.",
        "register_story_card": "Antes de seguir, lee la tarjeta de historia {number} al final del {envelope}.",
        "story_cards_title": "Tarjetas de historia",
        "story_cards_intro": (
            "Lee una tarjeta solo cuando el registro de respuestas te envíe a ella. Gira la hoja para leerla."
        ),
        "print_cut_strips": "Cuando abras este sobre, separa las tiras: recorta por las líneas discontinuas.",
        "manual_need_label_tape": (
            "Cinta adhesiva o pegamento para las etiquetas de los sobres (o escribe la letra en cada sobre)"
        ),
        "manual_print_box_title": "Imprime al 100 %",
        "manual_print_box_chrome": "Chrome: Más ajustes > Escala > Predeterminado",
        "manual_print_box_edge": "Edge: Más configuraciones > Escala > Tamaño real",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Ajuste de tamaño y gestión de páginas > Tamaño real",
        "citation_revealed_by": "Lo revela el enigma {code}",
        "accusation_title": "Formulario de acusación",
        "accusation_intro": (
            "Responded juntos a cada pregunta. Marcad una casilla por pregunta y escribid el documento que lo "
            "demuestra. Después contad vuestros puntos."
        ),
        "accusation_proof": "¿Qué documento lo demuestra?",
        "accusation_points": "{points} puntos",
        "accusation_detectives": "Detectives",
        "accusation_total": "Vuestros puntos: ______ de {total}",
        "labels_title": "Etiquetas de los sobres",
        "labels_intro": "Recorta cada etiqueta y pégala en su sobre.",
        "label_open_start": "Abrir al empezar",
        "label_open_after": "Abrir solo después del enigma {code}",
        "notes_title": "Notas del detective",
        "notes_intro": "Apunta lo que descubras. Usa un lápiz.",
        "notes_suspect": "Sospechoso",
        "notes_motive": "Móvil",
        "notes_opportunity": "Oportunidad",
        "notes_alibi": "Coartada",
        "notes_where": "¿Quién estaba dónde?",
        "notes_free": "Notas",
        "warning_title": "Aviso de spoilers",
        "hints_title": "Tarjetas de pistas",
        "hints_warning_text": (
            "Estas tarjetas te ayudan cuando te atascas. Lee solo una tarjeta cada vez y empieza siempre por la Pista "
            "1."
        ),
        "hints_how_to": (
            "Recorta cada tarjeta por las líneas discontinuas. Dóblala por la línea de puntos y rayas, con la parte "
            "impresa hacia fuera. El texto de detrás queda oculto hasta que des la vuelta a la tarjeta."
        ),
        "hints_companion": (
            "¿Tienes un móvil o un ordenador? La página Compañero de juego da las mismas pistas, una a una."
        ),
        "hint_label": "Pista {level}",
        "answer_label": "Respuesta",
        "hint_turn": "Dale la vuelta para leer",
        "solutions_title": "Soluciones",
        "solutions_warning_text": (
            "Este archivo contiene todas las respuestas y la historia completa. Léelo solo al final de la partida o "
            "para comprobar una respuesta."
        ),
        "solution_answer": "Respuesta",
        "solution_accepted": "También se acepta",
        "solution_steps": "Cómo se resuelve",
        "deduction_title": "La acusación",
        "exclusions_title": "¿Por qué no los demás?",
        "truth_title": "Toda la verdad",
        "reveal_title": "Cómo podíais saberlo",
        "epilogues_title": "Finales",
        "epilogue_threshold": "{percent} % de los puntos o más",
        "field_from": "De",
        "field_to": "Para",
        "field_cc": "CC",
        "field_date": "Fecha",
        "field_time": "Hora",
        "field_subject": "Asunto",
        "field_case_number": "Caso n.º",
        "field_officer": "Agente",
        "field_station": "Comisaría",
        "field_seat": "Asiento",
        "field_passenger": "Pasajero",
        "field_price": "Precio",
        "field_number": "N.º",
        "field_name": "Nombre",
        "field_role": "Profesión",
        "field_birth_date": "Nacimiento",
        "field_expires": "Válido hasta",
        "field_total": "Total",
        "field_reward": "Recompensa",
        "field_scale": "Escala",
        "field_legend": "Leyenda",
        "field_interviewer": "Entrevistador",
        "field_place": "Lugar",
        "field_issuer": "Expedido por",
        "field_form_number": "Formulario",
        "word_telegram": "Telegrama",
        "word_transcript": "Transcripción",
        "word_report": "Informe",
        "word_confidential": "Confidencial",
        "word_ticket": "Billete",
        "word_identity": "Documento de identidad",
        "word_receipt": "Recibo",
        "word_thanks": "Gracias",
        "manual_title": "Empieza aquí",
        "manual_checklist_title": "Lista de impresión",
        "manual_file": "Archivo",
        "manual_pages": "Páginas",
        "manual_print_column": "¿Imprimir?",
        "manual_print_yes": "Sí",
        "manual_print_optional": "Solo si jugáis sin móvil ni ordenador",
        "manual_print_companion_file": "No: ábrelo en un móvil o un ordenador",
        "manual_print_actual_size": (
            "Imprime al 100 % (tamaño real), a una cara, en papel {paper}. No uses «ajustar a la página»."
        ),
        "manual_print_bw": "Este juego está pensado para una impresora en blanco y negro.",
        "manual_print_color": "En color queda mejor, pero una impresora en blanco y negro también sirve.",
        "manual_print_skip_spoilers": (
            "No imprimas las pistas ni las soluciones si tenéis un móvil o un ordenador en la mesa: usad la página "
            "Compañero de juego."
        ),
        "manual_need_title": "Qué necesitas",
        "manual_need_envelopes": "{count} sobres",
        "manual_need_folders": "{count} carpetas o clips, uno para cada parte",
        "manual_need_pencils": "Lápices y una goma",
        "manual_need_paper": "Algo de papel para notas",
        "manual_need_scissors": "Tijeras",
        "manual_need_tape": "Cinta adhesiva o pegamento",
        "manual_need_mirror": "Un espejo pequeño (o una ventana con luz: apoya la hoja en ella y léela por detrás)",
        "manual_need_light": "Una ventana con luz o una lámpara, para mirar hojas a contraluz",
        "manual_setup_title": "Preparación",
        "manual_setup_split": "No leas el material del juego. Separa el montón por cada página que dice ALTO.",
        "manual_setup_outside": (
            "Las páginas anteriores a la primera página de ALTO quedan fuera de los sobres: {pages}."
        ),
        "manual_setup_outside_piles": (
            "Las páginas anteriores a la primera página de ALTO quedan sobre la mesa: {pages}."
        ),
        "manual_outside_cover": "la portada",
        "manual_outside_labels": "las etiquetas",
        "manual_outside_register": "el registro de respuestas",
        "manual_outside_notes": "las notas del detective",
        "list_separator": ", ",
        "list_two": "{first} y {last}",
        "list_many": "{items} y {last}",
        "manual_setup_envelopes": (
            "Mete cada parte en su propio sobre, con su página de ALTO encima. Pega la etiqueta correspondiente en "
            "cada sobre y ciérralo."
        ),
        "manual_setup_piles": "Deja cada parte boca abajo en su propio montón, con su página de ALTO encima.",
        "manual_setup_spoilers": "Guarda las pistas y las soluciones fuera de la vista hasta que las necesitéis.",
        "manual_play_title": "Cómo se juega",
        "manual_play_open_first": "Abrid el Sobre A. Leed esta introducción en voz alta:",
        "manual_play_solve": (
            "Leed los documentos y resolved los enigmas. El código de la esquina de una página (por ejemplo, A1) "
            "indica a qué enigma pertenece."
        ),
        "manual_play_check_register": (
            "Cuando tengáis una respuesta, buscadla en el registro de respuestas y leed el párrafo al que os envía."
        ),
        "manual_play_check_companion": "O escribid la respuesta en la página Compañero de juego.",
        "manual_play_next": (
            "Una respuesta correcta os dice cuándo abrir el siguiente sobre. Nunca abráis un sobre antes."
        ),
        "manual_play_accusation": "Al final, rellenad juntos el formulario de acusación.",
        "manual_hints_title": "Pistas y soluciones",
        "manual_hints_text": (
            "¿Atascados? Coged las tarjetas de pistas con el código de vuestro enigma y leed primero la Pista 1. Leed "
            "la siguiente solo si aún la necesitáis. La última tarjeta da la respuesta."
        ),
        "manual_hints_companion": "La página Compañero de juego muestra las mismas pistas, una a una.",
        "manual_solutions_text": "Las soluciones explican cada enigma y toda la historia. Leedlas al final.",
        "manual_scoring_title": "Acusación y puntuación",
        "manual_scoring_text": (
            "Cada pregunta del formulario de acusación da puntos, {total} en total. Contad vuestros puntos y buscad "
            "vuestro final en las soluciones:"
        ),
        "manual_rank_points": "Puntos",
        "manual_rank_ending": "Final",
        "manual_rank_range": "De {low} a {high}",
        "manual_host_title": "Guía del director de juego",
        "manual_host_intro": (
            "Tú diriges la partida y no juegas. Puedes leerlo todo antes de empezar. Planifica el tiempo con esta "
            "tabla (minutos desde el inicio):"
        ),
        "manual_host_stage": "Sobre",
        "manual_host_puzzles": "Enigmas",
        "manual_host_minutes": "Minutos",
        "manual_host_by": "Acabado en el minuto",
        "manual_host_stuck": "Si un grupo lleva 10 minutos atascado, dale la siguiente pista.",
        "manual_host_answers": (
            "Comprueba cada respuesta con el registro de respuestas o la página Compañero de juego antes de entregar "
            "el siguiente sobre."
        ),
        "manual_personal_title": "Para esta partida",
        "manual_host_name": "Anfitrión: {name}",
        "manual_player_names": "Detectives: {names}",
    },
    "ca": {
        "envelope_label": "Sobre {stage}",
        "continued": "continuació",
        "materials_title": "Material del joc",
        "file_manual": "1 - COMENÇA AQUÍ (manual)",
        "file_materials": "2 - IMPRIMEIX AIXÒ (material del joc)",
        "file_hints": "3 - Pistes",
        "file_solutions": "4 - Solucions",
        "file_companion": "Company de joc",
        "folder_spoilers": "NOMÉS AMFITRIÓ - espòilers",
        "file_export_warnings": "0 - LLEGEIX AIXÒ PRIMER (avisos)",
        "export_warnings_title": "Llegeix això abans de jugar",
        "export_warnings_intro": (
            "Mystery Forge prova cada joc amb comprovacions automàtiques i amb jugadors de prova d'IA. Algunes "
            "proves d'aquest joc no s'han superat. El més probable és que el joc funcioni, però les parts de sota "
            "poden ser confuses, massa difícils o incorrectes."
        ),
        "export_warnings_fix": (
            "Per corregir-les, fes doble clic a Start Mystery Forge, escriu 4 i demana a la IA que corregeixi els "
            "avisos d'aquest joc."
        ),
        "export_warning_puzzle": "Enigma {code}: {problems}",
        "export_warning_accusation": "Formulari d'acusació: {problems}",
        "export_warning_checks_failing": "algunes comprovacions automàtiques han fallat.",
        "export_warning_checks_stale": "les comprovacions automàtiques no s'han repetit després de l'últim canvi.",
        "export_warning_panel_stale": "els jugadors de prova no l'han provat després de l'últim canvi.",
        "export_warning_ambiguous": "els jugadors de prova han trobat més d'una resposta possible.",
        "export_warning_gold_suspect": "els jugadors de prova creuen que la resposta esperada pot ser incorrecta.",
        "export_warning_too_hard": "els jugadors de prova no l'han pogut resoldre.",
        "export_warning_guessable": "els jugadors de prova han pogut endevinar la resposta sense les pistes.",
        "export_warning_incomplete": "els jugadors de prova creuen que falta alguna cosa que necessiten.",
        "export_warning_trivial": "als jugadors de prova els ha semblat massa fàcil.",
        "export_warning_insufficient_solvers": "molt pocs jugadors de prova han acabat la prova.",
        "export_warning_puzzles_not_needed": "els jugadors de prova l'han pogut respondre sense resoldre els enigmes.",
        "made_with": "Fet amb Mystery Forge",
        "page_label": "Pàgina {number} de {count}",
        "copy_label": "Còpia {number} de {count}",
        "puzzle_badge": "Enigma",
        "print_cut": "Retalla per la línia discontínua.",
        "print_fold": "Doblega per la línia de punts i ratlles.",
        "cover_kicker": "Un misteri per imprimir",
        "cover_players": "{count} jugadors",
        "cover_players_solo": "1 jugador",
        "accusation_intro_solo": (
            "Respon cada pregunta. "
            "Marca una casella a cada pregunta i anota el document que ho demostra. Després compta els teus punts."
        ),
        "manual_play_accusation_solo": "Al final, omple el formulari d'acusació.",
        "cover_duration": "Uns {minutes} minuts",
        "cover_detectives": "Detectius: {names}",
        "cover_do_not_read": "No llegeixis per avançat. Obre cada sobre només quan el joc t'ho digui.",
        "stop": "ATURA'T",
        "stage_open_at_start": "Obre aquest sobre en començar la partida.",
        "stage_open_when": (
            "No obris aquest sobre encara. Obre'l només quan la comprovació de respostes t'ho digui, després de "
            "resoldre l'enigma {code}."
        ),
        "stage_turn_page": "Quan obris el sobre, gira aquesta pàgina i llegeix el text en veu alta.",
        "stage_read_aloud": "Llegiu en veu alta",
        "register_title": "Registre de respostes",
        "register_answer": "Resposta",
        "register_paragraph": "Paràgraf",
        "results_title": "Paràgrafs de resultat",
        "results_intro": "Llegeix només el paràgraf on t'envia el registre de respostes.",
        "register_wrong": "No passa res. Torna-ho a provar.",
        "register_intro": (
            "Escriu la teva resposta en majúscules, sense espais i sense accents (la Ç s'escriu C), i busca-la "
            "en aquesta llista. Primer hi ha els números i després les paraules de la A a la Z. Llegeix el "
            "paràgraf de resultat amb el número que té al costat. Si la teva resposta no és a la llista, no és "
            "correcta."
        ),
        "register_correct_open": "Correcte! Obre ara el {envelope}.",
        "register_correct_keep": "Correcte! Apunta aquesta resposta: un enigma posterior la necessita.",
        "register_correct_accusation": "Correcte! Era l'últim enigma: passeu a l'acusació.",
        "register_correct_notes": "Correcte! Apunta-ho a les teves notes.",
        "register_story_card": "Abans de continuar, llegeix la targeta d'història {number} al final del {envelope}.",
        "story_cards_title": "Targetes d'història",
        "story_cards_intro": (
            "Llegeix una targeta només quan el registre de respostes t'hi enviï. Gira el full per llegir-la."
        ),
        "print_cut_strips": "Quan obris aquest sobre, separa les tires: retalla per les línies discontínues.",
        "manual_need_label_tape": (
            "Cinta adhesiva o cola per a les etiquetes dels sobres (o escriu la lletra a cada sobre)"
        ),
        "manual_print_box_title": "Imprimeix al 100 %",
        "manual_print_box_chrome": "Chrome: Més opcions de configuració > Escala > Predeterminada",
        "manual_print_box_edge": "Edge: Més opcions de configuració > Escala > Mida real",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Ajuste de tamaño y gestión de páginas > Tamaño real",
        "citation_revealed_by": "Ho revela l'enigma {code}",
        "accusation_title": "Formulari d'acusació",
        "accusation_intro": (
            "Responeu junts cada pregunta. Marqueu una casella per pregunta i escriviu el document que ho demostra. "
            "Després compteu els punts."
        ),
        "accusation_proof": "Quin document ho demostra?",
        "accusation_points": "{points} punts",
        "accusation_detectives": "Detectius",
        "accusation_total": "Els vostres punts: ______ de {total}",
        "labels_title": "Etiquetes dels sobres",
        "labels_intro": "Retalla cada etiqueta i enganxa-la al seu sobre.",
        "label_open_start": "Obrir en començar",
        "label_open_after": "Obrir només després de l'enigma {code}",
        "notes_title": "Notes del detectiu",
        "notes_intro": "Apunta el que descobreixis. Fes servir un llapis.",
        "notes_suspect": "Sospitós",
        "notes_motive": "Mòbil",
        "notes_opportunity": "Oportunitat",
        "notes_alibi": "Coartada",
        "notes_where": "Qui era on?",
        "notes_free": "Notes",
        "warning_title": "Avís d'espòilers",
        "hints_title": "Targetes de pistes",
        "hints_warning_text": (
            "Aquestes targetes t'ajuden quan t'encalles. Llegeix només una targeta cada cop i comença sempre per la "
            "Pista 1."
        ),
        "hints_how_to": (
            "Retalla cada targeta per les línies discontínues. Doblega-la per la línia de punts i ratlles, amb la part "
            "impresa cap a fora. El text del darrere queda amagat fins que gires la targeta."
        ),
        "hints_companion": (
            "Tens un mòbil o un ordinador? La pàgina Company de joc dona les mateixes pistes, una a una."
        ),
        "hint_label": "Pista {level}",
        "answer_label": "Resposta",
        "hint_turn": "Gira-la per llegir",
        "solutions_title": "Solucions",
        "solutions_warning_text": (
            "Aquest fitxer conté totes les respostes i la història completa. Llegeix-lo només al final de la partida o "
            "per comprovar una resposta."
        ),
        "solution_answer": "Resposta",
        "solution_accepted": "També s'accepta",
        "solution_steps": "Com es resol",
        "deduction_title": "L'acusació",
        "exclusions_title": "Per què no els altres?",
        "truth_title": "Tota la veritat",
        "reveal_title": "Com ho podíeu saber",
        "epilogues_title": "Finals",
        "epilogue_threshold": "{percent} % dels punts o més",
        "field_from": "De",
        "field_to": "Per a",
        "field_cc": "CC",
        "field_date": "Data",
        "field_time": "Hora",
        "field_subject": "Assumpte",
        "field_case_number": "Cas núm.",
        "field_officer": "Agent",
        "field_station": "Comissaria",
        "field_seat": "Seient",
        "field_passenger": "Passatger",
        "field_price": "Preu",
        "field_number": "Núm.",
        "field_name": "Nom",
        "field_role": "Professió",
        "field_birth_date": "Naixement",
        "field_expires": "Vàlid fins a",
        "field_total": "Total",
        "field_reward": "Recompensa",
        "field_scale": "Escala",
        "field_legend": "Llegenda",
        "field_interviewer": "Entrevistador",
        "field_place": "Lloc",
        "field_issuer": "Expedit per",
        "field_form_number": "Formulari",
        "word_telegram": "Telegrama",
        "word_transcript": "Transcripció",
        "word_report": "Informe",
        "word_confidential": "Confidencial",
        "word_ticket": "Bitllet",
        "word_identity": "Document d'identitat",
        "word_receipt": "Rebut",
        "word_thanks": "Gràcies",
        "manual_title": "Comença aquí",
        "manual_checklist_title": "Llista d'impressió",
        "manual_file": "Fitxer",
        "manual_pages": "Pàgines",
        "manual_print_column": "Imprimir?",
        "manual_print_yes": "Sí",
        "manual_print_optional": "Només si jugueu sense mòbil ni ordinador",
        "manual_print_companion_file": "No: obre'l en un mòbil o un ordinador",
        "manual_print_actual_size": (
            "Imprimeix al 100 % (mida real), a una cara, en paper {paper}. No facis servir «ajusta a la pàgina»."
        ),
        "manual_print_bw": "Aquest joc està pensat per a una impressora en blanc i negre.",
        "manual_print_color": "En color queda millor, però una impressora en blanc i negre també serveix.",
        "manual_print_skip_spoilers": (
            "No imprimeixis les pistes ni les solucions si teniu un mòbil o un ordinador a la taula: feu servir la "
            "pàgina Company de joc."
        ),
        "manual_need_title": "Què necessites",
        "manual_need_envelopes": "{count} sobres",
        "manual_need_folders": "{count} carpetes o clips, un per a cada part",
        "manual_need_pencils": "Llapis i una goma",
        "manual_need_paper": "Una mica de paper per a notes",
        "manual_need_scissors": "Tisores",
        "manual_need_tape": "Cinta adhesiva o cola",
        "manual_need_mirror": "Un mirall petit (o una finestra amb llum: recolza-hi el full i llegeix-lo per darrere)",
        "manual_need_light": "Una finestra amb llum o un llum, per mirar fulls a contrallum",
        "manual_setup_title": "Preparació",
        "manual_setup_split": "No llegeixis el material del joc. Separa la pila per cada pàgina que diu ATURA'T.",
        "manual_setup_outside": "Les pàgines anteriors a la primera pàgina d'ATURA'T queden fora dels sobres: {pages}.",
        "manual_setup_outside_piles": (
            "Les pàgines anteriors a la primera pàgina d'ATURA'T queden sobre la taula: {pages}."
        ),
        "manual_outside_cover": "la portada",
        "manual_outside_labels": "les etiquetes",
        "manual_outside_register": "el registre de respostes",
        "manual_outside_notes": "les notes del detectiu",
        "list_separator": ", ",
        "list_two": "{first} i {last}",
        "list_many": "{items} i {last}",
        "manual_setup_envelopes": (
            "Posa cada part en el seu sobre, amb la seva pàgina d'ATURA'T a sobre. Enganxa l'etiqueta corresponent a "
            "cada sobre i tanca'l."
        ),
        "manual_setup_piles": "Deixa cada part cap per avall en la seva pila, amb la seva pàgina d'ATURA'T a sobre.",
        "manual_setup_spoilers": "Guarda les pistes i les solucions fora de la vista fins que les necessiteu.",
        "manual_play_title": "Com es juga",
        "manual_play_open_first": "Obriu el Sobre A. Llegiu aquesta introducció en veu alta:",
        "manual_play_solve": (
            "Llegiu els documents i resoleu els enigmes. El codi de la cantonada d'una pàgina (per exemple, A1) indica "
            "a quin enigma pertany."
        ),
        "manual_play_check_register": (
            "Quan tingueu una resposta, busqueu-la al registre de respostes i llegiu el paràgraf on us envia."
        ),
        "manual_play_check_companion": "O escriviu la resposta a la pàgina Company de joc.",
        "manual_play_next": "Una resposta correcta us diu quan obrir el sobre següent. No obriu mai un sobre abans.",
        "manual_play_accusation": "Al final, ompliu junts el formulari d'acusació.",
        "manual_hints_title": "Pistes i solucions",
        "manual_hints_text": (
            "Encallats? Agafeu les targetes de pistes amb el codi del vostre enigma i llegiu primer la Pista 1. Llegiu "
            "la següent només si encara la necessiteu. L'última targeta dona la resposta."
        ),
        "manual_hints_companion": "La pàgina Company de joc mostra les mateixes pistes, una a una.",
        "manual_solutions_text": "Les solucions expliquen cada enigma i tota la història. Llegiu-les al final.",
        "manual_scoring_title": "Acusació i puntuació",
        "manual_scoring_text": (
            "Cada pregunta del formulari d'acusació dona punts, {total} en total. Compteu els punts i busqueu el "
            "vostre final a les solucions:"
        ),
        "manual_rank_points": "Punts",
        "manual_rank_ending": "Final",
        "manual_rank_range": "De {low} a {high}",
        "manual_host_title": "Guia del director de joc",
        "manual_host_intro": (
            "Tu dirigeixes la partida i no hi jugues. Pots llegir-ho tot abans de començar. Planifica el temps amb "
            "aquesta taula (minuts des de l'inici):"
        ),
        "manual_host_stage": "Sobre",
        "manual_host_puzzles": "Enigmes",
        "manual_host_minutes": "Minuts",
        "manual_host_by": "Acabat al minut",
        "manual_host_stuck": "Si un grup fa 10 minuts que està encallat, dona-li la pista següent.",
        "manual_host_answers": (
            "Comprova cada resposta amb el registre de respostes o la pàgina Company de joc abans de donar el sobre "
            "següent."
        ),
        "manual_personal_title": "Per a aquesta partida",
        "manual_host_name": "Amfitrió: {name}",
        "manual_player_names": "Detectius: {names}",
    },
    "fr": {
        "envelope_label": "Enveloppe {stage}",
        "continued": "suite",
        "materials_title": "Matériel de jeu",
        "file_manual": "1 - COMMENCEZ ICI (manuel)",
        "file_materials": "2 - À IMPRIMER (matériel de jeu)",
        "file_hints": "3 - Indices",
        "file_solutions": "4 - Solutions",
        "file_companion": "Compagnon de jeu",
        "folder_spoilers": "HÔTE UNIQUEMENT - révélations",
        "file_export_warnings": "0 - À LIRE D'ABORD (avertissements)",
        "export_warnings_title": "Lisez ceci avant de jouer",
        "export_warnings_intro": (
            "Mystery Forge teste chaque jeu avec des contrôles automatiques et avec des joueurs de test IA. Certains "
            "tests de ce jeu n'ont pas réussi. Le jeu reste sans doute jouable, mais les parties ci-dessous peuvent "
            "être confuses, trop difficiles ou fausses."
        ),
        "export_warnings_fix": (
            "Pour les corriger, double-cliquez sur Start Mystery Forge, tapez 4 et demandez à l'IA de corriger les "
            "avertissements de ce jeu."
        ),
        "export_warning_puzzle": "Énigme {code} : {problems}",
        "export_warning_accusation": "Formulaire d'accusation : {problems}",
        "export_warning_checks_failing": "certains contrôles automatiques ont échoué.",
        "export_warning_checks_stale": (
            "les contrôles automatiques n'ont pas été refaits après la dernière modification."
        ),
        "export_warning_panel_stale": "les joueurs de test ne l'ont pas essayé après la dernière modification.",
        "export_warning_ambiguous": "les joueurs de test ont trouvé plus d'une réponse possible.",
        "export_warning_gold_suspect": "les joueurs de test pensent que la réponse attendue est peut-être fausse.",
        "export_warning_too_hard": "les joueurs de test n'ont pas pu la résoudre.",
        "export_warning_guessable": "les joueurs de test ont pu deviner la réponse sans les indices.",
        "export_warning_incomplete": "les joueurs de test pensent qu'il manque quelque chose dont ils ont besoin.",
        "export_warning_trivial": "les joueurs de test l'ont trouvée trop facile.",
        "export_warning_insufficient_solvers": "trop peu de joueurs de test ont terminé le test.",
        "export_warning_puzzles_not_needed": "les joueurs de test ont pu y répondre sans résoudre les énigmes.",
        "made_with": "Créé avec Mystery Forge",
        "page_label": "Page {number} sur {count}",
        "copy_label": "Exemplaire {number} sur {count}",
        "puzzle_badge": "Énigme",
        "print_cut": "Découpez le long de la ligne pointillée.",
        "print_fold": "Pliez le long de la ligne en tirets et points.",
        "cover_kicker": "Un mystère à imprimer",
        "cover_players": "{count} joueurs",
        "cover_players_solo": "1 joueur",
        "accusation_intro_solo": (
            "Réponds à chaque question. "
            "Coche une case par question et note le document qui le prouve. Puis compte tes points."
        ),
        "manual_play_accusation_solo": "À la fin, remplis le formulaire d'accusation.",
        "cover_duration": "Environ {minutes} minutes",
        "cover_detectives": "Détectives : {names}",
        "cover_do_not_read": "Ne lisez pas à l'avance. Ouvrez chaque enveloppe seulement quand le jeu vous le dit.",
        "stop": "STOP",
        "stage_open_at_start": "Ouvrez cette enveloppe au début de la partie.",
        "stage_open_when": (
            "N'ouvrez pas encore cette enveloppe. Ouvrez-la seulement quand la vérification des réponses vous le dit, "
            "après avoir résolu l'énigme {code}."
        ),
        "stage_turn_page": "Après avoir ouvert l'enveloppe, retournez cette page et lisez le texte à voix haute.",
        "stage_read_aloud": "À lire à voix haute",
        "register_title": "Registre des réponses",
        "register_answer": "Réponse",
        "register_paragraph": "Paragraphe",
        "results_title": "Paragraphes de résultat",
        "results_intro": "Lisez seulement le paragraphe indiqué par le registre des réponses.",
        "register_wrong": "Il ne se passe rien. Essayez encore.",
        "register_intro": (
            "Écrivez votre réponse en majuscules, sans espaces et sans accents (le Ç s'écrit C), puis "
            "cherchez-la dans cette liste. D'abord les nombres, puis les mots de A à Z. Lisez le paragraphe de "
            "résultat dont le numéro est à côté. Si votre réponse n'est pas dans la liste, elle n'est pas "
            "correcte."
        ),
        "register_correct_open": "Bravo ! Ouvrez maintenant l'{envelope}.",
        "register_correct_keep": "Bravo ! Notez cette réponse : une énigme plus loin en a besoin.",
        "register_correct_accusation": "Bravo ! C'était la dernière énigme : passez à l'accusation.",
        "register_correct_notes": "Bravo ! Notez-la dans vos notes.",
        "register_story_card": "Avant de continuer, lisez la carte d'histoire {number} à la fin de l'{envelope}.",
        "story_cards_title": "Cartes d'histoire",
        "story_cards_intro": (
            "Ne lisez une carte que lorsque le registre des réponses vous y envoie. Retournez la page pour la lire."
        ),
        "print_cut_strips": (
            "Quand vous ouvrez cette enveloppe, séparez les bandes : découpez le long des lignes pointillées."
        ),
        "manual_need_label_tape": (
            "Du ruban adhésif ou de la colle pour les étiquettes des enveloppes (ou écrivez la lettre sur chaque "
            "enveloppe)"
        ),
        "manual_print_box_title": "Imprimez à 100 %",
        "manual_print_box_chrome": "Chrome : Plus de paramètres > Mise à l'échelle > Par défaut",
        "manual_print_box_edge": "Edge : Plus de paramètres > Mise à l'échelle > Taille réelle",
        "manual_print_box_acrobat": "Adobe Acrobat Reader : Dimensionnement et gestion des pages > Taille réelle",
        "citation_revealed_by": "Révélé par l'énigme {code}",
        "accusation_title": "Formulaire d'accusation",
        "accusation_intro": (
            "Répondez ensemble à chaque question. Cochez une case par question et notez le document qui le prouve. "
            "Comptez ensuite vos points."
        ),
        "accusation_proof": "Quel document le prouve ?",
        "accusation_points": "{points} points",
        "accusation_detectives": "Détectives",
        "accusation_total": "Vos points : ______ sur {total}",
        "labels_title": "Étiquettes des enveloppes",
        "labels_intro": "Découpez chaque étiquette et collez-la sur son enveloppe.",
        "label_open_start": "À ouvrir au début",
        "label_open_after": "À ouvrir seulement après l'énigme {code}",
        "notes_title": "Notes du détective",
        "notes_intro": "Notez ce que vous découvrez. Utilisez un crayon.",
        "notes_suspect": "Suspect",
        "notes_motive": "Mobile",
        "notes_opportunity": "Occasion",
        "notes_alibi": "Alibi",
        "notes_where": "Qui était où ?",
        "notes_free": "Notes",
        "warning_title": "Attention, révélations",
        "hints_title": "Cartes d'indices",
        "hints_warning_text": (
            "Ces cartes vous aident quand vous êtes bloqués. Lisez une seule carte à la fois, et commencez toujours "
            "par l'Indice 1."
        ),
        "hints_how_to": (
            "Découpez chaque carte le long des lignes pointillées. Pliez-la le long de la ligne en tirets et points, "
            "face imprimée vers l'extérieur. Le texte du dos reste caché jusqu'à ce que vous retourniez la carte."
        ),
        "hints_companion": (
            "Vous avez un téléphone ou un ordinateur ? La page Compagnon de jeu donne les mêmes indices, un par un."
        ),
        "hint_label": "Indice {level}",
        "answer_label": "Réponse",
        "hint_turn": "Retournez pour lire",
        "solutions_title": "Solutions",
        "solutions_warning_text": (
            "Ce fichier contient toutes les réponses et toute l'histoire. Lisez-le seulement à la fin de la partie, ou "
            "pour vérifier une réponse."
        ),
        "solution_answer": "Réponse",
        "solution_accepted": "Aussi accepté",
        "solution_steps": "Comment la résoudre",
        "deduction_title": "L'accusation",
        "exclusions_title": "Pourquoi pas les autres ?",
        "truth_title": "Toute la vérité",
        "reveal_title": "Comment vous auriez pu le savoir",
        "epilogues_title": "Fins",
        "epilogue_threshold": "{percent} % des points ou plus",
        "field_from": "De",
        "field_to": "À",
        "field_cc": "Cc",
        "field_date": "Date",
        "field_time": "Heure",
        "field_subject": "Objet",
        "field_case_number": "Affaire n°",
        "field_officer": "Agent",
        "field_station": "Commissariat",
        "field_seat": "Place",
        "field_passenger": "Passager",
        "field_price": "Prix",
        "field_number": "N°",
        "field_name": "Nom",
        "field_role": "Profession",
        "field_birth_date": "Né le",
        "field_expires": "Valable jusqu'au",
        "field_total": "Total",
        "field_reward": "Récompense",
        "field_scale": "Échelle",
        "field_legend": "Légende",
        "field_interviewer": "Enquêteur",
        "field_place": "Lieu",
        "field_issuer": "Délivré par",
        "field_form_number": "Formulaire",
        "word_telegram": "Télégramme",
        "word_transcript": "Transcription",
        "word_report": "Rapport",
        "word_confidential": "Confidentiel",
        "word_ticket": "Billet",
        "word_identity": "Carte d'identité",
        "word_receipt": "Reçu",
        "word_thanks": "Merci",
        "manual_title": "Commencez ici",
        "manual_checklist_title": "Liste d'impression",
        "manual_file": "Fichier",
        "manual_pages": "Pages",
        "manual_print_column": "Imprimer ?",
        "manual_print_yes": "Oui",
        "manual_print_optional": "Seulement si vous jouez sans téléphone ni ordinateur",
        "manual_print_companion_file": "Non : ouvrez-le sur un téléphone ou un ordinateur",
        "manual_print_actual_size": (
            "Imprimez à 100 % (taille réelle), en recto seul, sur papier {paper}. N'utilisez pas « ajuster à la page »."
        ),
        "manual_print_bw": "Ce jeu est prévu pour une imprimante noir et blanc.",
        "manual_print_color": "La couleur est plus belle, mais une imprimante noir et blanc convient aussi.",
        "manual_print_skip_spoilers": (
            "N'imprimez pas les indices ni les solutions si vous avez un téléphone ou un ordinateur à table : utilisez "
            "plutôt la page Compagnon de jeu."
        ),
        "manual_need_title": "Ce qu'il vous faut",
        "manual_need_envelopes": "{count} enveloppes",
        "manual_need_folders": "{count} chemises ou trombones, un par partie",
        "manual_need_pencils": "Des crayons et une gomme",
        "manual_need_paper": "Du papier brouillon",
        "manual_need_scissors": "Des ciseaux",
        "manual_need_tape": "Du ruban adhésif ou de la colle",
        "manual_need_mirror": (
            "Un petit miroir (ou une fenêtre lumineuse : posez la page contre elle et lisez-la par l'arrière)"
        ),
        "manual_need_light": "Une fenêtre lumineuse ou une lampe, pour regarder des pages à contre-jour",
        "manual_setup_title": "Préparation",
        "manual_setup_split": "Ne lisez pas le matériel du jeu. Séparez la pile à chaque page marquée STOP.",
        "manual_setup_outside": "Les pages avant la première page STOP restent hors des enveloppes : {pages}.",
        "manual_setup_outside_piles": "Les pages avant la première page STOP restent sur la table : {pages}.",
        "manual_outside_cover": "la couverture",
        "manual_outside_labels": "les étiquettes",
        "manual_outside_register": "le registre des réponses",
        "manual_outside_notes": "les notes du détective",
        "list_separator": ", ",
        "list_two": "{first} et {last}",
        "list_many": "{items} et {last}",
        "manual_setup_envelopes": (
            "Mettez chaque partie dans sa propre enveloppe, sa page STOP au-dessus. Collez l'étiquette correspondante "
            "sur chaque enveloppe et fermez-la."
        ),
        "manual_setup_piles": "Posez chaque partie face cachée en pile séparée, sa page STOP au-dessus.",
        "manual_setup_spoilers": "Gardez les indices et les solutions hors de vue jusqu'à ce que vous en ayez besoin.",
        "manual_play_title": "Comment jouer",
        "manual_play_open_first": "Ouvrez l'Enveloppe A. Lisez cette introduction à voix haute :",
        "manual_play_solve": (
            "Lisez les documents et résolvez les énigmes. Le code dans le coin d'une page (par exemple A1) indique à "
            "quelle énigme elle appartient."
        ),
        "manual_play_check_register": (
            "Quand vous avez une réponse, cherchez-la dans le registre des réponses et lisez le paragraphe indiqué."
        ),
        "manual_play_check_companion": "Ou tapez la réponse sur la page Compagnon de jeu.",
        "manual_play_next": (
            "Une bonne réponse vous dit quand ouvrir l'enveloppe suivante. N'ouvrez jamais une enveloppe avant."
        ),
        "manual_play_accusation": "À la fin, remplissez ensemble le formulaire d'accusation.",
        "manual_hints_title": "Indices et solutions",
        "manual_hints_text": (
            "Bloqués ? Prenez les cartes d'indices avec le code de votre énigme et lisez d'abord l'Indice 1. Lisez la "
            "carte suivante seulement si vous en avez encore besoin. La dernière carte donne la réponse."
        ),
        "manual_hints_companion": "La page Compagnon de jeu montre les mêmes indices, un par un.",
        "manual_solutions_text": "Les solutions expliquent chaque énigme et toute l'histoire. Lisez-les à la fin.",
        "manual_scoring_title": "Accusation et score",
        "manual_scoring_text": (
            "Chaque question du formulaire d'accusation rapporte des points, {total} en tout. Comptez vos points et "
            "trouvez votre fin dans les solutions :"
        ),
        "manual_rank_points": "Points",
        "manual_rank_ending": "Fin",
        "manual_rank_range": "De {low} à {high}",
        "manual_host_title": "Guide du maître du jeu",
        "manual_host_intro": (
            "Vous menez la partie et vous ne jouez pas. Vous pouvez tout lire avant le début. Prévoyez votre temps "
            "avec ce tableau (minutes depuis le début) :"
        ),
        "manual_host_stage": "Enveloppe",
        "manual_host_puzzles": "Énigmes",
        "manual_host_minutes": "Minutes",
        "manual_host_by": "Fini à la minute",
        "manual_host_stuck": "Si un groupe est bloqué depuis 10 minutes, donnez-lui l'indice suivant.",
        "manual_host_answers": (
            "Vérifiez chaque réponse avec le registre des réponses ou la page Compagnon de jeu avant de donner "
            "l'enveloppe suivante."
        ),
        "manual_personal_title": "Pour cette partie",
        "manual_host_name": "Votre hôte : {name}",
        "manual_player_names": "Détectives : {names}",
    },
    "de": {
        "envelope_label": "Umschlag {stage}",
        "continued": "Fortsetzung",
        "materials_title": "Spielmaterial",
        "file_manual": "1 - HIER BEGINNEN (Anleitung)",
        "file_materials": "2 - AUSDRUCKEN (Spielmaterial)",
        "file_hints": "3 - Hinweise",
        "file_solutions": "4 - Lösungen",
        "file_companion": "Spielbegleiter",
        "folder_spoilers": "NUR GASTGEBER - Spoiler",
        "file_export_warnings": "0 - ZUERST LESEN (Warnungen)",
        "export_warnings_title": "Lies das vor dem Spiel",
        "export_warnings_intro": (
            "Mystery Forge testet jedes Spiel mit automatischen Prüfungen und mit KI-Testspielern. Einige Tests "
            "dieses Spiels sind nicht bestanden. Das Spiel ist wahrscheinlich trotzdem spielbar, aber die Teile "
            "unten können unklar, zu schwer oder falsch sein."
        ),
        "export_warnings_fix": (
            "Zum Beheben: Doppelklicke auf Start Mystery Forge, tippe 4 und bitte die KI, die Warnungen dieses "
            "Spiels zu beheben."
        ),
        "export_warning_puzzle": "Rätsel {code}: {problems}",
        "export_warning_accusation": "Anklageformular: {problems}",
        "export_warning_checks_failing": "einige automatische Prüfungen sind fehlgeschlagen.",
        "export_warning_checks_stale": "die automatischen Prüfungen liefen nach der letzten Änderung nicht erneut.",
        "export_warning_panel_stale": "die Testspieler haben es nach der letzten Änderung nicht erneut versucht.",
        "export_warning_ambiguous": "die Testspieler fanden mehr als eine passende Antwort.",
        "export_warning_gold_suspect": "die Testspieler halten die erwartete Antwort für möglicherweise falsch.",
        "export_warning_too_hard": "die Testspieler konnten es nicht lösen.",
        "export_warning_guessable": "die Testspieler konnten die Antwort ohne die Hinweise erraten.",
        "export_warning_incomplete": "die Testspieler glauben, dass etwas fehlt, das sie brauchen.",
        "export_warning_trivial": "die Testspieler fanden es zu leicht.",
        "export_warning_insufficient_solvers": "zu wenige Testspieler haben den Test beendet.",
        "export_warning_puzzles_not_needed": "die Testspieler konnten es beantworten, ohne die Rätsel zu lösen.",
        "made_with": "Erstellt mit Mystery Forge",
        "page_label": "Seite {number} von {count}",
        "copy_label": "Exemplar {number} von {count}",
        "puzzle_badge": "Rätsel",
        "print_cut": "Entlang der gestrichelten Linie ausschneiden.",
        "print_fold": "Entlang der Strich-Punkt-Linie falten.",
        "cover_kicker": "Ein Krimi zum Ausdrucken",
        "cover_players": "{count} Spieler",
        "cover_players_solo": "1 Spieler",
        "accusation_intro_solo": (
            "Beantworte jede Frage. "
            "Kreuze bei jeder Frage ein Kästchen an und nenne das Dokument, das es beweist. Zähle dann deine Punkte."
        ),
        "manual_play_accusation_solo": "Fülle am Ende das Anklageformular aus.",
        "cover_duration": "Etwa {minutes} Minuten",
        "cover_detectives": "Detektive: {names}",
        "cover_do_not_read": "Nicht vorauslesen. Öffnet jeden Umschlag erst, wenn das Spiel es sagt.",
        "stop": "STOPP",
        "stage_open_at_start": "Öffnet diesen Umschlag zu Beginn des Spiels.",
        "stage_open_when": (
            "Öffnet diesen Umschlag noch nicht. Öffnet ihn erst, wenn die Antwortkontrolle es sagt, nachdem ihr Rätsel "
            "{code} gelöst habt."
        ),
        "stage_turn_page": "Wenn ihr den Umschlag geöffnet habt, dreht diese Seite um und lest den Text laut vor.",
        "stage_read_aloud": "Laut vorlesen",
        "register_title": "Antwortregister",
        "register_answer": "Antwort",
        "register_paragraph": "Abschnitt",
        "results_title": "Ergebnisabschnitte",
        "results_intro": "Lest nur den Abschnitt, zu dem euch das Antwortregister schickt.",
        "register_wrong": "Nichts passiert. Versucht es noch einmal.",
        "register_intro": (
            "Schreibt eure Antwort in Großbuchstaben, ohne Leerzeichen und ohne Akzente (A statt Ä, SS statt ß), "
            "und sucht sie dann in dieser Liste. Zuerst kommen die Zahlen, dann die Wörter von A bis Z. Lest den "
            "Ergebnisabschnitt mit der Nummer daneben. Steht eure Antwort nicht in der Liste, ist sie falsch."
        ),
        "register_correct_open": "Richtig! Öffnet jetzt {envelope}.",
        "register_correct_keep": "Richtig! Schreibt diese Antwort auf: Ein späteres Rätsel braucht sie.",
        "register_correct_accusation": "Richtig! Das war das letzte Rätsel: Weiter zur Anklage.",
        "register_correct_notes": "Richtig! Schreibt sie in eure Notizen.",
        "register_story_card": "Bevor ihr weitermacht, lest die Story-Karte {number} am Ende von {envelope}.",
        "story_cards_title": "Story-Karten",
        "story_cards_intro": (
            "Lest eine Karte erst, wenn das Antwortregister euch zu ihr schickt. Dreht die Seite um, um sie zu lesen."
        ),
        "print_cut_strips": (
            "Wenn ihr diesen Umschlag öffnet, schneidet die Streifen entlang der gestrichelten Linien auseinander."
        ),
        "manual_need_label_tape": (
            "Klebeband oder Kleber für die Umschlag-Etiketten (oder schreibt den Buchstaben auf jeden Umschlag)"
        ),
        "manual_print_box_title": "In 100 % drucken",
        "manual_print_box_chrome": "Chrome: Weitere Einstellungen > Skalieren > Standard",
        "manual_print_box_edge": "Edge: Weitere Einstellungen > Skalierung > Tatsächliche Größe",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Seitengröße und -handhabung > Tatsächliche Größe",
        "citation_revealed_by": "Aufgedeckt durch Rätsel {code}",
        "accusation_title": "Anklageformular",
        "accusation_intro": (
            "Beantwortet jede Frage gemeinsam. Kreuzt pro Frage ein Kästchen an und nennt das Dokument, das es "
            "beweist. Zählt dann eure Punkte."
        ),
        "accusation_proof": "Welches Dokument beweist es?",
        "accusation_points": "{points} Punkte",
        "accusation_detectives": "Detektive",
        "accusation_total": "Eure Punkte: ______ von {total}",
        "labels_title": "Umschlag-Etiketten",
        "labels_intro": "Schneidet jedes Etikett aus und klebt es auf seinen Umschlag.",
        "label_open_start": "Zu Beginn öffnen",
        "label_open_after": "Erst nach Rätsel {code} öffnen",
        "notes_title": "Ermittlungsnotizen",
        "notes_intro": "Schreibt auf, was ihr herausfindet. Benutzt einen Bleistift.",
        "notes_suspect": "Verdächtige Person",
        "notes_motive": "Motiv",
        "notes_opportunity": "Gelegenheit",
        "notes_alibi": "Alibi",
        "notes_where": "Wer war wo?",
        "notes_free": "Notizen",
        "warning_title": "Spoiler-Warnung",
        "hints_title": "Hinweiskarten",
        "hints_warning_text": (
            "Diese Karten helfen, wenn ihr nicht weiterkommt. Lest immer nur eine Karte und beginnt immer mit Hinweis "
            "1."
        ),
        "hints_how_to": (
            "Schneidet jede Karte entlang der gestrichelten Linien aus. Faltet sie entlang der Strich-Punkt-Linie, mit "
            "dem Druck nach außen. Der Text auf der Rückseite bleibt verdeckt, bis ihr die Karte umdreht."
        ),
        "hints_companion": (
            "Habt ihr ein Handy oder einen Computer? Die Spielbegleiter-Seite gibt dieselben Hinweise, einen nach dem "
            "anderen."
        ),
        "hint_label": "Hinweis {level}",
        "answer_label": "Lösung",
        "hint_turn": "Zum Lesen umdrehen",
        "solutions_title": "Lösungen",
        "solutions_warning_text": (
            "Diese Datei enthält alle Antworten und die ganze Geschichte. Lest sie erst am Ende des Spiels oder um "
            "eine Antwort zu prüfen."
        ),
        "solution_answer": "Antwort",
        "solution_accepted": "Auch richtig",
        "solution_steps": "So wird es gelöst",
        "deduction_title": "Die Anklage",
        "exclusions_title": "Warum nicht die anderen?",
        "truth_title": "Die ganze Wahrheit",
        "reveal_title": "Woran ihr es hättet erkennen können",
        "epilogues_title": "Enden",
        "epilogue_threshold": "{percent} % der Punkte oder mehr",
        "field_from": "Von",
        "field_to": "An",
        "field_cc": "Kopie",
        "field_date": "Datum",
        "field_time": "Uhrzeit",
        "field_subject": "Betreff",
        "field_case_number": "Akte Nr.",
        "field_officer": "Beamter",
        "field_station": "Wache",
        "field_seat": "Platz",
        "field_passenger": "Fahrgast",
        "field_price": "Preis",
        "field_number": "Nr.",
        "field_name": "Name",
        "field_role": "Beruf",
        "field_birth_date": "Geboren",
        "field_expires": "Gültig bis",
        "field_total": "Summe",
        "field_reward": "Belohnung",
        "field_scale": "Maßstab",
        "field_legend": "Legende",
        "field_interviewer": "Befragt von",
        "field_place": "Ort",
        "field_issuer": "Ausgestellt von",
        "field_form_number": "Formular",
        "word_telegram": "Telegramm",
        "word_transcript": "Protokoll",
        "word_report": "Bericht",
        "word_confidential": "Vertraulich",
        "word_ticket": "Fahrkarte",
        "word_identity": "Ausweis",
        "word_receipt": "Quittung",
        "word_thanks": "Vielen Dank",
        "manual_title": "Hier beginnen",
        "manual_checklist_title": "Druckliste",
        "manual_file": "Datei",
        "manual_pages": "Seiten",
        "manual_print_column": "Drucken?",
        "manual_print_yes": "Ja",
        "manual_print_optional": "Nur wenn ihr ohne Handy oder Computer spielt",
        "manual_print_companion_file": "Nein: auf einem Handy oder Computer öffnen",
        "manual_print_actual_size": (
            "Druckt in 100 % (tatsächliche Größe), einseitig, auf {paper}-Papier. Nutzt nicht „An Seite anpassen“."
        ),
        "manual_print_bw": "Dieses Spiel ist für einen Schwarz-Weiß-Drucker gemacht.",
        "manual_print_color": "In Farbe sieht es am besten aus, aber ein Schwarz-Weiß-Drucker geht auch.",
        "manual_print_skip_spoilers": (
            "Druckt die Hinweise und die Lösungen nicht aus, wenn ihr ein Handy oder einen Computer am Tisch habt: "
            "Nutzt stattdessen die Spielbegleiter-Seite."
        ),
        "manual_need_title": "Das braucht ihr",
        "manual_need_envelopes": "{count} Umschläge",
        "manual_need_folders": "{count} Mappen oder Büroklammern, eine für jeden Teil",
        "manual_need_pencils": "Bleistifte und einen Radiergummi",
        "manual_need_paper": "Etwas Schmierpapier",
        "manual_need_scissors": "Eine Schere",
        "manual_need_tape": "Klebeband oder Kleber",
        "manual_need_mirror": (
            "Ein kleiner Spiegel (oder ein helles Fenster: die Seite dagegen halten und von hinten lesen)"
        ),
        "manual_need_light": "Ein helles Fenster oder eine Lampe, um Seiten gegen das Licht zu halten",
        "manual_setup_title": "Vorbereitung",
        "manual_setup_split": "Lest das Spielmaterial nicht. Teilt den Stapel bei jeder Seite mit STOPP.",
        "manual_setup_outside": "Die Seiten vor der ersten STOPP-Seite kommen in keinen Umschlag: {pages}.",
        "manual_setup_outside_piles": "Die Seiten vor der ersten STOPP-Seite bleiben auf dem Tisch: {pages}.",
        "manual_outside_cover": "das Deckblatt",
        "manual_outside_labels": "die Etiketten",
        "manual_outside_register": "das Antwortregister",
        "manual_outside_notes": "die Ermittlungsnotizen",
        "list_separator": ", ",
        "list_two": "{first} und {last}",
        "list_many": "{items} und {last}",
        "manual_setup_envelopes": (
            "Legt jeden Teil in einen eigenen Umschlag, mit seiner STOPP-Seite oben. Klebt das passende Etikett auf "
            "jeden Umschlag und verschließt ihn."
        ),
        "manual_setup_piles": "Legt jeden Teil verdeckt auf einen eigenen Stapel, mit seiner STOPP-Seite oben.",
        "manual_setup_spoilers": "Legt die Hinweise und die Lösungen außer Sicht, bis ihr sie braucht.",
        "manual_play_title": "So wird gespielt",
        "manual_play_open_first": "Öffnet Umschlag A. Lest diese Einleitung laut vor:",
        "manual_play_solve": (
            "Lest die Dokumente und löst die Rätsel. Der Code in der Ecke einer Seite (zum Beispiel A1) zeigt, zu "
            "welchem Rätsel sie gehört."
        ),
        "manual_play_check_register": (
            "Habt ihr eine Antwort, sucht sie im Antwortregister und lest den Abschnitt, zu dem es euch schickt."
        ),
        "manual_play_check_companion": "Oder gebt die Antwort auf der Spielbegleiter-Seite ein.",
        "manual_play_next": (
            "Eine richtige Antwort sagt euch, wann ihr den nächsten Umschlag öffnet. Öffnet nie einen Umschlag vorher."
        ),
        "manual_play_accusation": "Füllt am Ende gemeinsam das Anklageformular aus.",
        "manual_hints_title": "Hinweise und Lösungen",
        "manual_hints_text": (
            "Kommt ihr nicht weiter? Nehmt die Hinweiskarten mit dem Code eures Rätsels und lest zuerst Hinweis 1. "
            "Lest die nächste Karte nur, wenn ihr sie noch braucht. Die letzte Karte nennt die Antwort."
        ),
        "manual_hints_companion": "Die Spielbegleiter-Seite zeigt dieselben Hinweise, einen nach dem anderen.",
        "manual_solutions_text": "Die Lösungen erklären jedes Rätsel und die ganze Geschichte. Lest sie am Ende.",
        "manual_scoring_title": "Anklage und Punkte",
        "manual_scoring_text": (
            "Jede Frage des Anklageformulars bringt Punkte, insgesamt {total}. Zählt eure Punkte und sucht euer Ende "
            "in den Lösungen:"
        ),
        "manual_rank_points": "Punkte",
        "manual_rank_ending": "Ende",
        "manual_rank_range": "{low} bis {high}",
        "manual_host_title": "Leitfaden für die Spielleitung",
        "manual_host_intro": (
            "Du leitest das Spiel und spielst nicht mit. Du darfst vor dem Spiel alles lesen. Plane deine Zeit mit "
            "dieser Tabelle (Minuten ab Beginn):"
        ),
        "manual_host_stage": "Umschlag",
        "manual_host_puzzles": "Rätsel",
        "manual_host_minutes": "Minuten",
        "manual_host_by": "Fertig bei Minute",
        "manual_host_stuck": "Kommt eine Gruppe 10 Minuten nicht weiter, gib ihr den nächsten Hinweis.",
        "manual_host_answers": (
            "Prüfe jede Antwort mit dem Antwortregister oder der Spielbegleiter-Seite, bevor du den nächsten Umschlag "
            "ausgibst."
        ),
        "manual_personal_title": "Für dieses Spiel",
        "manual_host_name": "Gastgeber: {name}",
        "manual_player_names": "Detektive: {names}",
    },
    "it": {
        "envelope_label": "Busta {stage}",
        "continued": "continua",
        "materials_title": "Materiale di gioco",
        "file_manual": "1 - INIZIA DA QUI (manuale)",
        "file_materials": "2 - STAMPA QUESTO (materiale di gioco)",
        "file_hints": "3 - Indizi",
        "file_solutions": "4 - Soluzioni",
        "file_companion": "Compagno di gioco",
        "folder_spoilers": "SOLO CHI CONDUCE - spoiler",
        "file_export_warnings": "0 - LEGGI PRIMA (avvisi)",
        "export_warnings_title": "Leggi qui prima di giocare",
        "export_warnings_intro": (
            "Mystery Forge prova ogni gioco con controlli automatici e con giocatori di prova IA. Alcune prove di "
            "questo gioco non sono riuscite. Il gioco probabilmente funziona, ma le parti qui sotto possono essere "
            "poco chiare, troppo difficili o sbagliate."
        ),
        "export_warnings_fix": (
            "Per correggerle, fai doppio clic su Start Mystery Forge, scrivi 4 e chiedi all'IA di correggere gli "
            "avvisi di questo gioco."
        ),
        "export_warning_puzzle": "Enigma {code}: {problems}",
        "export_warning_accusation": "Modulo d'accusa: {problems}",
        "export_warning_checks_failing": "alcuni controlli automatici non sono riusciti.",
        "export_warning_checks_stale": "i controlli automatici non sono stati ripetuti dopo l'ultima modifica.",
        "export_warning_panel_stale": "i giocatori di prova non l'hanno provato dopo l'ultima modifica.",
        "export_warning_ambiguous": "i giocatori di prova hanno trovato più di una risposta possibile.",
        "export_warning_gold_suspect": "i giocatori di prova pensano che la risposta attesa possa essere sbagliata.",
        "export_warning_too_hard": "i giocatori di prova non sono riusciti a risolverlo.",
        "export_warning_guessable": "i giocatori di prova hanno potuto indovinare la risposta senza gli indizi.",
        "export_warning_incomplete": "i giocatori di prova pensano che manchi qualcosa che serve loro.",
        "export_warning_trivial": "i giocatori di prova l'hanno trovato troppo facile.",
        "export_warning_insufficient_solvers": "troppo pochi giocatori di prova hanno finito la prova.",
        "export_warning_puzzles_not_needed": "i giocatori di prova hanno potuto rispondere senza risolvere gli enigmi.",
        "made_with": "Creato con Mystery Forge",
        "page_label": "Pagina {number} di {count}",
        "copy_label": "Copia {number} di {count}",
        "puzzle_badge": "Enigma",
        "print_cut": "Ritaglia lungo la linea tratteggiata.",
        "print_fold": "Piega lungo la linea a tratto e punto.",
        "cover_kicker": "Un mistero da stampare",
        "cover_players": "{count} giocatori",
        "cover_players_solo": "1 giocatore",
        "accusation_intro_solo": (
            "Rispondi a ogni domanda. "
            "Segna una casella per ogni domanda e indica il documento che lo prova. Poi conta i tuoi punti."
        ),
        "manual_play_accusation_solo": "Alla fine, compila il modulo d'accusa.",
        "cover_duration": "Circa {minutes} minuti",
        "cover_detectives": "Detective: {names}",
        "cover_do_not_read": "Non leggere in anticipo. Apri ogni busta solo quando il gioco te lo dice.",
        "stop": "STOP",
        "stage_open_at_start": "Apri questa busta all'inizio della partita.",
        "stage_open_when": (
            "Non aprire ancora questa busta. Aprila solo quando il controllo delle risposte te lo dice, dopo aver "
            "risolto l'enigma {code}."
        ),
        "stage_turn_page": "Dopo aver aperto la busta, gira questa pagina e leggi il testo ad alta voce.",
        "stage_read_aloud": "Leggete ad alta voce",
        "register_title": "Registro delle risposte",
        "register_answer": "Risposta",
        "register_paragraph": "Paragrafo",
        "results_title": "Paragrafi di risultato",
        "results_intro": "Leggi solo il paragrafo indicato dal registro delle risposte.",
        "register_wrong": "Non succede nulla. Riprovate.",
        "register_intro": (
            "Scrivi la tua risposta in maiuscolo, senza spazi e senza accenti, poi cercala in questo elenco. "
            "Prima i numeri, poi le parole dalla A alla Z. Poi leggi il paragrafo di risultato con il numero "
            "accanto. Se la tua risposta non è nell'elenco, non è corretta."
        ),
        "register_correct_open": "Esatto! Aprite ora la {envelope}.",
        "register_correct_keep": "Esatto! Scrivete questa risposta: un enigma successivo ne ha bisogno.",
        "register_correct_accusation": "Esatto! Era l'ultimo enigma: passate all'accusa.",
        "register_correct_notes": "Esatto! Scrivetela nei vostri appunti.",
        "register_story_card": (
            "Prima di andare avanti, leggi la carta della storia {number} alla fine della {envelope}."
        ),
        "story_cards_title": "Carte della storia",
        "story_cards_intro": (
            "Leggi una carta solo quando il registro delle risposte ti manda lì. Gira il foglio per leggerla."
        ),
        "print_cut_strips": "Quando aprite questa busta, separate le strisce: tagliate lungo le linee tratteggiate.",
        "manual_need_label_tape": (
            "Nastro adesivo o colla per le etichette delle buste (oppure scrivete la lettera su ogni busta)"
        ),
        "manual_print_box_title": "Stampa al 100%",
        "manual_print_box_chrome": "Chrome: Altre impostazioni > Scala > Predefinita",
        "manual_print_box_edge": "Edge: Altre impostazioni > Scala > Dimensioni effettive",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Ridimensionamento e gestione pagine > Dimensioni effettive",
        "citation_revealed_by": "Rivelato dall'enigma {code}",
        "accusation_title": "Modulo d'accusa",
        "accusation_intro": (
            "Rispondete insieme a ogni domanda. Segnate una casella per domanda e scrivete il documento che lo prova. "
            "Poi contate i punti."
        ),
        "accusation_proof": "Quale documento lo prova?",
        "accusation_points": "{points} punti",
        "accusation_detectives": "Detective",
        "accusation_total": "I vostri punti: ______ su {total}",
        "labels_title": "Etichette delle buste",
        "labels_intro": "Ritaglia ogni etichetta e incollala sulla sua busta.",
        "label_open_start": "Da aprire all'inizio",
        "label_open_after": "Da aprire solo dopo l'enigma {code}",
        "notes_title": "Appunti del detective",
        "notes_intro": "Annota ciò che scopri. Usa una matita.",
        "notes_suspect": "Sospettato",
        "notes_motive": "Movente",
        "notes_opportunity": "Occasione",
        "notes_alibi": "Alibi",
        "notes_where": "Chi era dove?",
        "notes_free": "Appunti",
        "warning_title": "Attenzione: spoiler",
        "hints_title": "Carte degli indizi",
        "hints_warning_text": (
            "Queste carte vi aiutano quando siete bloccati. Leggete una sola carta alla volta e iniziate sempre "
            "dall'Indizio 1."
        ),
        "hints_how_to": (
            "Ritaglia ogni carta lungo le linee tratteggiate. Piegala lungo la linea a tratto e punto, con la stampa "
            "verso l'esterno. Il testo sul retro resta nascosto finché non giri la carta."
        ),
        "hints_companion": (
            "Avete un telefono o un computer? La pagina Compagno di gioco dà gli stessi indizi, uno alla volta."
        ),
        "hint_label": "Indizio {level}",
        "answer_label": "Risposta",
        "hint_turn": "Gira per leggere",
        "solutions_title": "Soluzioni",
        "solutions_warning_text": (
            "Questo file contiene tutte le risposte e tutta la storia. Leggetelo solo alla fine della partita o per "
            "verificare una risposta."
        ),
        "solution_answer": "Risposta",
        "solution_accepted": "Accettato anche",
        "solution_steps": "Come si risolve",
        "deduction_title": "L'accusa",
        "exclusions_title": "Perché non gli altri?",
        "truth_title": "Tutta la verità",
        "reveal_title": "Come potevate saperlo",
        "epilogues_title": "Finali",
        "epilogue_threshold": "{percent}% dei punti o più",
        "field_from": "Da",
        "field_to": "A",
        "field_cc": "Cc",
        "field_date": "Data",
        "field_time": "Ora",
        "field_subject": "Oggetto",
        "field_case_number": "Caso n.",
        "field_officer": "Agente",
        "field_station": "Commissariato",
        "field_seat": "Posto",
        "field_passenger": "Passeggero",
        "field_price": "Prezzo",
        "field_number": "N.",
        "field_name": "Nome",
        "field_role": "Professione",
        "field_birth_date": "Nato il",
        "field_expires": "Valido fino al",
        "field_total": "Totale",
        "field_reward": "Ricompensa",
        "field_scale": "Scala",
        "field_legend": "Legenda",
        "field_interviewer": "Intervistatore",
        "field_place": "Luogo",
        "field_issuer": "Rilasciato da",
        "field_form_number": "Modulo",
        "word_telegram": "Telegramma",
        "word_transcript": "Trascrizione",
        "word_report": "Rapporto",
        "word_confidential": "Riservato",
        "word_ticket": "Biglietto",
        "word_identity": "Carta d'identità",
        "word_receipt": "Ricevuta",
        "word_thanks": "Grazie",
        "manual_title": "Inizia da qui",
        "manual_checklist_title": "Lista di stampa",
        "manual_file": "File",
        "manual_pages": "Pagine",
        "manual_print_column": "Stampare?",
        "manual_print_yes": "Sì",
        "manual_print_optional": "Solo se giocate senza telefono né computer",
        "manual_print_companion_file": "No: aprilo su un telefono o un computer",
        "manual_print_actual_size": (
            "Stampa al 100% (dimensioni reali), solo fronte, su carta {paper}. Non usare «adatta alla pagina»."
        ),
        "manual_print_bw": "Questo gioco è pensato per una stampante in bianco e nero.",
        "manual_print_color": "A colori rende meglio, ma va bene anche una stampante in bianco e nero.",
        "manual_print_skip_spoilers": (
            "Non stampare gli indizi e le soluzioni se avete un telefono o un computer al tavolo: usate invece la "
            "pagina Compagno di gioco."
        ),
        "manual_need_title": "Cosa ti serve",
        "manual_need_envelopes": "{count} buste",
        "manual_need_folders": "{count} cartelline o graffette, una per ogni parte",
        "manual_need_pencils": "Matite e una gomma",
        "manual_need_paper": "Un po' di carta per appunti",
        "manual_need_scissors": "Forbici",
        "manual_need_tape": "Nastro adesivo o colla",
        "manual_need_mirror": "Uno specchietto (o una finestra luminosa: appoggia il foglio e leggilo dal retro)",
        "manual_need_light": "Una finestra luminosa o una lampada, per guardare i fogli in controluce",
        "manual_setup_title": "Preparazione",
        "manual_setup_split": "Non leggere il materiale di gioco. Dividi la pila a ogni pagina con scritto STOP.",
        "manual_setup_outside": "Le pagine prima della prima pagina STOP restano fuori dalle buste: {pages}.",
        "manual_setup_outside_piles": "Le pagine prima della prima pagina STOP restano sul tavolo: {pages}.",
        "manual_outside_cover": "la copertina",
        "manual_outside_labels": "le etichette",
        "manual_outside_register": "il registro delle risposte",
        "manual_outside_notes": "gli appunti del detective",
        "list_separator": ", ",
        "list_two": "{first} e {last}",
        "list_many": "{items} e {last}",
        "manual_setup_envelopes": (
            "Metti ogni parte nella sua busta, con la sua pagina STOP sopra. Incolla l'etichetta giusta su ogni busta "
            "e chiudila."
        ),
        "manual_setup_piles": "Metti ogni parte a faccia in giù in una pila separata, con la sua pagina STOP sopra.",
        "manual_setup_spoilers": "Tieni gli indizi e le soluzioni fuori vista finché non servono.",
        "manual_play_title": "Come si gioca",
        "manual_play_open_first": "Aprite la Busta A. Leggete questa introduzione ad alta voce:",
        "manual_play_solve": (
            "Leggete i documenti e risolvete gli enigmi. Il codice nell'angolo di una pagina (per esempio A1) indica a "
            "quale enigma appartiene."
        ),
        "manual_play_check_register": (
            "Quando avete una risposta, cercatela nel registro delle risposte e leggete il paragrafo indicato."
        ),
        "manual_play_check_companion": "Oppure scrivete la risposta nella pagina Compagno di gioco.",
        "manual_play_next": (
            "Una risposta corretta vi dice quando aprire la busta successiva. Non aprite mai una busta prima."
        ),
        "manual_play_accusation": "Alla fine, compilate insieme il modulo d'accusa.",
        "manual_hints_title": "Indizi e soluzioni",
        "manual_hints_text": (
            "Bloccati? Prendete le carte degli indizi con il codice del vostro enigma e leggete prima l'Indizio 1. "
            "Leggete la carta successiva solo se vi serve ancora. L'ultima carta dà la risposta."
        ),
        "manual_hints_companion": "La pagina Compagno di gioco mostra gli stessi indizi, uno alla volta.",
        "manual_solutions_text": "Le soluzioni spiegano ogni enigma e tutta la storia. Leggetele alla fine.",
        "manual_scoring_title": "Accusa e punteggio",
        "manual_scoring_text": (
            "Ogni domanda del modulo d'accusa dà punti, {total} in tutto. Contate i punti e trovate il vostro finale "
            "nelle soluzioni:"
        ),
        "manual_rank_points": "Punti",
        "manual_rank_ending": "Finale",
        "manual_rank_range": "Da {low} a {high}",
        "manual_host_title": "Guida per chi conduce",
        "manual_host_intro": (
            "Tu conduci la partita e non giochi. Puoi leggere tutto prima di iniziare. Organizza il tempo con questa "
            "tabella (minuti dall'inizio):"
        ),
        "manual_host_stage": "Busta",
        "manual_host_puzzles": "Enigmi",
        "manual_host_minutes": "Minuti",
        "manual_host_by": "Finito al minuto",
        "manual_host_stuck": "Se un gruppo è bloccato da 10 minuti, dagli l'indizio successivo.",
        "manual_host_answers": (
            "Controlla ogni risposta con il registro delle risposte o la pagina Compagno di gioco prima di dare la "
            "busta successiva."
        ),
        "manual_personal_title": "Per questa partita",
        "manual_host_name": "Chi conduce: {name}",
        "manual_player_names": "Detective: {names}",
    },
    "pt": {
        "envelope_label": "Envelope {stage}",
        "continued": "continuação",
        "materials_title": "Material do jogo",
        "file_manual": "1 - COMECE AQUI (manual)",
        "file_materials": "2 - IMPRIMA ISTO (material do jogo)",
        "file_hints": "3 - Pistas",
        "file_solutions": "4 - Soluções",
        "file_companion": "Companheiro de jogo",
        "folder_spoilers": "SÓ ANFITRIÃO - spoilers",
        "file_export_warnings": "0 - LEIA PRIMEIRO (avisos)",
        "export_warnings_title": "Leia isto antes de jogar",
        "export_warnings_intro": (
            "O Mystery Forge testa cada jogo com verificações automáticas e com jogadores de teste de IA. Alguns "
            "testes deste jogo não passaram. O jogo provavelmente funciona, mas as partes abaixo podem ser confusas, "
            "difíceis demais ou erradas."
        ),
        "export_warnings_fix": (
            "Para corrigi-las, clique duas vezes em Start Mystery Forge, digite 4 e peça à IA que corrija os avisos "
            "deste jogo."
        ),
        "export_warning_puzzle": "Enigma {code}: {problems}",
        "export_warning_accusation": "Formulário de acusação: {problems}",
        "export_warning_checks_failing": "algumas verificações automáticas falharam.",
        "export_warning_checks_stale": "as verificações automáticas não foram repetidas após a última alteração.",
        "export_warning_panel_stale": "os jogadores de teste não o testaram após a última alteração.",
        "export_warning_ambiguous": "os jogadores de teste encontraram mais de uma resposta possível.",
        "export_warning_gold_suspect": "os jogadores de teste acham que a resposta esperada pode estar errada.",
        "export_warning_too_hard": "os jogadores de teste não conseguiram resolvê-lo.",
        "export_warning_guessable": "os jogadores de teste conseguiram adivinhar a resposta sem as pistas.",
        "export_warning_incomplete": "os jogadores de teste acham que falta algo de que precisam.",
        "export_warning_trivial": "os jogadores de teste acharam-no fácil demais.",
        "export_warning_insufficient_solvers": "poucos jogadores de teste terminaram o teste.",
        "export_warning_puzzles_not_needed": "os jogadores de teste conseguiram responder sem resolver os enigmas.",
        "made_with": "Feito com Mystery Forge",
        "page_label": "Página {number} de {count}",
        "copy_label": "Cópia {number} de {count}",
        "puzzle_badge": "Enigma",
        "print_cut": "Recorte pela linha tracejada.",
        "print_fold": "Dobre pela linha de traço e ponto.",
        "cover_kicker": "Um mistério para imprimir",
        "cover_players": "{count} jogadores",
        "cover_players_solo": "1 jogador",
        "accusation_intro_solo": (
            "Responde a cada pergunta. "
            "Marca uma caixa em cada pergunta e indica o documento que o prova. Depois conta os teus pontos."
        ),
        "manual_play_accusation_solo": "No fim, preenche o formulário de acusação.",
        "cover_duration": "Cerca de {minutes} minutos",
        "cover_detectives": "Detetives: {names}",
        "cover_do_not_read": "Não leia antes do tempo. Abra cada envelope só quando o jogo mandar.",
        "stop": "PARE",
        "stage_open_at_start": "Abra este envelope no início do jogo.",
        "stage_open_when": (
            "Ainda não abra este envelope. Abra-o só quando a verificação de respostas mandar, depois de resolver o "
            "enigma {code}."
        ),
        "stage_turn_page": "Depois de abrir o envelope, vire esta página e leia o texto em voz alta.",
        "stage_read_aloud": "Leiam em voz alta",
        "register_title": "Registo de respostas",
        "register_answer": "Resposta",
        "register_paragraph": "Parágrafo",
        "results_title": "Parágrafos de resultado",
        "results_intro": "Leia só o parágrafo indicado pelo registo de respostas.",
        "register_wrong": "Não acontece nada. Tentem outra vez.",
        "register_intro": (
            "Escreva a sua resposta em maiúsculas, sem espaços e sem acentos (o Ç escreve-se C), e depois "
            "procure-a nesta lista. Primeiro os números, depois as palavras de A a Z. Leia o parágrafo de "
            "resultado com o número ao lado. Se a sua resposta não está na lista, não está correta."
        ),
        "register_correct_open": "Correto! Abram agora o {envelope}.",
        "register_correct_keep": "Correto! Anotem esta resposta: um enigma mais à frente precisa dela.",
        "register_correct_accusation": "Correto! Era o último enigma: passem à acusação.",
        "register_correct_notes": "Correto! Escrevam-na nas vossas notas.",
        "register_story_card": "Antes de continuar, leia o cartão de história {number} no fim do {envelope}.",
        "story_cards_title": "Cartões de história",
        "story_cards_intro": (
            "Leia um cartão só quando o registo de respostas o mandar para ele. Vire a folha para o ler."
        ),
        "print_cut_strips": "Quando abrirem este envelope, separem as tiras: cortem pelas linhas tracejadas.",
        "manual_need_label_tape": (
            "Fita-cola ou cola para as etiquetas dos envelopes (ou escrevam a letra em cada envelope)"
        ),
        "manual_print_box_title": "Imprima a 100%",
        "manual_print_box_chrome": "Chrome: Mais definições > Escala > Predefinição",
        "manual_print_box_edge": "Edge: Mais definições > Escala > Tamanho real",
        "manual_print_box_acrobat": "Adobe Acrobat Reader: Dimensionamento e manuseamento de páginas > Tamanho real",
        "citation_revealed_by": "Revelado pelo enigma {code}",
        "accusation_title": "Formulário de acusação",
        "accusation_intro": (
            "Respondam juntos a cada pergunta. Marquem uma caixa por pergunta e escrevam o documento que o prova. "
            "Depois contem os pontos."
        ),
        "accusation_proof": "Que documento o prova?",
        "accusation_points": "{points} pontos",
        "accusation_detectives": "Detetives",
        "accusation_total": "Os vossos pontos: ______ de {total}",
        "labels_title": "Etiquetas dos envelopes",
        "labels_intro": "Recorte cada etiqueta e cole-a no seu envelope.",
        "label_open_start": "Abrir no início",
        "label_open_after": "Abrir só depois do enigma {code}",
        "notes_title": "Notas do detetive",
        "notes_intro": "Anote o que descobrir. Use um lápis.",
        "notes_suspect": "Suspeito",
        "notes_motive": "Motivo",
        "notes_opportunity": "Oportunidade",
        "notes_alibi": "Álibi",
        "notes_where": "Quem estava onde?",
        "notes_free": "Notas",
        "warning_title": "Aviso de spoilers",
        "hints_title": "Cartões de pistas",
        "hints_warning_text": (
            "Estes cartões ajudam quando ficam bloqueados. Leiam só um cartão de cada vez e comecem sempre pela Pista "
            "1."
        ),
        "hints_how_to": (
            "Recorte cada cartão pelas linhas tracejadas. Dobre-o pela linha de traço e ponto, com a impressão para "
            "fora. O texto do verso fica escondido até virar o cartão."
        ),
        "hints_companion": (
            "Têm um telemóvel ou um computador? A página Companheiro de jogo dá as mesmas pistas, uma de cada vez."
        ),
        "hint_label": "Pista {level}",
        "answer_label": "Resposta",
        "hint_turn": "Vire para ler",
        "solutions_title": "Soluções",
        "solutions_warning_text": (
            "Este ficheiro contém todas as respostas e a história completa. Leiam-no só no fim do jogo ou para "
            "verificar uma resposta."
        ),
        "solution_answer": "Resposta",
        "solution_accepted": "Também aceite",
        "solution_steps": "Como se resolve",
        "deduction_title": "A acusação",
        "exclusions_title": "Porque não os outros?",
        "truth_title": "Toda a verdade",
        "reveal_title": "Como podiam ter sabido",
        "epilogues_title": "Finais",
        "epilogue_threshold": "{percent}% dos pontos ou mais",
        "field_from": "De",
        "field_to": "Para",
        "field_cc": "Cc",
        "field_date": "Data",
        "field_time": "Hora",
        "field_subject": "Assunto",
        "field_case_number": "Processo n.º",
        "field_officer": "Agente",
        "field_station": "Esquadra",
        "field_seat": "Lugar",
        "field_passenger": "Passageiro",
        "field_price": "Preço",
        "field_number": "N.º",
        "field_name": "Nome",
        "field_role": "Profissão",
        "field_birth_date": "Nascimento",
        "field_expires": "Válido até",
        "field_total": "Total",
        "field_reward": "Recompensa",
        "field_scale": "Escala",
        "field_legend": "Legenda",
        "field_interviewer": "Entrevistador",
        "field_place": "Local",
        "field_issuer": "Emitido por",
        "field_form_number": "Formulário",
        "word_telegram": "Telegrama",
        "word_transcript": "Transcrição",
        "word_report": "Relatório",
        "word_confidential": "Confidencial",
        "word_ticket": "Bilhete",
        "word_identity": "Bilhete de identidade",
        "word_receipt": "Recibo",
        "word_thanks": "Obrigado",
        "manual_title": "Comece aqui",
        "manual_checklist_title": "Lista de impressão",
        "manual_file": "Ficheiro",
        "manual_pages": "Páginas",
        "manual_print_column": "Imprimir?",
        "manual_print_yes": "Sim",
        "manual_print_optional": "Só se jogarem sem telemóvel nem computador",
        "manual_print_companion_file": "Não: abra-o num telemóvel ou computador",
        "manual_print_actual_size": (
            "Imprima a 100% (tamanho real), só de um lado, em papel {paper}. Não use «ajustar à página»."
        ),
        "manual_print_bw": "Este jogo foi feito para uma impressora a preto e branco.",
        "manual_print_color": "A cores fica melhor, mas uma impressora a preto e branco também serve.",
        "manual_print_skip_spoilers": (
            "Não imprima as pistas nem as soluções se tiverem um telemóvel ou um computador na mesa: usem antes a "
            "página Companheiro de jogo."
        ),
        "manual_need_title": "O que precisa",
        "manual_need_envelopes": "{count} envelopes",
        "manual_need_folders": "{count} pastas ou clipes, um para cada parte",
        "manual_need_pencils": "Lápis e uma borracha",
        "manual_need_paper": "Algum papel de rascunho",
        "manual_need_scissors": "Tesoura",
        "manual_need_tape": "Fita-cola ou cola",
        "manual_need_mirror": "Um pequeno espelho (ou uma janela clara: encoste a folha e leia-a pelo verso)",
        "manual_need_light": "Uma janela clara ou um candeeiro, para ver folhas contra a luz",
        "manual_setup_title": "Preparação",
        "manual_setup_split": "Não leia o material do jogo. Separe a pilha em cada página que diz PARE.",
        "manual_setup_outside": "As páginas antes da primeira página PARE ficam fora dos envelopes: {pages}.",
        "manual_setup_outside_piles": "As páginas antes da primeira página PARE ficam em cima da mesa: {pages}.",
        "manual_outside_cover": "a capa",
        "manual_outside_labels": "as etiquetas",
        "manual_outside_register": "o registo de respostas",
        "manual_outside_notes": "as notas do detetive",
        "list_separator": ", ",
        "list_two": "{first} e {last}",
        "list_many": "{items} e {last}",
        "manual_setup_envelopes": (
            "Coloque cada parte no seu envelope, com a sua página PARE por cima. Cole a etiqueta certa em cada "
            "envelope e feche-o."
        ),
        "manual_setup_piles": (
            "Coloque cada parte virada para baixo numa pilha própria, com a sua página PARE por cima."
        ),
        "manual_setup_spoilers": "Guarde as pistas e as soluções fora de vista até precisarem delas.",
        "manual_play_title": "Como se joga",
        "manual_play_open_first": "Abram o Envelope A. Leiam esta introdução em voz alta:",
        "manual_play_solve": (
            "Leiam os documentos e resolvam os enigmas. O código no canto de uma página (por exemplo, A1) diz a que "
            "enigma pertence."
        ),
        "manual_play_check_register": (
            "Quando tiverem uma resposta, procurem-na no registo de respostas e leiam o parágrafo indicado."
        ),
        "manual_play_check_companion": "Ou escrevam a resposta na página Companheiro de jogo.",
        "manual_play_next": (
            "Uma resposta correta diz-vos quando abrir o envelope seguinte. Nunca abram um envelope antes."
        ),
        "manual_play_accusation": "No fim, preencham juntos o formulário de acusação.",
        "manual_hints_title": "Pistas e soluções",
        "manual_hints_text": (
            "Bloqueados? Peguem nos cartões de pistas com o código do vosso enigma e leiam primeiro a Pista 1. Leiam o "
            "cartão seguinte só se ainda precisarem. O último cartão dá a resposta."
        ),
        "manual_hints_companion": "A página Companheiro de jogo mostra as mesmas pistas, uma de cada vez.",
        "manual_solutions_text": "As soluções explicam cada enigma e toda a história. Leiam-nas no fim.",
        "manual_scoring_title": "Acusação e pontuação",
        "manual_scoring_text": (
            "Cada pergunta do formulário de acusação dá pontos, {total} no total. Contem os pontos e procurem o vosso "
            "final nas soluções:"
        ),
        "manual_rank_points": "Pontos",
        "manual_rank_ending": "Final",
        "manual_rank_range": "De {low} a {high}",
        "manual_host_title": "Guia do mestre de jogo",
        "manual_host_intro": (
            "Você conduz o jogo e não joga. Pode ler tudo antes de começar. Planeie o tempo com esta tabela (minutos "
            "desde o início):"
        ),
        "manual_host_stage": "Envelope",
        "manual_host_puzzles": "Enigmas",
        "manual_host_minutes": "Minutos",
        "manual_host_by": "Acabado ao minuto",
        "manual_host_stuck": "Se um grupo estiver bloqueado há 10 minutos, dê-lhe a pista seguinte.",
        "manual_host_answers": (
            "Verifique cada resposta com o registo de respostas ou a página Companheiro de jogo antes de entregar o "
            "envelope seguinte."
        ),
        "manual_personal_title": "Para este jogo",
        "manual_host_name": "Anfitrião: {name}",
        "manual_player_names": "Detetives: {names}",
    },
}

# The texts of the companion page. The page fills each `{name}` field itself, in JavaScript, so `text()` never formats
# these. The "Check" and "Solutions" words in the help texts must match the tab names of the same language.
COMPANION_STRINGS: Final[dict[str, dict[str, str]]] = {
    "en": {
        "companion_page_label": "Game companion",
        "companion_tab_start": "Start",
        "companion_tab_check": "Check",
        "companion_tab_hints": "Hints",
        "companion_tab_accuse": "Accuse",
        "companion_tab_solutions": "Solutions",
        "companion_tab_help": "How to play",
        "companion_read_aloud": "Read this aloud",
        "companion_intro_more": "Read the whole introduction",
        "companion_game_length": "About {minutes} minutes",
        "companion_timer_label": "Time left",
        "companion_timer_overtime": "Extra time",
        "companion_timer_start": "Start the clock",
        "companion_timer_pause": "Pause",
        "companion_timer_resume": "Resume",
        "companion_envelopes_heading": "Envelopes",
        "companion_envelope_open": "Open",
        "companion_envelope_sealed": "Sealed",
        "companion_check_heading": "Check an answer",
        "companion_check_puzzle_label": "Puzzle code",
        "companion_check_answer_label": "Your answer",
        "companion_check_submit": "Check",
        "companion_result_correct": "Correct!",
        "companion_result_near": "Almost there",
        "companion_result_wrong": "Not quite. Try again.",
        "companion_result_solved": "Solved",
        "companion_unlock_call": "Open now: {envelope}",
        "companion_hints_heading": "Hints",
        "companion_hints_intro": "Try first. Each hint shows one small step.",
        "companion_hint_show": "Show hint {level}",
        "companion_hint_label": "Hint {level}",
        "companion_hint_confirm": "Show hint {level} for puzzle {code}?",
        "companion_answer_show": "Show the answer",
        "companion_answer_confirm": (
            "Show the full answer to puzzle {code}? This spoils the puzzle for the whole group."
        ),
        "companion_confirm_yes": "Yes, show it",
        "companion_confirm_no": "Not yet",
        "companion_solutions_warning_title": "Spoilers ahead",
        "companion_solutions_warning_text": (
            "This page shows the full solutions. Open one only when the whole group agrees."
        ),
        "companion_solutions_enter": "I understand. Show the list.",
        "companion_solution_show": "Show the solution to {code}",
        "companion_solution_answer": "Answer: {answer}",
        "companion_accuse_heading": "The accusation",
        "companion_accuse_intro": "Agree on an answer to every question, then lock in your accusation.",
        "companion_accuse_early": "Most groups accuse after they solve the last puzzle.",
        "companion_accuse_submit": "Lock in the accusation",
        "companion_accuse_confirm": "Lock in these answers? You cannot change them later.",
        "companion_accuse_incomplete": "Answer every question first.",
        "companion_score": "{points} of {max} points",
        "companion_question_right": "Right",
        "companion_question_wrong": "Wrong",
        "companion_reveal_heading": "How you could have known",
        "companion_ending_heading": "The ending",
        "companion_final_solved": "You solved the last puzzle!",
        "companion_no_puzzles": "No puzzle is open yet.",
        "companion_locked_note": "More puzzles appear here when you open the next envelope.",
        "companion_reset": "Start over",
        "companion_reset_confirm": "Erase all progress on this device and start over?",
        "companion_storage_off": "This browser does not save your progress. Keep this page open.",
        "companion_help_1": "Read the introduction aloud, then start the clock.",
        "companion_help_2": "Open an envelope only when the game tells you to.",
        "companion_help_3": (
            "When you have an answer, type it under Check. Spaces, accents, and capital letters do not matter."
        ),
        "companion_help_4": "Stuck? Hints show one small step at a time. The answer comes last.",
        "companion_help_5": "Solutions shows everything. Use it at the end, or when the whole group agrees.",
        "companion_close": "Close",
    },
    "es": {
        "companion_page_label": "Compañero de juego",
        "companion_tab_start": "Inicio",
        "companion_tab_check": "Comprobar",
        "companion_tab_hints": "Pistas",
        "companion_tab_accuse": "Acusar",
        "companion_tab_solutions": "Soluciones",
        "companion_tab_help": "Cómo se juega",
        "companion_read_aloud": "Leedlo en voz alta",
        "companion_intro_more": "Leer toda la introducción",
        "companion_game_length": "Unos {minutes} minutos",
        "companion_timer_label": "Tiempo restante",
        "companion_timer_overtime": "Tiempo extra",
        "companion_timer_start": "Poner en marcha el reloj",
        "companion_timer_pause": "Pausa",
        "companion_timer_resume": "Continuar",
        "companion_envelopes_heading": "Sobres",
        "companion_envelope_open": "Abierto",
        "companion_envelope_sealed": "Cerrado",
        "companion_check_heading": "Comprobar una respuesta",
        "companion_check_puzzle_label": "Código del enigma",
        "companion_check_answer_label": "Vuestra respuesta",
        "companion_check_submit": "Comprobar",
        "companion_result_correct": "¡Correcto!",
        "companion_result_near": "Casi",
        "companion_result_wrong": "No es eso. Probad otra vez.",
        "companion_result_solved": "Resuelto",
        "companion_unlock_call": "Abrid ahora: {envelope}",
        "companion_hints_heading": "Pistas",
        "companion_hints_intro": "Intentadlo primero. Cada pista muestra un pequeño paso.",
        "companion_hint_show": "Mostrar la pista {level}",
        "companion_hint_label": "Pista {level}",
        "companion_hint_confirm": "¿Mostrar la pista {level} del enigma {code}?",
        "companion_answer_show": "Mostrar la respuesta",
        "companion_answer_confirm": (
            "¿Mostrar la respuesta completa del enigma {code}? Esto desvela el enigma a todo el grupo."
        ),
        "companion_confirm_yes": "Sí, mostrarla",
        "companion_confirm_no": "Todavía no",
        "companion_solutions_warning_title": "Cuidado: soluciones",
        "companion_solutions_warning_text": (
            "Esta página muestra las soluciones completas. Abrid una solo cuando todo el grupo esté de acuerdo."
        ),
        "companion_solutions_enter": "Lo entiendo. Mostrar la lista.",
        "companion_solution_show": "Mostrar la solución de {code}",
        "companion_solution_answer": "Respuesta: {answer}",
        "companion_accuse_heading": "La acusación",
        "companion_accuse_intro": "Poneos de acuerdo en cada pregunta y después confirmad la acusación.",
        "companion_accuse_early": "La mayoría de los grupos acusan después de resolver el último enigma.",
        "companion_accuse_submit": "Confirmar la acusación",
        "companion_accuse_confirm": "¿Confirmar estas respuestas? Después no podréis cambiarlas.",
        "companion_accuse_incomplete": "Primero responded todas las preguntas.",
        "companion_score": "{points} de {max} puntos",
        "companion_question_right": "Acierto",
        "companion_question_wrong": "Error",
        "companion_reveal_heading": "Cómo podíais saberlo",
        "companion_ending_heading": "El final",
        "companion_final_solved": "¡Habéis resuelto el último enigma!",
        "companion_no_puzzles": "Todavía no hay ningún enigma abierto.",
        "companion_locked_note": "Aquí aparecerán más enigmas cuando abráis el siguiente sobre.",
        "companion_reset": "Empezar de nuevo",
        "companion_reset_confirm": "¿Borrar todo el progreso de este dispositivo y empezar de nuevo?",
        "companion_storage_off": "Este navegador no guarda vuestro progreso. Mantened esta página abierta.",
        "companion_help_1": "Leed la introducción en voz alta y poned en marcha el reloj.",
        "companion_help_2": "Abrid un sobre solo cuando el juego os lo diga.",
        "companion_help_3": (
            "Cuando tengáis una respuesta, escribidla en Comprobar. Los espacios, los acentos y las mayúsculas no "
            "importan."
        ),
        "companion_help_4": "¿Atascados? Las pistas muestran un pequeño paso cada vez. La respuesta llega al final.",
        "companion_help_5": "Soluciones lo muestra todo. Usadlo al final, o cuando todo el grupo esté de acuerdo.",
        "companion_close": "Cerrar",
    },
    "ca": {
        "companion_page_label": "Company de joc",
        "companion_tab_start": "Inici",
        "companion_tab_check": "Comprovar",
        "companion_tab_hints": "Pistes",
        "companion_tab_accuse": "Acusar",
        "companion_tab_solutions": "Solucions",
        "companion_tab_help": "Com es juga",
        "companion_read_aloud": "Llegiu-ho en veu alta",
        "companion_intro_more": "Llegir tota la introducció",
        "companion_game_length": "Uns {minutes} minuts",
        "companion_timer_label": "Temps restant",
        "companion_timer_overtime": "Temps extra",
        "companion_timer_start": "Engegar el rellotge",
        "companion_timer_pause": "Pausa",
        "companion_timer_resume": "Continuar",
        "companion_envelopes_heading": "Sobres",
        "companion_envelope_open": "Obert",
        "companion_envelope_sealed": "Tancat",
        "companion_check_heading": "Comprovar una resposta",
        "companion_check_puzzle_label": "Codi de l'enigma",
        "companion_check_answer_label": "La vostra resposta",
        "companion_check_submit": "Comprovar",
        "companion_result_correct": "Correcte!",
        "companion_result_near": "Gairebé",
        "companion_result_wrong": "No és això. Torneu-ho a provar.",
        "companion_result_solved": "Resolt",
        "companion_unlock_call": "Obriu ara: {envelope}",
        "companion_hints_heading": "Pistes",
        "companion_hints_intro": "Primer intenteu-ho. Cada pista mostra un petit pas.",
        "companion_hint_show": "Mostrar la pista {level}",
        "companion_hint_label": "Pista {level}",
        "companion_hint_confirm": "Voleu veure la pista {level} de l'enigma {code}?",
        "companion_answer_show": "Mostrar la resposta",
        "companion_answer_confirm": (
            "Voleu veure la resposta completa de l'enigma {code}? Això desvela l'enigma a tot el grup."
        ),
        "companion_confirm_yes": "Sí, mostra-ho",
        "companion_confirm_no": "Encara no",
        "companion_solutions_warning_title": "Compte: solucions",
        "companion_solutions_warning_text": (
            "Aquesta pàgina mostra les solucions completes. Obriu-ne una només quan tot el grup hi estigui d'acord."
        ),
        "companion_solutions_enter": "Ho entenc. Mostra la llista.",
        "companion_solution_show": "Mostrar la solució de {code}",
        "companion_solution_answer": "Resposta: {answer}",
        "companion_accuse_heading": "L'acusació",
        "companion_accuse_intro": "Poseu-vos d'acord en cada pregunta i després confirmeu l'acusació.",
        "companion_accuse_early": "La majoria de grups acusen després de resoldre l'últim enigma.",
        "companion_accuse_submit": "Confirmar l'acusació",
        "companion_accuse_confirm": "Voleu confirmar aquestes respostes? Després no les podreu canviar.",
        "companion_accuse_incomplete": "Primer responeu totes les preguntes.",
        "companion_score": "{points} de {max} punts",
        "companion_question_right": "Encert",
        "companion_question_wrong": "Error",
        "companion_reveal_heading": "Com ho podíeu saber",
        "companion_ending_heading": "El final",
        "companion_final_solved": "Heu resolt l'últim enigma!",
        "companion_no_puzzles": "Encara no hi ha cap enigma obert.",
        "companion_locked_note": "Aquí apareixeran més enigmes quan obriu el sobre següent.",
        "companion_reset": "Tornar a començar",
        "companion_reset_confirm": "Voleu esborrar tot el progrés d'aquest dispositiu i tornar a començar?",
        "companion_storage_off": "Aquest navegador no desa el vostre progrés. Mantingueu aquesta pàgina oberta.",
        "companion_help_1": "Llegiu la introducció en veu alta i engegueu el rellotge.",
        "companion_help_2": "Obriu un sobre només quan el joc us ho digui.",
        "companion_help_3": (
            "Quan tingueu una resposta, escriviu-la a Comprovar. Els espais, els accents i les majúscules no importen."
        ),
        "companion_help_4": "Encallats? Les pistes mostren un petit pas cada vegada. La resposta arriba al final.",
        "companion_help_5": "Solucions ho mostra tot. Feu-ho servir al final, o quan tot el grup hi estigui d'acord.",
        "companion_close": "Tancar",
    },
    "fr": {
        "companion_page_label": "Compagnon de jeu",
        "companion_tab_start": "Début",
        "companion_tab_check": "Vérifier",
        "companion_tab_hints": "Indices",
        "companion_tab_accuse": "Accuser",
        "companion_tab_solutions": "Solutions",
        "companion_tab_help": "Comment jouer",
        "companion_read_aloud": "Lisez ce texte à voix haute",
        "companion_intro_more": "Lire toute l'introduction",
        "companion_game_length": "Environ {minutes} minutes",
        "companion_timer_label": "Temps restant",
        "companion_timer_overtime": "Temps supplémentaire",
        "companion_timer_start": "Lancer le chrono",
        "companion_timer_pause": "Pause",
        "companion_timer_resume": "Reprendre",
        "companion_envelopes_heading": "Enveloppes",
        "companion_envelope_open": "Ouverte",
        "companion_envelope_sealed": "Fermée",
        "companion_check_heading": "Vérifier une réponse",
        "companion_check_puzzle_label": "Code de l'énigme",
        "companion_check_answer_label": "Votre réponse",
        "companion_check_submit": "Vérifier",
        "companion_result_correct": "Correct !",
        "companion_result_near": "Presque",
        "companion_result_wrong": "Pas tout à fait. Essayez encore.",
        "companion_result_solved": "Résolue",
        "companion_unlock_call": "Ouvrez maintenant : {envelope}",
        "companion_hints_heading": "Indices",
        "companion_hints_intro": "Essayez d'abord. Chaque indice montre un petit pas.",
        "companion_hint_show": "Voir l'indice {level}",
        "companion_hint_label": "Indice {level}",
        "companion_hint_confirm": "Voir l'indice {level} de l'énigme {code} ?",
        "companion_answer_show": "Voir la réponse",
        "companion_answer_confirm": (
            "Voir la réponse complète de l'énigme {code} ? Cela gâche l'énigme pour tout le groupe."
        ),
        "companion_confirm_yes": "Oui, montrer",
        "companion_confirm_no": "Pas encore",
        "companion_solutions_warning_title": "Attention : solutions",
        "companion_solutions_warning_text": (
            "Cette page montre les solutions complètes. N'en ouvrez une que si tout le groupe est d'accord."
        ),
        "companion_solutions_enter": "J'ai compris. Montrer la liste.",
        "companion_solution_show": "Voir la solution de {code}",
        "companion_solution_answer": "Réponse : {answer}",
        "companion_accuse_heading": "L'accusation",
        "companion_accuse_intro": "Mettez-vous d'accord sur chaque question, puis validez votre accusation.",
        "companion_accuse_early": "La plupart des groupes accusent après avoir résolu la dernière énigme.",
        "companion_accuse_submit": "Valider l'accusation",
        "companion_accuse_confirm": "Valider ces réponses ? Vous ne pourrez plus les changer.",
        "companion_accuse_incomplete": "Répondez d'abord à toutes les questions.",
        "companion_score": "{points} sur {max} points",
        "companion_question_right": "Juste",
        "companion_question_wrong": "Faux",
        "companion_reveal_heading": "Comment vous auriez pu le savoir",
        "companion_ending_heading": "La fin",
        "companion_final_solved": "Vous avez résolu la dernière énigme !",
        "companion_no_puzzles": "Aucune énigme n'est encore ouverte.",
        "companion_locked_note": "D'autres énigmes apparaîtront ici quand vous ouvrirez l'enveloppe suivante.",
        "companion_reset": "Recommencer",
        "companion_reset_confirm": "Effacer toute la progression sur cet appareil et recommencer ?",
        "companion_storage_off": "Ce navigateur n'enregistre pas votre progression. Gardez cette page ouverte.",
        "companion_help_1": "Lisez l'introduction à voix haute, puis lancez le chrono.",
        "companion_help_2": "N'ouvrez une enveloppe que lorsque le jeu vous le dit.",
        "companion_help_3": (
            "Quand vous avez une réponse, tapez-la dans Vérifier. Les espaces, les accents et les majuscules ne "
            "comptent pas."
        ),
        "companion_help_4": "Bloqués ? Les indices montrent un petit pas à la fois. La réponse vient en dernier.",
        "companion_help_5": "Solutions montre tout. Utilisez-le à la fin, ou quand tout le groupe est d'accord.",
        "companion_close": "Fermer",
    },
    "de": {
        "companion_page_label": "Spielbegleiter",
        "companion_tab_start": "Start",
        "companion_tab_check": "Prüfen",
        "companion_tab_hints": "Tipps",
        "companion_tab_accuse": "Anklagen",
        "companion_tab_solutions": "Lösungen",
        "companion_tab_help": "Spielregeln",
        "companion_read_aloud": "Lest diesen Text laut vor",
        "companion_intro_more": "Die ganze Einleitung lesen",
        "companion_game_length": "Etwa {minutes} Minuten",
        "companion_timer_label": "Restzeit",
        "companion_timer_overtime": "Nachspielzeit",
        "companion_timer_start": "Uhr starten",
        "companion_timer_pause": "Pause",
        "companion_timer_resume": "Weiter",
        "companion_envelopes_heading": "Umschläge",
        "companion_envelope_open": "Offen",
        "companion_envelope_sealed": "Verschlossen",
        "companion_check_heading": "Eine Antwort prüfen",
        "companion_check_puzzle_label": "Rätselcode",
        "companion_check_answer_label": "Eure Antwort",
        "companion_check_submit": "Prüfen",
        "companion_result_correct": "Richtig!",
        "companion_result_near": "Fast",
        "companion_result_wrong": "Nicht ganz. Versucht es noch einmal.",
        "companion_result_solved": "Gelöst",
        "companion_unlock_call": "Jetzt öffnen: {envelope}",
        "companion_hints_heading": "Tipps",
        "companion_hints_intro": "Versucht es zuerst selbst. Jeder Tipp zeigt einen kleinen Schritt.",
        "companion_hint_show": "Tipp {level} zeigen",
        "companion_hint_label": "Tipp {level}",
        "companion_hint_confirm": "Tipp {level} für Rätsel {code} zeigen?",
        "companion_answer_show": "Antwort zeigen",
        "companion_answer_confirm": (
            "Die ganze Antwort für Rätsel {code} zeigen? Damit ist das Rätsel für die ganze Gruppe verraten."
        ),
        "companion_confirm_yes": "Ja, zeigen",
        "companion_confirm_no": "Noch nicht",
        "companion_solutions_warning_title": "Achtung: Lösungen",
        "companion_solutions_warning_text": (
            "Diese Seite zeigt die ganzen Lösungen. Öffnet eine nur, wenn die ganze Gruppe einverstanden ist."
        ),
        "companion_solutions_enter": "Verstanden. Liste zeigen.",
        "companion_solution_show": "Lösung für {code} zeigen",
        "companion_solution_answer": "Antwort: {answer}",
        "companion_accuse_heading": "Die Anklage",
        "companion_accuse_intro": "Einigt euch bei jeder Frage auf eine Antwort und bestätigt dann eure Anklage.",
        "companion_accuse_early": "Die meisten Gruppen klagen an, nachdem sie das letzte Rätsel gelöst haben.",
        "companion_accuse_submit": "Anklage bestätigen",
        "companion_accuse_confirm": "Diese Antworten bestätigen? Danach könnt ihr sie nicht mehr ändern.",
        "companion_accuse_incomplete": "Beantwortet zuerst alle Fragen.",
        "companion_score": "{points} von {max} Punkten",
        "companion_question_right": "Richtig",
        "companion_question_wrong": "Falsch",
        "companion_reveal_heading": "Woran ihr es hättet erkennen können",
        "companion_ending_heading": "Das Ende",
        "companion_final_solved": "Ihr habt das letzte Rätsel gelöst!",
        "companion_no_puzzles": "Noch ist kein Rätsel offen.",
        "companion_locked_note": "Weitere Rätsel erscheinen hier, wenn ihr den nächsten Umschlag öffnet.",
        "companion_reset": "Neu beginnen",
        "companion_reset_confirm": "Den ganzen Fortschritt auf diesem Gerät löschen und neu beginnen?",
        "companion_storage_off": "Dieser Browser speichert euren Fortschritt nicht. Lasst diese Seite offen.",
        "companion_help_1": "Lest die Einleitung laut vor und startet dann die Uhr.",
        "companion_help_2": "Öffnet einen Umschlag erst, wenn das Spiel es euch sagt.",
        "companion_help_3": (
            "Wenn ihr eine Antwort habt, gebt sie unter Prüfen ein. Leerzeichen, Akzente und Großbuchstaben sind egal."
        ),
        "companion_help_4": "Kommt ihr nicht weiter? Tipps zeigen einen kleinen Schritt nach dem anderen. Die Antwort "
        "kommt zuletzt.",
        "companion_help_5": "Lösungen zeigt alles. Nutzt es am Ende, oder wenn die ganze Gruppe einverstanden ist.",
        "companion_close": "Schließen",
    },
    "it": {
        "companion_page_label": "Compagno di gioco",
        "companion_tab_start": "Inizio",
        "companion_tab_check": "Verifica",
        "companion_tab_hints": "Indizi",
        "companion_tab_accuse": "Accusa",
        "companion_tab_solutions": "Soluzioni",
        "companion_tab_help": "Come si gioca",
        "companion_read_aloud": "Leggete questo testo ad alta voce",
        "companion_intro_more": "Leggi tutta l'introduzione",
        "companion_game_length": "Circa {minutes} minuti",
        "companion_timer_label": "Tempo rimasto",
        "companion_timer_overtime": "Tempo extra",
        "companion_timer_start": "Avvia il cronometro",
        "companion_timer_pause": "Pausa",
        "companion_timer_resume": "Riprendi",
        "companion_envelopes_heading": "Buste",
        "companion_envelope_open": "Aperta",
        "companion_envelope_sealed": "Chiusa",
        "companion_check_heading": "Verifica una risposta",
        "companion_check_puzzle_label": "Codice dell'enigma",
        "companion_check_answer_label": "La vostra risposta",
        "companion_check_submit": "Verifica",
        "companion_result_correct": "Giusto!",
        "companion_result_near": "Quasi",
        "companion_result_wrong": "Non proprio. Riprovate.",
        "companion_result_solved": "Risolto",
        "companion_unlock_call": "Aprite ora: {envelope}",
        "companion_hints_heading": "Indizi",
        "companion_hints_intro": "Provate prima da soli. Ogni indizio mostra un piccolo passo.",
        "companion_hint_show": "Mostra l'indizio {level}",
        "companion_hint_label": "Indizio {level}",
        "companion_hint_confirm": "Mostrare l'indizio {level} dell'enigma {code}?",
        "companion_answer_show": "Mostra la risposta",
        "companion_answer_confirm": (
            "Mostrare la risposta completa dell'enigma {code}? Così l'enigma è svelato per tutto il gruppo."
        ),
        "companion_confirm_yes": "Sì, mostra",
        "companion_confirm_no": "Non ancora",
        "companion_solutions_warning_title": "Attenzione: soluzioni",
        "companion_solutions_warning_text": (
            "Questa pagina mostra le soluzioni complete. Apritene una solo se tutto il gruppo è d'accordo."
        ),
        "companion_solutions_enter": "Ho capito. Mostra l'elenco.",
        "companion_solution_show": "Mostra la soluzione di {code}",
        "companion_solution_answer": "Risposta: {answer}",
        "companion_accuse_heading": "L'accusa",
        "companion_accuse_intro": "Mettetevi d'accordo su ogni domanda, poi confermate l'accusa.",
        "companion_accuse_early": "Quasi tutti i gruppi accusano dopo aver risolto l'ultimo enigma.",
        "companion_accuse_submit": "Conferma l'accusa",
        "companion_accuse_confirm": "Confermare queste risposte? Dopo non potrete cambiarle.",
        "companion_accuse_incomplete": "Prima rispondete a tutte le domande.",
        "companion_score": "{points} su {max} punti",
        "companion_question_right": "Giusto",
        "companion_question_wrong": "Sbagliato",
        "companion_reveal_heading": "Come potevate capirlo",
        "companion_ending_heading": "Il finale",
        "companion_final_solved": "Avete risolto l'ultimo enigma!",
        "companion_no_puzzles": "Nessun enigma è ancora aperto.",
        "companion_locked_note": "Altri enigmi appariranno qui quando aprirete la busta successiva.",
        "companion_reset": "Ricomincia",
        "companion_reset_confirm": "Cancellare tutti i progressi su questo dispositivo e ricominciare?",
        "companion_storage_off": "Questo browser non salva i vostri progressi. Tenete aperta questa pagina.",
        "companion_help_1": "Leggete l'introduzione ad alta voce, poi avviate il cronometro.",
        "companion_help_2": "Aprite una busta solo quando il gioco ve lo dice.",
        "companion_help_3": (
            "Quando avete una risposta, scrivetela in Verifica. Spazi, accenti e maiuscole non contano."
        ),
        "companion_help_4": "Bloccati? Gli indizi mostrano un piccolo passo alla volta. La risposta arriva per ultima.",
        "companion_help_5": "Soluzioni mostra tutto. Usatelo alla fine, o quando tutto il gruppo è d'accordo.",
        "companion_close": "Chiudi",
    },
    "pt": {
        "companion_page_label": "Companheiro de jogo",
        "companion_tab_start": "Início",
        "companion_tab_check": "Verificar",
        "companion_tab_hints": "Pistas",
        "companion_tab_accuse": "Acusar",
        "companion_tab_solutions": "Soluções",
        "companion_tab_help": "Como jogar",
        "companion_read_aloud": "Leiam isto em voz alta",
        "companion_intro_more": "Ler toda a introdução",
        "companion_game_length": "Cerca de {minutes} minutos",
        "companion_timer_label": "Tempo restante",
        "companion_timer_overtime": "Tempo extra",
        "companion_timer_start": "Iniciar o relógio",
        "companion_timer_pause": "Pausa",
        "companion_timer_resume": "Continuar",
        "companion_envelopes_heading": "Envelopes",
        "companion_envelope_open": "Aberto",
        "companion_envelope_sealed": "Fechado",
        "companion_check_heading": "Verificar uma resposta",
        "companion_check_puzzle_label": "Código do enigma",
        "companion_check_answer_label": "A vossa resposta",
        "companion_check_submit": "Verificar",
        "companion_result_correct": "Correto!",
        "companion_result_near": "Quase",
        "companion_result_wrong": "Não é bem isso. Tentem outra vez.",
        "companion_result_solved": "Resolvido",
        "companion_unlock_call": "Abram agora: {envelope}",
        "companion_hints_heading": "Pistas",
        "companion_hints_intro": "Tentem primeiro. Cada pista mostra um pequeno passo.",
        "companion_hint_show": "Mostrar a pista {level}",
        "companion_hint_label": "Pista {level}",
        "companion_hint_confirm": "Mostrar a pista {level} do enigma {code}?",
        "companion_answer_show": "Mostrar a resposta",
        "companion_answer_confirm": (
            "Mostrar a resposta completa do enigma {code}? Isto revela o enigma a todo o grupo."
        ),
        "companion_confirm_yes": "Sim, mostrar",
        "companion_confirm_no": "Ainda não",
        "companion_solutions_warning_title": "Atenção: soluções",
        "companion_solutions_warning_text": (
            "Esta página mostra as soluções completas. Abram uma só quando todo o grupo concordar."
        ),
        "companion_solutions_enter": "Entendi. Mostrar a lista.",
        "companion_solution_show": "Mostrar a solução de {code}",
        "companion_solution_answer": "Resposta: {answer}",
        "companion_accuse_heading": "A acusação",
        "companion_accuse_intro": "Concordem numa resposta para cada pergunta e depois confirmem a acusação.",
        "companion_accuse_early": "A maioria dos grupos acusa depois de resolver o último enigma.",
        "companion_accuse_submit": "Confirmar a acusação",
        "companion_accuse_confirm": "Confirmar estas respostas? Depois não as podem mudar.",
        "companion_accuse_incomplete": "Respondam primeiro a todas as perguntas.",
        "companion_score": "{points} de {max} pontos",
        "companion_question_right": "Certo",
        "companion_question_wrong": "Errado",
        "companion_reveal_heading": "Como podiam ter sabido",
        "companion_ending_heading": "O final",
        "companion_final_solved": "Resolveram o último enigma!",
        "companion_no_puzzles": "Ainda não há nenhum enigma aberto.",
        "companion_locked_note": "Mais enigmas aparecem aqui quando abrirem o próximo envelope.",
        "companion_reset": "Recomeçar",
        "companion_reset_confirm": "Apagar todo o progresso neste dispositivo e recomeçar?",
        "companion_storage_off": "Este navegador não guarda o vosso progresso. Mantenham esta página aberta.",
        "companion_help_1": "Leiam a introdução em voz alta e depois iniciem o relógio.",
        "companion_help_2": "Abram um envelope só quando o jogo vos disser.",
        "companion_help_3": (
            "Quando tiverem uma resposta, escrevam-na em Verificar. Espaços, acentos e maiúsculas não contam."
        ),
        "companion_help_4": "Encravados? As pistas mostram um pequeno passo de cada vez. A resposta vem no fim.",
        "companion_help_5": "Soluções mostra tudo. Usem no fim, ou quando todo o grupo concordar.",
        "companion_close": "Fechar",
    },
}
for _language, _companion_texts in COMPANION_STRINGS.items():
    STRINGS[_language].update(_companion_texts)

MONTHS: Final[dict[str, tuple[str, ...]]] = {
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
    "es": (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ),
    "ca": (
        "gener", "febrer", "març", "abril", "maig", "juny",
        "juliol", "agost", "setembre", "octubre", "novembre", "desembre",
    ),
    "fr": (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ),
    "de": (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ),
    "it": (
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ),
    "pt": (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ),
}  # fmt: skip

WEEKDAYS: Final[dict[str, tuple[str, ...]]] = {
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"),
    "ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
    "fr": ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"),
    "de": ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"),
    "it": ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"),
    "pt": ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"),
}

# Each pattern receives the day number, the month name, and the year.
DATE_PATTERNS: Final[dict[str, str]] = {
    "en": "{day} {month} {year}",
    "es": "{day} de {month} de {year}",
    "ca": "{day} de {month} de {year}",
    "fr": "{day} {month} {year}",
    "de": "{day}. {month} {year}",
    "it": "{day} {month} {year}",
    "pt": "{day} de {month} de {year}",
}


class LanguagePack(BaseModel):
    """The fixed texts of one language that has no checked table here. The generator translates the English pack
    into `source/strings.json` once per game, and the toolkit checks it before it uses it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strings: dict[str, str]
    months: list[str] = Field(min_length=12, max_length=12)
    weekdays: list[str] = Field(min_length=7, max_length=7)
    date_pattern: str


DATE_FIELDS: Final[frozenset[str]] = frozenset({"day", "month", "year"})
# A Japanese pack may print era years instead (昭和33年), when the story counts years by era too.
ERA_DATE_FIELDS: Final[frozenset[str]] = frozenset({"day", "month", "era_year"})
# The first day of each Japanese era, newest first.
JAPANESE_ERAS: Final[tuple[tuple[datetime, str], ...]] = (
    (datetime(2019, 5, 1), "令和"),
    (datetime(1989, 1, 8), "平成"),
    (datetime(1926, 12, 25), "昭和"),
    (datetime(1912, 7, 30), "大正"),
    (datetime(1868, 10, 23), "明治"),
)
# The texts that name the exported files. Windows refuses these characters in a file name.
FILE_NAME_PREFIX: Final[str] = "file_"
FORBIDDEN_FILE_CHARACTERS: Final[frozenset[str]] = frozenset(r'<>:"/\|?*')


def language_pack_template() -> LanguagePack:
    return LanguagePack(
        strings=dict(STRINGS["en"]),
        months=list(MONTHS["en"]),
        weekdays=list(WEEKDAYS["en"]),
        date_pattern=DATE_PATTERNS["en"],
    )


def placeholders(value: str) -> list[str]:
    return sorted({field for _, field, _, _ in Formatter().parse(value) if field})


def language_pack_problems(pack: LanguagePack) -> list[str]:
    """Return what a translated pack lost or changed: a key, a {field} that the code fills, or a date field."""
    english: dict[str, str] = STRINGS["en"]
    problems: list[str] = [f"The key '{key}' is missing." for key in english if key not in pack.strings]
    problems += [f"The key '{key}' is not a fixed text." for key in pack.strings if key not in english]
    for key, value in pack.strings.items():
        expected: list[str] = placeholders(english.get(key, value))
        found: list[str] = placeholders(value)
        if found != expected:
            listed: str = ", ".join(f"{{{name}}}" for name in expected) or "no field"
            given: str = ", ".join(f"{{{name}}}" for name in found) or "no field"
            problems.append(f"The text '{key}' must keep the fields {listed}, not {given}.")
    for key, value in pack.strings.items():
        if key.startswith(FILE_NAME_PREFIX):
            forbidden: list[str] = sorted({character for character in value if character in FORBIDDEN_FILE_CHARACTERS})
            if forbidden:
                listed_characters: str = ", ".join(f"'{character}'" for character in forbidden)
                problems.append(f"The file name '{key}' holds a character that file names forbid: {listed_characters}.")
    if set(placeholders(pack.date_pattern)) not in (DATE_FIELDS, ERA_DATE_FIELDS):
        problems.append("The date pattern must hold {day}, {month}, and {year} (or {era_year}, the Japanese era year).")
    return problems


def register_language(language: str, pack: LanguagePack) -> None:
    """Serve a checked pack for this language, for the rest of this process."""
    STRINGS[language] = dict(pack.strings)
    MONTHS[language] = tuple(pack.months)
    WEEKDAYS[language] = tuple(pack.weekdays)
    DATE_PATTERNS[language] = pack.date_pattern


# Languages whose script runs from right to left; the pages set `dir="rtl"` for them.
RIGHT_TO_LEFT_LANGUAGES: Final[frozenset[str]] = frozenset({"ar", "he", "fa", "ur"})


def text_direction(language: str) -> str:
    return "rtl" if language in RIGHT_TO_LEFT_LANGUAGES else "ltr"


# Game languages that are not written in the Latin alphabet (Serbian counts here, because Cyrillic is its official
# script). The mechanics that fold text to A to Z cannot hide their answers.
NON_LATIN_LANGUAGES: Final[frozenset[str]] = frozenset(
    {"ar", "bg", "bn", "el", "fa", "he", "hi", "ja", "ko", "ru", "sr", "ta", "th", "uk", "ur", "zh"}
)


def known_language(language: str) -> str:
    return language if language in STRINGS else "en"


def text(language: str, key: str, solo: bool = False, **values: str) -> str:
    """Return the fixed text `key` in the language, with `{name}` fields filled from `values`.

    A solo game takes the `<key>_solo` text when one exists, such as "1 player" instead of "1 players".
    """
    strings: dict[str, str] = STRINGS[known_language(language)]
    if key not in strings:
        raise KeyError(f"No fixed text named '{key}'.")
    chosen: str = f"{key}_solo" if solo and f"{key}_solo" in strings else key
    return strings[chosen].format(**values)


def join_list(language: str, items: list[str]) -> str:
    """Return the items as one phrase, such as "a, b, and c" in English or "a, b y c" in Spanish."""
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return text(language, "list_two", first=items[0], last=items[1])
    return text(language, "list_many", items=text(language, "list_separator").join(items[:-1]), last=items[-1])


def format_date(moment: datetime, language: str) -> str:
    """Return a long date such as "14 de marzo de 1931", or "昭和33年3月14日" for a pattern with {era_year}."""
    chosen: str = known_language(language)
    month: str = MONTHS[chosen][moment.month - 1]
    return DATE_PATTERNS[chosen].format(
        day=moment.day, month=month, year=moment.year, era_year=japanese_era_year(moment)
    )


def uses_era_years(language: str) -> bool:
    """True when the toolkit prints the dates of this language with Japanese era years."""
    return "era_year" in placeholders(DATE_PATTERNS[known_language(language)])


def japanese_era_year(moment: datetime) -> str:
    """The Japanese era and the year in it, such as "昭和33". The first year of an era is "元".

    A date before the Meiji era gets the plain year.
    """
    for start, era in JAPANESE_ERAS:
        if moment >= start:
            number: int = moment.year - start.year + 1
            return f"{era}{'元' if number == 1 else number}"
    return str(moment.year)


def weekday_name(moment: datetime, language: str) -> str:
    return WEEKDAYS[known_language(language)][moment.weekday()]
