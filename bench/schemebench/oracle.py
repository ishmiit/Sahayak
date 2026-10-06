"""SchemeBench oracle: the expected answer for every scheme, derived straight from the
official texts as plain if/else.

This file deliberately does not import the engine or read packs/schemes.v1.json. It is a
second, independent transcription of the same official rules, so a wrong age limit, a
missing condition or a mis-wired answer in the pack shows up as a disagreement. It shares
the pack's documented interpretations (the "interpretation" list in the pack), because
those are decisions about what the app's questions mean, not rules.

Its author is the same as the pack's, so it catches transcription errors, not
misreadings of the rules. The human second derivation (worksheet_v1.csv) covers those.

Answers use the API format: age (int), situation (list of widow / disability80 /
earner_died), ration, bank, work, money, kisan.
"""
from __future__ import annotations

ELIGIBLE, LIKELY, CHECK, UNLOCK, NO = "eligible", "likely", "check", "unlock", "not_eligible"
UNORGANISED_WORK = ("farm_labour", "unorganised")


def _bpl(a: dict) -> str:
    """Interpretation bpl_proxy: an AAY or BPL/PHH card means likely BPL (the office checks
    the list), APL means not BPL, no card or don't know means unknown."""
    return {"aay": LIKELY, "bpl_phh": LIKELY, "apl": NO, "none": CHECK, "dont_know": CHECK}[a["ration"]]


def ignoaps(a: dict) -> str:
    # Nagaland DSW: "The eligibility age for availing IGNOAPS is 60years and above living below poverty line."
    if a["age"] < 60:
        return NO
    return _bpl(a)


def ignwps(a: dict) -> str:
    # Meghalaya: "BPL widow between 40-79 years of age". At 80 the pension moves to IGNOAPS.
    if "widow" not in a["situation"]:
        return NO
    if a["age"] < 40 or a["age"] > 79:
        return NO
    return _bpl(a)


def igndps(a: dict) -> str:
    # Meghalaya: BPL, "severe or multiple disabilities", "between the age of 18-79 years";
    # Nagaland: "more than 80% disability". The question asks for a certificate of 80% or more.
    if "disability80" not in a["situation"]:
        return NO
    if a["age"] < 18 or a["age"] > 79:
        return NO
    return _bpl(a)


def nfbs(a: dict) -> str:
    # Meghalaya: "below poverty line families on the death of a primary bread winner between
    # the age of 18-59 years". The earner's age is part of the question.
    if "earner_died" not in a["situation"]:
        return NO
    return _bpl(a)


def _bank_scheme(a: dict, lo: int, hi: int) -> str:
    # PIB 9 May 2023: "Persons in the age group of {lo}-{hi} years having an individual bank or
    # a post office account are entitled to enroll". No account yet: open one, then join.
    if a["age"] < lo or a["age"] > hi:
        return NO
    return {"yes": ELIGIBLE, "no": UNLOCK, "dont_know": CHECK}[a["bank"]]


def pmsby(a: dict) -> str:
    return _bank_scheme(a, 18, 70)


def pmjjby(a: dict) -> str:
    return _bank_scheme(a, 18, 50)


def apy(a: dict) -> str:
    # PFRDA FAQ: age 18-40, savings bank / post office account; from 1 Oct 2022 anyone who
    # "is or has been an income-tax payer" cannot open an account.
    if a["age"] < 18 or a["age"] > 40:
        return NO
    if a["money"] == "taxpayer":
        return NO
    if a["bank"] == "no":
        return UNLOCK  # interpretation unlock: tax status may still be unknown
    if a["bank"] == "dont_know" or a["money"] == "dont_know":
        return CHECK
    return ELIGIBLE


def pmkisan(a: dict) -> str:
    # pmkisan.gov.in: income support "to all land holding farmer families", except the listed
    # higher-economic-status categories. Land must be in the records (interpretation land_proof).
    if a["work"] != "farmer_land":
        return NO
    if a["kisan"] == "yes":
        return NO
    if a["kisan"] == "dont_know":
        return CHECK
    return LIKELY


def pmjay(a: dict) -> str:
    # PIB 9 Dec 2024: Rs 5 lakh cover "to all senior citizens of the age 70 years and above
    # irrespective of their socio-economic status". Below 70 the family must be on the
    # SECC 2011 / state list, which only a CSC can look up (interpretation pmjay_list).
    return ELIGIBLE if a["age"] >= 70 else CHECK


def eshram(a: dict) -> str:
    # eShram FAQ: "any individual engaged in unorganised work and aged between 16 to 59 years";
    # an unorganised worker is "not a member of ESIC or EPFO"; Q54: agricultural labourers and
    # landless farmers can register (interpretation unorganised).
    if a["age"] < 16 or a["age"] > 59:
        return NO
    return ELIGIBLE if a["work"] in UNORGANISED_WORK else NO


def pmsym(a: dict) -> str:
    # PIB 23 Mar 2023: "workers in the age group of 18-40 years whose monthly income is
    # Rs. 15000/- or less and not a member of EPFO/ESIC/NPS (Govt. funded)". A taxpayer earns
    # over the limit (interpretation tax_income).
    if a["age"] < 18 or a["age"] > 40:
        return NO
    if a["work"] not in UNORGANISED_WORK:
        return NO
    return {"le15k": ELIGIBLE, "gt15k": NO, "taxpayer": NO, "dont_know": CHECK}[a["money"]]


def pmjdy(a: dict) -> str:
    # pmjdy.gov.in: a basic savings account "by persons not having any other account".
    return {"no": ELIGIBLE, "yes": NO, "dont_know": CHECK}[a["bank"]]


SCHEMES = {
    "ignoaps": ignoaps, "ignwps": ignwps, "igndps": igndps, "nfbs": nfbs, "pmsby": pmsby, "pmjjby": pmjjby,
    "apy": apy, "pmkisan": pmkisan, "pmjay": pmjay, "eshram": eshram, "pmsym": pmsym, "pmjdy": pmjdy,
}


def expected(answers: dict) -> dict[str, str]:
    return {sid: fn(answers) for sid, fn in SCHEMES.items()}
