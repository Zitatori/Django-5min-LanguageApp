# Japanese Study Cheatsheets

## Integration

- `/study-cheatsheets/` lists the owner's saved sheets and latest content; POST creates a sheet for one completed Japanese lesson. `/study-cheatsheets/<uuid>/` provides the full sheet, lesson-history anchor, and older/newer navigation.
- Home, lesson history and existing AI Study Notes link to the new interface. Existing study materials and the conversation experience remain intact.
- Existing Gold membership rules apply to generation; saved materials remain readable by the owner after Gold expires. Administrators (staff or the existing Admin role) can review saved materials using separate read-only Admin Dashboard routes; ordinary tutors cannot. Raw private notes and evidence quotes are not exposed by those routes. There is no monthly generation limit.
- The source is the actual tutor's latest `ConversationNote` for the selected match: `conversation_content`, `learner_level`, and `next_conversation`. The database currently has no separate field named tutor “Private Notes.” The student's `student_private_note` is never included in this feature.
- A recorded A1–C2 assessment and lesson content are required. The learner cannot override the assessment. Up to four earlier lesson notes and eight earlier cheatsheets provide bounded progression context. Previously generated content does **not** imply mastery.

## Generation and validation

Uses the existing Responses API transport and settings. No new API key or package is required in production. Existing settings:

- `OPENAI_API_KEY`
- `OPENAI_STUDY_MODEL` (existing default `gpt-4.1-mini`)
- `OPENAI_STUDY_MAX_OUTPUT_TOKENS` (default 3600)
- `OPENAI_STUDY_TIMEOUT_SECONDS` (default 20, shared budget for generation and review)

Generation returns strict JSON, not executable markup. A second short model request independently checks grounding, difficulty, reading correspondence, privacy and recommendations. Logs contain model/status/token totals, never prompts, notes, keys or output. Both calls count towards API costs.

All displayed generated text uses the same `{text, kana, romaji}` component. A1/A2 Japanese text is recursively checked for missing, non-Latin or truncated romaji and kanji in kana fields. Romaji appears immediately below the Japanese text. Schema limits, per-level curriculum topic IDs, bounded sentence length, exact source evidence, and a semantic review fail closed. Control characters and escaped code-point text are rejected. Evidence is removed before persistence and never rendered. Automated semantic checks reduce errors but cannot prove pedagogical quality or perfect pronunciation; learners are told to check uncertainties with a tutor.

Vocabulary and grammar may be shorter than the requested 3–5 / 1–2 counts if the tutor did not document enough material. Review and new practice/recommendations are visibly separated. Every sheet has a two-day, 5–10 minute per day plan.

Progression is an original conservative teaching sequence informed by [GENKI's published syllabus](https://bookclub2.japantimes.co.jp/download/files/genki3/genki-3rd_syllabus_E.pdf). It is not copied textbook content or an official CEFR–textbook equivalence. [JLPT's CEFR reference](https://www.jlpt.jp/e/about/cefr_reference.html) concerns language knowledge and reception; it is not used to override tutor-assessed speaking proficiency.

Structured output reference: https://developers.openai.com/api/docs/guides/structured-outputs

## Database and deployment

Migration `0027_study_cheatsheets` adds `StudyNote.format` (legacy default `study_note`), a nullable `lesson` FK, and a conditional unique constraint for active/ready cheatsheets per owner/lesson. Existing rows are preserved. Failed attempts can be retried using a fresh signed token. The existing user-wide generation claim also prevents overlap with the older study notes feature; abandoned claims expire after five minutes.

Run `python manage.py migrate`, `python manage.py collectstatic --noinput`, and the normal translation compilation during deployment. The existing `build.sh` already runs these operations. Do not deploy Python/template changes without migration 0027.

The `.po` and compiled `.mo` additions cover Japanese, English, French and Spanish. Model explanation language is selected separately from the fixed Japanese learning language.

## Rounded icon assets

`static/icons/quicklesson-rounded-source.png` is the cleaned rounded tile. Tab exports are 16/32 PNG and a 16/32/48 BMP-encoded ICO with transparent corners. PWA `any` icons are 192/512 PNG with transparent corners. A separate opaque white maskable icon keeps the artwork within the safe area; Apple touch uses opaque white corners so iOS can apply its mask. New asset filenames and a manifest version parameter avoid reusing the old files. Existing installed PWAs and Safari may retain their own icon cache after deployment.

The image was edited with built-in ImageGen, then normalized into icon export canvases. Final prompt: “Produce a CLEAN production app icon by editing the reference. Keep the same two birds inside blue stopwatch and exact 5 min lettering. White rounded-square tile with smooth perfect geometric rounded corners. Entire tile inside canvas with 3% transparent margin. The exterior must be 100% transparent, no speckles, no distressing, no sketch outlines, no black pixels, no fringe, no border, no shadow. This is clean app icon export, not a drawing or textured paper. Preserve original image composition, colors, characters.”
