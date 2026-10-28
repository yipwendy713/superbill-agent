"""Superbill voice agent: a physical therapist calls after their sessions,
describes each one, and gets a separate draft superbill (.docx) per patient.
Built from the `guava create` starter.

Flow per call:
    superbill_1 -> "another patient?" -> superbill_2 -> "another patient?" -> ... -> goodbye

Run `guava run` from this folder.
"""

import logging
import re
import sys
from datetime import date
from pathlib import Path

import guava
from guava import logging_utils
from guava.events import BotSessionEnded, CallerSpeechEvent

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))  # so superbill.py is found however this is launched

from diagnoses import search_diagnoses  # noqa: E402
from superbill import build_superbill, save_superbill  # noqa: E402

logger = logging.getLogger("superbill_agent")

agent = guava.Agent(
    name="Sam",
    organization="[Practice Name]",
    purpose=(
        "You help physical therapists create superbills after patient sessions, "
        "one patient at a time. The therapist describes each session out loud, and "
        "you collect the details needed to bill it: patient, date, diagnosis, "
        "evaluation, and the minutes spent on each treatment."
    ),
)

# Timed services the PT might mention: CPT code -> (field key, description)
TIMED_SERVICES = {
    "97140": ("manual_therapy_min", "Minutes of manual therapy"),
    "97110": ("ther_ex_min", "Minutes of therapeutic exercise"),
    "97530": ("ther_activities_min", "Minutes of therapeutic activities"),
    "97112": ("neuro_reed_min", "Minutes of neuromuscular re-education"),
    "97035": ("ultrasound_min", "Minutes of ultrasound"),
    "97032": ("estim_attended_min", "Minutes of attended electrical stimulation"),
}

# Per-call state: which patient we're on, what step, saved superbills.
# {call_id: {"n": 1, "phase": "superbill" | "another", "nudged": False, "saved": [...]}}
_calls = {}


def _key(name, n):
    """Field keys are unique per patient (patient_name_1, patient_name_2, ...) so
    one patient's answers never carry over into the next superbill."""
    return f"{name}_{n}"


def start_superbill(call: guava.Call, n: int):
    state = _calls.setdefault(call.id, {"saved": []})
    state.update(n=n, phase="superbill", nudged=False)

    if n == 1:
        opening = guava.Say(
            "Hi, this is Sam. Tell me about the session you'd like to bill: "
            "the patient, the diagnosis, and what you did and for how long."
        )
    else:
        opening = guava.Say("Okay, next patient. Tell me about that session.")

    checklist = [
        opening,
        guava.Field(key=_key("patient_name", n), field_type="text", sensitive=True,
                    description=(
                        "Patient's full name. The therapist may spell it letter by "
                        "letter, with pauses between letters. While they are spelling, "
                        "stay silent and do not respond to individual letters or short "
                        "pauses; wait until they clearly finish or say they're done. "
                        "If the name sounds unusual, ask them to spell it. Then spell "
                        "the name back letter by letter and ask them to confirm it.")),
        guava.Field(key=_key("service_date", n), field_type="date",
                    description="Date of the session"),
        guava.Field(key=_key("diagnosis", n), field_type="multiple_choice",
                    searchable=True,
                    description=("Primary diagnosis for this visit, including the side "
                                 "(right or left) when it applies. Pick the best match "
                                 "without confirming it now; it is confirmed at the end.")),
        guava.Field(key=_key("eval_level", n), field_type="multiple_choice",
                    choices=["none", "low", "moderate", "high"],
                    description="Whether a PT evaluation was done, and if so its complexity"),
    ]
    for key, description in TIMED_SERVICES.values():
        checklist.append(guava.Field(
            key=_key(key, n), field_type="integer", required=False,
            description=(f"{description}, only if the therapist mentions it. "
                         "Never ask about this service on its own; if it isn't "
                         "mentioned, it wasn't done.")))
    checklist += [
        guava.Field(key=_key("estim_unattended", n), field_type="multiple_choice",
                    choices=["yes", "no"], required=False,
                    description=("Whether unattended electrical stimulation was used, "
                                 "only if the therapist mentions it. Never ask about it "
                                 "on its own.")),
        ("Once the therapist has described their services, or says there are no other "
         "services, stop asking about services. Then do ONE final read-back of "
         "everything in a single short summary: date, diagnosis, evaluation (if any), "
         "and each service mentioned with its minutes. Do not repeat the patient's "
         "name. Ask once if it's all correct. If they correct something, update it "
         "and confirm only that change."),
    ]

    new_patient_note = (
        "" if n == 1 else
        "This is a NEW patient. Ignore every detail from earlier patients in this "
        "call; collect everything fresh. "
    )
    call.set_task(
        f"superbill_{n}",
        objective=(
            new_patient_note +
            "Help the physical therapist create a superbill for one session. "
            "Let them describe the session in their own words, then extract every "
            "detail you can from what they said. Only ask follow-up questions for "
            "information that is still missing. Do not confirm details one at a "
            "time as you go. The only thing to confirm during the conversation is "
            "the patient's name; everything else is confirmed once, together, at "
            "the end. Services they don't mention were not done, so don't ask about "
            "each one separately. If the therapist says there are no other services, "
            "go straight to the final read-back. If information is missing, do not "
            "make anything up and leave it blank."
        ),
        checklist=checklist,
    )


