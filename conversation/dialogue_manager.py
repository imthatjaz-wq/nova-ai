"""Dialogue manager: context, calls to modules, and honesty trace."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .nlu import interpret, NLUResult
from . import nlg
from memory.store import STM, LTM
from internet.search import search_web
from internet.summarize import summarize_text
from commands import handlers as cmd_handlers


@dataclass
class Trace:
    steps: List[str] = field(default_factory=list)

    def add(self, s: str) -> None:
        self.steps.append(s)

    def render(self) -> str:
        return " | ".join(self.steps)


@dataclass
class DialogueManager:
    stm: STM = field(default_factory=lambda: STM(capacity=10))
    ltm: Optional[LTM] = None

    def ensure_ltm(self) -> LTM:
        if self.ltm is None:
            self.ltm = LTM()
        return self.ltm

    def handle(self, text: str) -> str:
        tr = Trace()
        nlu_res: NLUResult = interpret(text)
        tr.add(f"intent={nlu_res.intent}")
        self.stm.add("user", text)

        if nlu_res.intent == "COMMAND":
            action = nlu_res.slots.get("action", "")
            if action == "open_url" and "url" in nlu_res.slots:
                msg = cmd_handlers.open_url(nlu_res.slots["url"])
                tr.add("cmd=open_url")
                resp = nlg.command_ack(msg)
            elif action == "create_file":
                path = nlu_res.slots.get("path", "C:/Nova/data/untitled.txt")
                msg = cmd_handlers.create_file(path)
                tr.add("cmd=create_file")
                resp = nlg.command_ack(msg)
            else:
                resp = nlg.command_ack("I don't recognize that command yet.")
            self.stm.add("nova", resp)
            return resp + f"\n(trace: {tr.render()})"

        if nlu_res.intent == "QUESTION":
            # Try memory first (simple pattern example: capital:country)
            ltm = self.ensure_ltm()
            fact = None
            cites: List[str] = []
            if nlu_res.slots.get("qtype") == "capital_of":
                key = f"capital:{nlu_res.slots.get('country','')}"
                found = ltm.get_facts(key)
                if found:
                    fact = found[0][2]
                    tr.add("memory=hit")
            if not fact:
                # Ethical search then summarize name/snippet
                tr.add("internet=search")
                results = search_web(nlu_res.text)
                if results:
                    top = results[0]
                    fact = summarize_text(f"{top.get('name','')}. {top.get('snippet','')}")
                    cites.append(top.get("url", ""))
            resp = nlg.answer_fact(nlu_res.text, fact, sources=cites)
            self.stm.add("nova", resp)
            return resp + f"\n(trace: {tr.render()})"

        # Default chat
        reply = nlg.smalltalk("Got it.")
        self.stm.add("nova", reply)
        return reply + f"\n(trace: {tr.render()})"
