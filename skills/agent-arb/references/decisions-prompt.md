You are extracting architecture decisions from ONE section of a design document.
Reply with a JSON object only: {"decisions": [...]}.

A decision is a choice the author made that could have gone another way: how data moves, where state lives, how failures are handled, how components are separated, which mechanism secures a path, what is monitored. Do not invent decisions that are not in the text. Skip background, requirements lists and glossary text.

Each decision has:
- "title": short, the choice itself
- "scope": one of "architecture", "design", "implementation"
- "context": why the choice was needed, in one or two sentences from the text
- "options": list of {"name","tradeoff"} for alternatives the text mentions; empty if none are mentioned
- "chosen": the option taken
- "implications": consequences the text states; empty if none
- "evidence_quote": a sentence copied EXACTLY, character for character, from the section that shows this decision
- "tags": from this list only: {tags}
- "data_classes": from this list only, when the section says such data is handled: {data_classes}

If the section contains no decision, reply {"decisions": []}.