def ask_for_another(call: guava.Call, n: int, bill: dict):
    state = _calls[call.id]
    state["phase"] = "another"

    saved_line = (f"Tell the therapist this superbill is saved as a draft for their "
                  f"review, with a total of ${bill['totals']['total_charges']:.2f}.")
    if bill["warnings"]:
        saved_line += " Briefly mention what needs review: " + " ".join(bill["warnings"])

    call.set_task(
        f"another_{n}",
        objective="Find out whether the therapist has another patient's superbill to do.",
        checklist=[
            saved_line,
            guava.Field(key=_key("another", n), field_type="multiple_choice",
                        choices=["yes", "no"],
                        question="Is there another patient's superbill you'd like to work on?"),
        ],
    )


@agent.on_call_start
def on_call_start(call: guava.Call):
    logger.info("Call started (session: %s)", call.id)
    start_superbill(call, 1)


@agent.on_task_complete
def on_any_task_complete(call: guava.Call, task_id: str):
    """One handler for every task, so we can loop through patients."""
    kind, _, num = task_id.rpartition("_")
    n = int(num)

    if kind == "superbill":
        d = call.get_field(_key("service_date", n))
        service_date = date(d["year"], d["month"], d["day"]) if d else date.today()
        bill = build_superbill(
            patient_name=call.get_field(_key("patient_name", n)),
            service_date=service_date,
            diagnosis=call.get_field(_key("diagnosis", n)),
            eval_level=call.get_field(_key("eval_level", n)),
            timed_minutes={code: call.get_field(_key(key, n)) or 0
                           for code, (key, _) in TIMED_SERVICES.items()},
            estim_unattended=call.get_field(_key("estim_unattended", n)) == "yes",
        )
        path = save_superbill(bill)
        _calls[call.id]["saved"].append(path)
        logger.info("Superbill %d saved to %s", n, path)  # no patient name in logs
        ask_for_another(call, n, bill)

    elif kind == "another":
        if (call.get_field(_key("another", n)) == "yes"
                and n < MAX_PATIENTS_PER_CALL):
            start_superbill(call, n + 1)
        else:
            count = len(_calls[call.id]["saved"])
            call.hangup(
                f"Tell the therapist that {count} draft "
                f"superbill{'s are' if count != 1 else ' is'} saved and ready for "
                "their review, then say goodbye."
            )


# Phrases that mean "I'm done listing services"
DONE_WITH_SERVICES = re.compile(
    r"\b(no (other|more|additional) (services?|treatments?)|nothing else|"
    r"that'?s (it|all)|that is (it|all)|no,? that'?s everything)\b",
    re.IGNORECASE,
)


@agent.on_caller_speech
def on_caller_speech(call: guava.Call, event: CallerSpeechEvent):
    """When the PT says they're done listing services for the current patient,
    tell the agent to move on to the read-back. Once per patient."""
    state = _calls.get(call.id)
    if not state or state["phase"] != "superbill" or state["nudged"]:
        return
    if DONE_WITH_SERVICES.search(event.utterance or ""):
        state["nudged"] = True
        logger.info("Therapist is done listing services; moving to read-back.")
        call.send_instruction(
            "The therapist has no other services for this patient. Stop asking about "
            "services. Every service they did not mention was not done (0 minutes), "
            "and unattended e-stim was not used. If anything else required is still "
            "missing, ask only for that. Then do the single final read-back of "
            "date, diagnosis, evaluation, and services with minutes, and ask once "
            "if it's all correct."
        )


def find_diagnosis(call: guava.Call, query: str):
    """Match what the therapist said to the closest ICD-10 codes."""
    matches, fallback = search_diagnoses(query)
    logger.info("Diagnosis search found %d matches", len(matches))
    return matches, fallback


# Each patient has its own diagnosis field (diagnosis_1, diagnosis_2, ...), and
# Guava binds search handlers by field name, so register the search for each one.
MAX_PATIENTS_PER_CALL = 25
for _n in range(1, MAX_PATIENTS_PER_CALL + 1):
    agent.on_search_query(_key("diagnosis", _n))(find_diagnosis)


@agent.on_session_end
def on_session_end(call: guava.Call, event: BotSessionEnded):
    _calls.pop(call.id, None)
    logger.info("Session ended (session: %s)", call.id)


if __name__ == "__main__":
    logging_utils.configure_logging()

    # Run this to attach your agent to a phone number. Call your agent's number to talk to it.
    # agent.listen_phone("+14849687344")

    # Run this to talk to your agent using your local audio device.
    agent.call_local()

    # Run this to receive a WebRTC link where you can talk to your agent in the browser.
    # agent.listen_webrtc()

    # Run this to test your agent in a text-based chat session in the terminal (no audio required).
    # agent.chat()
