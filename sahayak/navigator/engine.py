"""Benefits Navigator: scheme rules as data, evaluated with three-valued logic plus "likely".

The rules live in packs/schemes.v1.json; this module only evaluates them, so a scheme
change is a pack change, never a code change. Truth values, ordered F < U < L < T:

  T  yes
  L  likely: true on what the person told us, but the office will want proof
     (a ration card standing in for BPL status, farm land that must be in the records)
  U  not known: not asked yet, or "don't know"
  F  no

`all` takes the minimum and `any` the maximum, which is Kleene's three-valued logic with
L slotted between U and T. `not` swaps T and F and turns L into U, because "probably
true" does not make the opposite "probably false".

The interview walks the pack's questions in order and asks one only while some answer
to it could still change a scheme's result, never more than `max_questions` in all.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Any, Iterable

from ..packs import Pack, get_pack

F, U, L, T = 0, 1, 2, 3
CODE = {"F": F, "U": U, "L": L, "T": T}
NAME = {F: "F", U: "U", L: "L", T: "T"}
STATUS = {T: "eligible", L: "likely", U: "check", F: "not_eligible"}
GROUPS = ("eligible", "likely", "check", "unlock", "have", "not_eligible")
_NOT = {T: F, F: T, U: U, L: U}
AGE_MIN, AGE_MAX = 0, 120


class AnswerError(ValueError):
    """An answer the pack does not allow: unknown question, option or age."""


class Facts:
    """What the answers tell us: an age interval plus a truth value per fact."""

    __slots__ = ("age", "values")

    def __init__(self, age: tuple[int, int] = (AGE_MIN, AGE_MAX), values: dict[str, int] | None = None):
        self.age = age
        self.values = values or {}

    def get(self, fact: str) -> int:
        return self.values.get(fact, U)

    def with_values(self, changes: dict[str, int]) -> "Facts":
        return Facts(self.age, {**self.values, **changes})

    def with_age(self, age: tuple[int, int]) -> "Facts":
        return Facts(age, self.values)


def _age_truth(cond: list, age: tuple[int, int]) -> int:
    lo, hi = cond[0], AGE_MAX if cond[1] is None else cond[1]
    if lo <= age[0] and age[1] <= hi:
        return T
    if age[1] < lo or age[0] > hi:
        return F
    return U  # an age range that straddles the limit


def evaluate(node: dict, facts: Facts, trail: list | None = None) -> int:
    """Truth value of a rule node. Nodes carrying `say` are appended to `trail` as
    (say, value) so the result can explain itself."""
    if "all" in node:
        value = min((evaluate(n, facts, trail) for n in node["all"]), default=T)
    elif "any" in node:
        value = max((evaluate(n, facts, trail) for n in node["any"]), default=F)
    elif "not" in node:
        value = _NOT[evaluate(node["not"], facts)]
    elif "fact" in node:
        value = facts.get(node["fact"])
    elif "age" in node:
        value = _age_truth(node["age"], facts.age)
    else:
        raise ValueError(f"unknown rule node: {sorted(node)}")
    if trail is not None and "say" in node:
        trail.append((node["say"], value))
    return value


def _codes(sets: dict[str, str]) -> dict[str, int]:
    return {fact: CODE[v] for fact, v in sets.items()}


def _walk(node: dict) -> Iterable[dict]:
    yield node
    for key in ("all", "any"):
        for child in node.get(key, []):
            yield from _walk(child)
    if "not" in node:
        yield from _walk(node["not"])


class Navigator:
    def __init__(self, pack: Pack):
        self.pack = pack
        d = pack.data
        self.questions: list[dict] = d["questions"]
        self.by_id = {q["id"]: q for q in self.questions}
        self.schemes: list[dict] = d["schemes"]
        self.max_questions = int(d.get("max_questions", 8))
        self._validate()
        # Ages where some rule changes its answer: enough to test whether age still matters.
        edges = {AGE_MIN, AGE_MAX}
        for s in self.schemes:
            for node in _walk(s["rule"]):
                if "age" in node:
                    lo, hi = node["age"]
                    edges.add(lo)
                    if hi is not None and hi < AGE_MAX:
                        edges.add(hi + 1)
        self._age_probes = sorted(edges)

    # ------------------------------------------------------------------ answers -> facts

    def facts(self, answers: dict[str, Any]) -> Facts:
        if len(answers) > len(self.questions):
            raise AnswerError("too many answers")
        age, values = (AGE_MIN, AGE_MAX), {}
        for qid, ans in answers.items():
            q = self.by_id.get(qid)
            if q is None:
                raise AnswerError(f"unknown question '{qid}'")
            if q["kind"] == "age":
                age = self._age(q, ans)
            elif q["kind"] == "single":
                values.update(_codes(self._option(q, ans)["sets"]))
            else:  # multi: chosen options are T, the rest F
                chosen = self._chosen(q, ans)
                values.update({o["fact"]: T if o["id"] in chosen else F for o in q["options"]})
        return Facts(age, values)

    def _age(self, q: dict, ans: Any) -> tuple[int, int]:
        if isinstance(ans, bool):
            raise AnswerError("age must be a whole number or an age band")
        if isinstance(ans, int):
            if not AGE_MIN <= ans <= AGE_MAX:
                raise AnswerError(f"age must be {AGE_MIN}-{AGE_MAX}")
            return ans, ans
        for band in q["bands"]:
            if band["id"] == ans:
                return band["range"][0], band["range"][1]
        raise AnswerError(f"unknown age band '{ans}'")

    @staticmethod
    def _option(q: dict, ans: Any) -> dict:
        for o in q["options"]:
            if o["id"] == ans:
                return o
        raise AnswerError(f"'{ans}' is not an answer to '{q['id']}'")

    @staticmethod
    def _chosen(q: dict, ans: Any) -> set[str]:
        if not isinstance(ans, list):
            raise AnswerError(f"'{q['id']}' takes a list of options")
        ids = {o["id"] for o in q["options"]}
        bad = [a for a in ans if a not in ids]
        if bad:
            raise AnswerError(f"{bad} are not answers to '{q['id']}'")
        return set(ans)

    # ------------------------------------------------------------------ evaluation

    def outcomes(self, facts: Facts) -> tuple[tuple[int, bool], ...]:
        """What the person would see for every scheme: its truth value and, for a 'no',
        whether opening a bank account would change it. The interview compares these."""
        out = []
        for s in self.schemes:
            truth = evaluate(s["rule"], facts)
            out.append((truth, truth == F and self._unlock(s, facts) is not None))
        return tuple(out)

    def _unlock(self, scheme: dict, facts: Facts) -> dict | None:
        """A 'no' that one doable step, such as opening a bank account, would turn into
        anything but 'no'. Other conditions may still be unknown; the card lists them."""
        for fact, spec in self.pack.data.get("actionable", {}).items():
            if facts.get(fact) == F and evaluate(scheme["rule"], facts.with_values({fact: CODE[spec["to"]]})) > F:
                return {"fact": fact, "hint": spec["hint"]}
        return None

    # ------------------------------------------------------------------ interview

    def shown_options(self, q: dict, facts: Facts) -> list[dict] | None:
        """The options worth showing for question `q`, or None if no answer could change a result."""
        if q["kind"] == "age":
            seen = {self.outcomes(facts.with_age((a, a))) for a in self._age_probes}
            return q["bands"] if len(seen) > 1 else None
        if q["kind"] == "single":
            seen = {self.outcomes(facts.with_values(_codes(o["sets"]))) for o in q["options"]}
            return q["options"] if len(seen) > 1 else None
        shown = [o for o in q["options"]
                 if self.outcomes(facts.with_values({o["fact"]: T})) != self.outcomes(facts.with_values({o["fact"]: F}))]
        return shown or None

    def next_question(self, answers: dict[str, Any]) -> dict | None:
        facts = self.facts(answers)
        if len(answers) >= self.max_questions:
            return None
        for q in self.questions:
            if q["id"] in answers:
                continue
            shown = self.shown_options(q, facts)
            if shown is None:
                continue
            out = {"id": q["id"], "kind": q["kind"], "short": q["short"], "text": q["text"], "help": q.get("help"),
                   "number": len(answers) + 1, "max_questions": self.max_questions}
            if q["kind"] == "age":
                out["bands"] = [{"id": b["id"], "label": b["label"]} for b in shown]
            else:
                out["options"] = [{"id": o["id"], "label": o["label"]} for o in shown]
            if q["kind"] == "multi":
                out["none"] = q["none"]
            return out
        return None

    def interview(self, answer_for) -> dict[str, Any]:
        """Run the whole interview, asking `answer_for(question)` for each answer. Used by
        SchemeBench and the tests to replay a persona through the real question order."""
        answers: dict[str, Any] = {}
        while (q := self.next_question(answers)) is not None:
            answers[q["id"]] = answer_for(q)
        return answers

    # ------------------------------------------------------------------ result

    def result(self, answers: dict[str, Any], already: Iterable[str] = ()) -> dict[str, Any]:
        t0 = time.perf_counter()
        facts = self.facts(answers)
        already = set(already)
        unknown = already - {s["id"] for s in self.schemes}
        if unknown:
            raise AnswerError(f"unknown schemes {sorted(unknown)}")
        cards = [self._card(s, facts, answers, s["id"] in already) for s in self.schemes]
        d = self.pack.data
        return {
            "pack": {"name": self.pack.name, "version": self.pack.version, "date": self.pack.date},
            "asked": len(answers),
            "max_questions": self.max_questions,
            "profile": self.profile(answers),
            "schemes": cards,
            "groups": {g: [c["id"] for c in cards if c["status"] == g] for g in GROUPS},
            "notes": {"amount": d["amount_note"], "fraud": d["fraud_note"], "decision": d["decision_note"]},
            "timing_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    def _card(self, s: dict, facts: Facts, answers: dict, have: bool) -> dict[str, Any]:
        trail: list = []
        truth = evaluate(s["rule"], facts, trail)
        status = STATUS[truth]
        unlock = self._unlock(s, facts) if truth == F else None
        if unlock:
            status = "unlock"
        if have:
            status = "have"
        reasons = [{"text": say, "truth": NAME[v]} for say, v in trail]
        if truth == F and not unlock:  # say only what rules the scheme out
            reasons = [r for r in reasons if r["truth"] == "F"]
        counter = s["counter"].get("check") if status == "check" else None
        counter = counter or s["counter"]["default"]
        sources = self.pack.data["sources"]
        return {
            "id": s["id"], "short": s["short"], "family": s["family"], "name": s["name"],
            "status": status, "truth": NAME[truth],
            "what": s["what"], "benefit": s["benefit"], "benefit_now": self._benefit_now(s, facts),
            "reasons": reasons,
            "documents": s["documents"], "where": s["where"],
            "counter": {lang: self._fill(text, answers, lang) for lang, text in counter.items()},
            "check_how": s.get("check_how") if status == "check" else None,
            "notes": s.get("notes", []),
            "unlock": unlock,
            "sources": [{"id": sid, **sources[sid]} for sid in s["sources"]],
        }

    @staticmethod
    def _benefit_now(s: dict, facts: Facts) -> dict | None:
        for variant in s.get("benefit_now", []):
            if not variant["when"] or evaluate(variant["when"], facts) == T:
                return {"hi": variant["hi"], "en": variant["en"]}
        return None

    def _fill(self, text: str, answers: dict, lang: str) -> str:
        return " ".join(text.replace("{age_phrase}", self.age_phrase(answers, lang)).split())

    def age_phrase(self, answers: dict, lang: str) -> str:
        age = answers.get("age")
        if isinstance(age, int) and not isinstance(age, bool):
            return self.pack.data["age_phrase"]["exact"][lang].format(n=age)
        for band in self.by_id["age"]["bands"]:
            if band["id"] == age:
                return band["phrase"][lang]
        return ""

    def profile(self, answers: dict[str, Any]) -> list[dict[str, Any]]:
        """The answers in question order, in words (for the screen and the printed slip)."""
        out = []
        for q in self.questions:
            if q["id"] not in answers:
                continue
            ans = answers[q["id"]]
            if q["kind"] == "age":
                if isinstance(ans, int):
                    label, code = {"hi": f"{ans} साल", "en": f"{ans} years"}, str(ans)
                else:
                    band = next(b for b in q["bands"] if b["id"] == ans)
                    label, code = band["label"], ans
            elif q["kind"] == "single":
                o = self._option(q, ans)
                label, code = o["label"], o["id"]
            else:
                chosen = [o for o in q["options"] if o["id"] in ans]
                label = ({lang: "; ".join(o["label"][lang] for o in chosen) for lang in ("hi", "en")}
                         if chosen else q["none"])
                code = "+".join(o["id"] for o in chosen) or "none"
            out.append({"id": q["id"], "short": q["short"], "answer": label, "code": code})
        return out

    # ------------------------------------------------------------------ catalogue

    def catalog(self) -> dict[str, Any]:
        d = self.pack.data
        return {
            "pack": {"name": self.pack.name, "version": self.pack.version, "date": self.pack.date},
            "max_questions": self.max_questions,
            "schemes": [{"id": s["id"], "short": s["short"], "family": s["family"], "name": s["name"], "what": s["what"]}
                        for s in self.schemes],
            "demos": d.get("demos", []),
            "notes": {"amount": d["amount_note"], "fraud": d["fraud_note"], "decision": d["decision_note"]},
        }

    # ------------------------------------------------------------------ pack checks

    def _validate(self) -> None:
        d = self.pack.data
        facts, sources = set(d["facts"]), set(d["sources"])
        problems = []
        if len(self.by_id) != len(self.questions):
            problems.append("duplicate question ids")
        if len({s["id"] for s in self.schemes}) != len(self.schemes):
            problems.append("duplicate scheme ids")
        for q in self.questions:
            if q["kind"] not in ("age", "single", "multi"):
                problems.append(f"{q['id']}: unknown kind {q['kind']}")
            for o in q.get("options", []):
                used = set(o.get("sets", {})) | ({o["fact"]} if "fact" in o else set())
                problems += [f"{q['id']}.{o['id']}: undeclared fact '{f}'" for f in used - facts]
                problems += [f"{q['id']}.{o['id']}: bad truth value '{v}'" for v in o.get("sets", {}).values() if v not in CODE]
        for s in self.schemes:
            for node in _walk(s["rule"]):
                if "fact" in node and node["fact"] not in facts:
                    problems.append(f"{s['id']}: undeclared fact '{node['fact']}'")
            problems += [f"{s['id']}: unknown source '{x}'" for x in s["sources"] if x not in sources]
            for key in ("name", "what", "benefit", "documents", "where", "counter"):
                if not s.get(key):
                    problems.append(f"{s['id']}: missing {key}")
        if "age" not in self.by_id:
            problems.append("no age question")
        if problems:
            raise ValueError("schemes pack: " + "; ".join(problems))


@lru_cache(maxsize=1)
def get_navigator() -> Navigator:
    return Navigator(get_pack("schemes"))
