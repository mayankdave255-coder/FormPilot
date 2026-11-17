# FormPilot: open tasks

Status: the app was not runnable before this review (a syntax error in `app.js` stopped the whole UI). It now runs end to end in demo mode, with 37 backend tests and 10 frontend tests passing. The items below are what is still open.

## Must do before the demo

1. **Run it on your own machine.** Use `.\run.ps1` on Windows, open http://127.0.0.1:8000 in Chrome, and click through all five screens. I could only test in Linux with jsdom, not in a real browser.
2. **Test camera and microphone on a phone.** The scanner, voice recording and the mobile layout have never been run on a real device. Mic and camera need HTTPS or localhost.
3. **Test live providers if you have keys.** Add `GEMINI_API_KEY` and `SARVAM_API_KEY` to `.env`. The Gemini and Sarvam calls (model names `saaras:v4` and `bulbul:v4-flash`, the `doc_ai` SDK calls, the speaker names) were not run, so check them against the current provider docs.
4. **Make three sample PDFs for the demo:** an application form with labelled fields, a marksheet containing `Student Name: Rahul Kumar`, and an income certificate. Rehearse the name mismatch story with them.
5. **Record a 60 to 90 second backup video** of the full flow in case Wi-Fi or provider calls fail on demo day.

## Decide and finish (the scripted parts of the UI)

6. **Readiness screen.** Its name-mismatch card, document checklist and answer summary still use the hardcoded Rahul Kumar data in `fields` and `state.docsPresent`. Only the new "Checks from the server" card is live. Either connect the rest to `/readiness`, or present that screen as a scripted demo.
7. **Upload buttons for marksheet and bank proof.** The UI only uploads the application and the income certificate, so the real mismatch check cannot trigger from the UI. Use `pickSupporting('marksheet')` as the pattern, and add `marksheet` and `bank_proof` handling in `validation_for` if you want them required.
8. **Guided assistant.** It cycles through 3 questions (income, date of birth, name), not every detected field. Drive it from `state.formFields`.
9. **Hardcoded details.** "Page X of 4", the preview paper, "Updated today at 10:43 AM" and the second "Recent applications" row are placeholders.

## Before sharing a public link

10. **Deployment.** Sessions live in memory and files on local disk, so run one worker on a host that keeps a process alive (Render, Railway, Fly, a VPS, Docker). Vercel serverless will lose sessions between requests.
11. Set `CORS_ORIGINS` to your real domain instead of `*`.
12. Keep the "do not upload real IDs" warning visible, and use only fictional documents in the demo.

## Nice to have

13. Hindi in the draft PDF is readable but uses basic glyph shaping (ReportLab has no complex-script support). Eyeball a longer address.
14. `.agents/skills/unslop/` is a writing-style helper unrelated to the app. Remove it from your submission if judges will see the repo.
15. Add a GitHub Actions workflow to run `python -m pytest -q`.
