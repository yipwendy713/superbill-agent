# Superbill Voice Agent for Physical Therapists

This is a prototype voice agent that turns a physical therapist's spoken summary of their sessions into draft superbills, one Word document per patient. Built with the [Guava](https://goguava.ai) voice AI SDK at the Guava voice agent hackathon during LA Tech Week (October 2026).

## The problem

Many physical therapists see patients out of network. After each visit, they give the patient a **superbill**, an itemized bill the patient submits to insurance for reimbursement. Filling one out means choosing the right ICD-10 diagnosis code, listing each CPT procedure code, and converting treatment minutes into billable 15-minute units.

It's after-hours admin work, usually done in a batch at the end of a long day, and coding mistakes can get a patient's claim rejected. This project started with an idea from my physical therapist.

## What it does

Here is a [demo video](https://youtu.be/MFq6Ao2RfBU) of the agent.

The PT talks through their sessions, and the agent drafts a superbill for each patient:

> **PT:** "Jane Doe, today, right knee pain, no evaluation. 15 minutes of manual therapy and 30 minutes of therapeutic exercise. No other services."
>
> **Agent:** *(spells the name back to confirm, then gives one summary)* "Today's session: pain in right knee, no evaluation, 15 minutes of manual therapy and 30 minutes of therapeutic exercise. Is that all correct?"
>
> **PT:** "Yes."
>
> **Agent:** "Your draft superbill is saved for review, with a total of $200. Is there another patient's superbill you'd like to work on?"

Each patient's superbill is saved as an editable Word document marked **DRAFT**, with a line for the clinician's signature. The PT reviews it, edits it if needed, and saves it as a PDF for the patient.

## Features

- **Natural dictation.** The PT describes the session in their own words, and the agent only asks about what's missing.
- **Multiple patients per conversation.** After each superbill, the agent asks whether there's another patient, so a day's visits can be done in one sitting.
- **One confirmation at the end.** Only the patient's name is confirmed during the conversation (spelled back letter by letter). Everything else is confirmed once, in a single summary.
- **Diagnosis search with everyday language.** 77 common physical therapy ICD-10-CM codes (FY 2027). Phrases like "frozen shoulder," "tennis elbow," "ACL," or "knee replacement" map to the official codes, and the side the PT mentions (right or left) is preferred.
- **Unit calculation.** Treatment minutes are converted to 15-minute units 
- **Guardrails.** Prices come only from a sample practice's fee schedule. A code with no price is flagged for review, never billed at $0. Every superbill is a draft that needs clinician approval.
- **Privacy.** The patient name field is marked `sensitive`, so Guava redacts it from stored transcripts and recordings. Patient names are kept out of logs and file names.
- **"No other services" shortcut.** When the PT says something like "no other services" or "that's it," the agent stops asking and moves straight to the summary.

## How it works

```
PT speaks ──► Guava voice agent ──► structured fields ──► superbill.py ──► .docx / .json / .html
              (main.py)              (per patient)         (codes, units,
                   │                                         prices, flags)
                   └── diagnosis search (diagnoses.py)
```

| File | What it does |
|---|---|
| `main.py` | The Guava agent: conversation flow, one task per patient, the "another patient?" loop, and the "no other services" shortcut. |
| `superbill.py` | Billing logic with no voice code: fee schedule, minutes-to-units, totals, warnings, and output as Word, JSON, and HTML. |
| `diagnoses.py` | The 77 ICD-10-CM codes and a keyword search with everyday synonyms. |

Each patient gets its own Guava task (`superbill_1`, `superbill_2`, ...) with its own field names (`patient_name_1`, `patient_name_2`, ...), so details from one patient can never carry into the next superbill.

## Running it

**Requirements:** the [Guava CLI](https://docs.goguava.ai/getting-started/quickstart), a Guava account, and Python 3.11 or newer.

```bash
guava login
guava run
```

`guava run` sets up the project environment from `pyproject.toml`, including `python-docx`. If Word output is missing, install it into the project environment:

```bash
.venv/bin/python -m pip install python-docx
```

**Choose how to talk to the agent** at the bottom of `main.py`. Leave exactly one of these uncommented:

- `agent.call_local()`: use your laptop's microphone and speakers (built-in speakers work best).
- `agent.listen_phone("<your Guava number>")`: call the agent's phone number.
- `agent.listen_webrtc()`: talk in the browser.
- `agent.chat()`: type instead of talk, for quick testing.

**Output** goes to the `superbills/` folder: one `.docx` per patient, plus `.json` (structured data) and `.html` copies.

**Test the billing logic without any voice:**

```bash
.venv/bin/python superbill.py    # builds a sample superbill for a fake patient
.venv/bin/python diagnoses.py    # runs sample diagnosis searches
```

## Limitations and next steps

- **One primary diagnosis per superbill.** Some cases, like rehab after a joint replacement, are usually billed with two codes (Z47.1 plus the joint code).
- **Simplified unit rule.** Units are calculated per service. Medicare's 8-minute rule uses total timed minutes across services, which can give different results.
- **GP modifier on every code.** Payer requirements vary.
- **No schedule integration yet.** Next step: pull the day's patients and their last diagnosis, so the PT can say "Jane, same as last time, plus ten minutes of ultrasound."
- **Not production-ready for real patient data.** Real use would need HIPAA-compliant storage, access controls, audit logging, and a Business Associate Agreement with each vendor.

## Disclaimer

This is a hackathon prototype built and tested with made-up patient data.  It is not HIPAA-compliant.  

## Credits

- Voice platform: [Guava](https://goguava.ai)
- Common PT diagnosis list: [Vero Scribe physical therapy ICD-10 reference](https://www.veroscribe.com/icd-10/common-codes/physical-therapy), with descriptions from the CDC/NCHS ICD-10-CM code set
