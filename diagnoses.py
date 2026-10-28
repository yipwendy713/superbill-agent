"""Common physical therapy ICD-10-CM codes (FY 2027), with a simple search
so the voice agent can match what the therapist says to a code.

Source list: veroscribe.com/icd-10/common-codes/physical-therapy
Descriptions follow the CDC/NCHS ICD-10-CM code set.
"""
import re

CODES = [
    # Low back and neck
    ("M54.50", "Low back pain, unspecified"),
    ("M54.51", "Vertebrogenic low back pain"),
    ("M54.59", "Other low back pain"),
    ("M54.2", "Cervicalgia"),
    ("M54.6", "Pain in thoracic spine"),
    ("M54.16", "Radiculopathy, lumbar region"),
    ("M54.12", "Radiculopathy, cervical region"),
    ("M54.41", "Lumbago with sciatica, right side"),
    ("M54.42", "Lumbago with sciatica, left side"),
    ("M51.26", "Other intervertebral disc displacement, lumbar region"),
    ("M51.362", "Other intervertebral disc degeneration, lumbar region with discogenic back pain and lower extremity pain"),
    ("M48.062", "Spinal stenosis, lumbar region with neurogenic claudication"),
    ("M47.816", "Spondylosis without myelopathy or radiculopathy, lumbar region"),
    ("S13.4XXD", "Sprain of ligaments of cervical spine, subsequent encounter"),
    ("S33.5XXD", "Sprain of ligaments of lumbar spine, subsequent encounter"),
    ("S39.012D", "Strain of muscle, fascia and tendon of lower back, subsequent encounter"),
    # Shoulder
    ("M25.511", "Pain in right shoulder"),
    ("M25.512", "Pain in left shoulder"),
    ("M75.101", "Unspecified rotator cuff tear or rupture of right shoulder, not specified as traumatic"),
    ("M75.102", "Unspecified rotator cuff tear or rupture of left shoulder, not specified as traumatic"),
    ("M75.41", "Impingement syndrome of right shoulder"),
    ("M75.42", "Impingement syndrome of left shoulder"),
    ("M75.01", "Adhesive capsulitis of right shoulder"),
    ("M75.02", "Adhesive capsulitis of left shoulder"),
    ("M25.611", "Stiffness of right shoulder, not elsewhere classified"),
    ("M25.612", "Stiffness of left shoulder, not elsewhere classified"),
    ("S46.011D", "Strain of muscle(s) and tendon(s) of the rotator cuff of right shoulder, subsequent encounter"),
    # Hip and knee
    ("M25.551", "Pain in right hip"),
    ("M25.552", "Pain in left hip"),
    ("M25.561", "Pain in right knee"),
    ("M25.562", "Pain in left knee"),
    ("M17.11", "Unilateral primary osteoarthritis, right knee"),
    ("M17.12", "Unilateral primary osteoarthritis, left knee"),
    ("M17.0", "Bilateral primary osteoarthritis of knee"),
    ("M16.11", "Unilateral primary osteoarthritis, right hip"),
    ("M16.12", "Unilateral primary osteoarthritis, left hip"),
    ("M22.2X1", "Patellofemoral disorders, right knee"),
    ("M22.2X2", "Patellofemoral disorders, left knee"),
    ("M76.31", "Iliotibial band syndrome, right leg"),
    ("M76.32", "Iliotibial band syndrome, left leg"),
    ("S83.511D", "Sprain of anterior cruciate ligament of right knee, subsequent encounter"),
    # Ankle and foot
    ("M25.571", "Pain in right ankle and joints of right foot"),
    ("M25.572", "Pain in left ankle and joints of left foot"),
    ("M67.A01", "Plantar fasciitis, right foot"),
    ("M67.A02", "Plantar fasciitis, left foot"),
    ("M76.61", "Achilles tendinitis, right leg"),
    ("M76.62", "Achilles tendinitis, left leg"),
    ("S93.401D", "Sprain of unspecified ligament of right ankle, subsequent encounter"),
    ("S93.402D", "Sprain of unspecified ligament of left ankle, subsequent encounter"),
    # Elbow, wrist and hand
    ("M77.11", "Lateral epicondylitis, right elbow"),
    ("M77.12", "Lateral epicondylitis, left elbow"),
    ("G56.01", "Carpal tunnel syndrome, right upper limb"),
    ("G56.02", "Carpal tunnel syndrome, left upper limb"),
    ("M65.4", "Radial styloid tenosynovitis [de Quervain]"),
    ("M25.531", "Pain in right wrist"),
    ("M25.532", "Pain in left wrist"),
    # Strength, gait and balance
    ("M62.81", "Muscle weakness (generalized)"),
    ("R26.2", "Difficulty in walking, not elsewhere classified"),
    ("R26.89", "Other abnormalities of gait and mobility"),
    ("R26.81", "Unsteadiness on feet"),
    ("R29.6", "Repeated falls"),
    ("Z91.81", "History of falling"),
    ("R53.1", "Weakness"),
    ("M25.661", "Stiffness of right knee, not elsewhere classified"),
    ("M25.662", "Stiffness of left knee, not elsewhere classified"),
    ("R29.3", "Abnormal posture"),
    # After surgery and joint replacement
    ("Z47.1", "Aftercare following joint replacement surgery"),
    ("Z96.651", "Presence of right artificial knee joint"),
    ("Z96.652", "Presence of left artificial knee joint"),
    ("Z96.641", "Presence of right artificial hip joint"),
    ("Z96.642", "Presence of left artificial hip joint"),
    ("Z47.89", "Encounter for other orthopedic aftercare"),
    ("Z98.890", "Other specified postprocedural states"),
    # Neurological
    ("I69.351", "Hemiplegia and hemiparesis following cerebral infarction affecting right dominant side"),
    ("I69.352", "Hemiplegia and hemiparesis following cerebral infarction affecting left dominant side"),
    ("G20.A1", "Parkinson's disease without dyskinesia, without mention of fluctuations"),
    ("G35.D", "Multiple sclerosis, unspecified"),
]

