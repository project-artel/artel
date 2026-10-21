# Git Language

Commits and pull requests settle which language a sentence is written in. Word
choice reaches further than that, into code comments, test names, and issue
bodies as well.

## Commits

- Write commit titles and bodies in Korean.
- Keep the Conventional Commit type and optional scope in English.
- Keep code identifiers, file paths, commands, log output, error strings, API names, and technical terms in their canonical English form.

## Pull Requests

- Write pull request titles and bodies in Korean.
- Keep the Conventional Commit type and optional scope in English.
- Keep code identifiers, file paths, commands, log output, error strings, API names, technical terms, and template section headings in their canonical English form.

## Titles

Follow the title rules in [writing-style.md](writing-style.md). Name the affected
thing and the change, and give the number when it matters. End Korean work-item
titles with a noun such as `추가`, `수정`, `적용`, or `이동`, not `~한다`.
This applies to commit subjects, pull request titles, Jira summaries, and
headings in documents or decks. Keep the Conventional Commit type in English.

- Epic: `QA run 결과 재생 지원`
- Story: `QA agent context에 pulse 추가`
- Task: `SceneMemory에 pulse 프레임 누적`

Avoid aphorisms, rhetorical questions, and metaphors. Prefer
`fix(qa): QA run 재시도 3회로 제한` to an abstract claim about stability.

## Word Choice

This section is about the words you pick when you write about this code: the
verbs, and the nouns for things the code never named. A thing the code does
name keeps the name the code gave it — `pulse`, `screen`, `capability`,
`anchor` — in backticks, even inside a Korean sentence.

It applies wherever that writing lands: line and block comments, KDoc and
docstrings, SQL comments, test names, commit messages, and issue and pull
request bodies.

**Never invent a Korean word to carry a technical meaning.** Verbs count as
much as nouns. The test is not whether a Korean rendering is possible. It is
whether a Korean speaker who has not read the code would use that word for
this. `발화하다` for `fire` fails it: nobody who has not read the file knows
what it means.

Where the ordinary Korean word is exact, use it. Merging two duplicate `screen`
rows really is `합친다` — `접는다` was reached for because it sounded closer to
the code, and it left the sentence harder to read and no more precise. Where
reaching for a Korean word produces something you had to make up, write the
English word instead. English is a safe answer. A made-up word never is.

**Pick the word that is correct, not the word that sounds considered.** Test a
word by asking whether it actually means this, not whether it sounds right in
the sentence. `capture 를 청구한다` is wrong because `청구` is the word for
collecting money; asking the SDK to take a screen capture is `요청`. Commonness
only breaks a tie: when two words are both correct, take the one the reader
already knows — `만들어낸 말` over `조어`. Never take a vague common word over
an exact one. A sentence that reads smoothly and says nothing is the worse
failure of the two.

**Prefer the precise term over the short ambiguous one**, especially where the
short one already means something else nearby. In prose write `screen capture`,
not `capture`: `content_map` also has a `capture` field whose values are
`editor`, `editor-play`, and `player`, and a reader cannot tell which one a
bare `capture` meant. Identifiers keep the names they have; this is about the
prose around them.

**Write concretely.** Name the thing, say what happens, give the number.
`재시도는 3회까지` beats `적절히 재시도한다`. Figurative or grand phrasing hides
whether the sentence is even true, and a reviewer cannot check a metaphor. A
short plain sentence with a number in it beats a well-turned one.

None of this asks for more Korean. It asks you to stop making words up. Leave
English where English reads naturally.

Existing text is not a defect to sweep. Words like these are already spread
through comments, documents, and branch names here; that is history, not a
standard. Fix the wording in text you are already writing, and leave the file
around it alone.