# What the agent sees and what get_field() returns: "Pain in right knee (M25.561)"
DIAGNOSES = {f"{desc} ({code})": (code, desc) for code, desc in CODES}

# Everyday words a PT might say -> words used in the official descriptions
SYNONYMS = {
    "lower back": "low back", "back pain": "low back pain", "neck": "cervicalgia cervical",
    "mid back": "thoracic", "upper back": "thoracic", "sciatica": "sciatica lumbago",
    "herniated": "disc displacement", "bulging": "disc displacement",
    "frozen shoulder": "adhesive capsulitis", "rotator cuff": "rotator cuff",
    "tennis elbow": "lateral epicondylitis", "de quervain": "quervain tenosynovitis",
    "it band": "iliotibial band", "itb": "iliotibial band", "acl": "anterior cruciate",
    "runner's knee": "patellofemoral", "kneecap": "patellofemoral",
    "arthritis": "osteoarthritis", "oa": "osteoarthritis",
    "knee replacement": "artificial knee aftercare joint replacement",
    "hip replacement": "artificial hip aftercare joint replacement",
    "tka": "artificial knee aftercare", "tkr": "artificial knee aftercare",
    "tha": "artificial hip aftercare", "thr": "artificial hip aftercare",
    "post op": "aftercare postprocedural", "post-op": "aftercare postprocedural",
    "surgery": "aftercare postprocedural", "stroke": "cerebral infarction hemiparesis",
    "cva": "cerebral infarction hemiparesis", "parkinson": "parkinson's",
    "ms": "multiple sclerosis", "balance": "unsteadiness gait", "fall": "falls falling",
    "falls": "falls falling", "gait": "gait walking", "weak": "weakness",
    "stiff": "stiffness", "sprained": "sprain", "strained": "strain", "posture": "posture",
}

STOPWORDS = {"the", "and", "with", "of", "in", "a", "an", "for", "on", "pain", "patient",
             "has", "her", "his", "their", "is", "was", "side", "s", "not", "other"}


def _words(text):
    return set(re.findall(r"[a-z0-9']+", text.lower().replace("'s", "")))


def search_diagnoses(query, limit=5):
    """Return (matches, fallback) lists of diagnosis labels for Guava's search field."""
    q = query.lower()
    for phrase, expansion in SYNONYMS.items():
        if re.search(rf"\b{re.escape(phrase)}\b", q):
            q += " " + expansion
    q_words = _words(q)
    wants_pain = "pain" in q_words or "hurts" in q_words or "ache" in q_words
    side = "right" if "right" in q_words else "left" if "left" in q_words else None
    terms = q_words - STOPWORDS - {"right", "left"}

    scored = []
    for label, (code, desc) in DIAGNOSES.items():
        d_words = _words(desc)
        score = len(terms & d_words) * 2
        if code.lower() in q:  # the PT read out the code itself
            score += 10
        if score == 0:
            continue
        if wants_pain and "pain" in d_words:
            score += 1
        if side and side in d_words:
            score += 2
        elif side and ({"right", "left"} - {side}) & d_words:
            score -= 3  # wrong side
        scored.append((score, label))

    scored.sort(key=lambda s: -s[0])
    matches = [label for score, label in scored if score > 0][:limit]
    fallback = [label for label in DIAGNOSES if label.startswith(
        ("Low back pain, unspecified", "Cervicalgia", "Pain in right knee",
         "Pain in left knee", "Pain in right shoulder", "Muscle weakness"))]
    return matches, fallback


if __name__ == "__main__":
    for q in ["right knee pain", "frozen shoulder on the left", "tennis elbow right",
              "lower back pain with sciatica on the right", "rehab after a right knee replacement",
              "ACL sprain right knee", "plantar fasciitis left foot", "balance problems, falls",
              "neck pain", "M54.50"]:
        print(f"{q!r} -> {search_diagnoses(q)[0][:3]}")
