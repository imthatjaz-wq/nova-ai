"""Dialogue manager: context, calls to modules, and honesty trace."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .nlu import interpret, NLUResult
from . import nlg
from memory.store import STM, LTM
from internet.search import aggregate_sources

# Back-compat shim for tests that monkeypatch conversation.dialogue_manager.search_web
try:  # pragma: no cover - used only for patch targets
    from internet.search import search_web as search_web  # type: ignore
except Exception:  # pragma: no cover
    def search_web(query: str):  # type: ignore
        return []
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
    verbose: bool = False  # if True, include trace lines
    state: Dict[str, Any] = field(default_factory=dict)  # pending action/topic

    def ensure_ltm(self) -> LTM:
        if self.ltm is None:
            self.ltm = LTM()
        return self.ltm

    def _resolve_coref(self, text: str) -> Dict[str, str]:
        """Very small heuristic coref: map pronouns to last mentioned file/url/app.

        Returns slots to merge into NLU slots, e.g., {"path": last_path}.
        """
        lowered = text.strip().lower()
        if " it" in lowered or lowered.startswith("it"):
            last = self.state.get("last_object")
            if isinstance(last, dict):
                return {k: v for k, v in last.items() if isinstance(v, str)}
        return {}

    def _remember_object(self, slots: Dict[str, str]) -> None:
        # Track last mentioned path/url/app for coref
        obj: Dict[str, str] = {}
        for k in ("path", "url", "app"):
            if k in slots:
                obj[k] = slots[k]
        if obj:
            self.state["last_object"] = obj

    def handle(self, text: str) -> str:
        tr = Trace()
        nlu_res: NLUResult = interpret(text)
        tr.add(f"intent={nlu_res.intent}")
        self.stm.add("user", text)

        # merge coref slots
        try:
            coref_slots = self._resolve_coref(text)
            for k, v in coref_slots.items():
                nlu_res.slots.setdefault(k, v)
        except Exception:
            pass

        # Confirm/cancel flow
        if nlu_res.intent == "CONFIRM":
            pending = self.state.get("pending")
            if not pending:
                resp = nlg.smalltalk("Noted.")
                self.stm.add("nova", resp)
                return resp + (f"\n(trace: {tr.render()})" if self.verbose else "")
            val = nlu_res.slots.get("value", "").lower()
            if val.startswith("y"):
                fn = pending.get("fn")
                args = pending.get("args", [])
                kwargs = pending.get("kwargs", {})
                msg: str | None = None
                try:
                    if callable(fn):
                        result = fn(*args, **kwargs)  # type: ignore[misc]
                        msg = result if isinstance(result, str) else str(result)
                except Exception:
                    msg = "[error] failed to execute pending command"
                resp = nlg.command_ack(msg or "[ok]")
                self.state.pop("pending", None)
                self.stm.add("nova", resp)
                return resp + (f"\n(trace: {tr.render()})" if self.verbose else "")
            else:
                self.state.pop("pending", None)
                resp = nlg.smalltalk("Cancelled.")
                self.stm.add("nova", resp)
                return resp + (f"\n(trace: {tr.render()})" if self.verbose else "")

        # Commands
        if nlu_res.intent == "COMMAND":
            action = nlu_res.slots.get("action", "")
            if action == "open_url" and "url" in nlu_res.slots:
                msg = cmd_handlers.open_url(nlu_res.slots["url"])
                tr.add("cmd=open_url")
                resp = nlg.command_ack(msg)
                self._remember_object(nlu_res.slots)
            elif action == "create_file":
                path = nlu_res.slots.get("path", "C:/Nova/data/untitled.txt")
                msg = cmd_handlers.create_file(path)
                tr.add("cmd=create_file")
                resp = nlg.command_ack(msg)
                self._remember_object(nlu_res.slots)
            elif action == "open_file" and "path" in nlu_res.slots:
                msg = cmd_handlers.open_file(nlu_res.slots["path"])
                tr.add("cmd=open_file")
                resp = nlg.command_ack(msg)
                self._remember_object(nlu_res.slots)
            elif action == "open_app" and "app" in nlu_res.slots:
                msg = cmd_handlers.open_app(nlu_res.slots["app"])
                tr.add("cmd=open_app")
                resp = nlg.command_ack(msg)
                self._remember_object(nlu_res.slots)
            elif action == "set_reminder":
                seconds = int(nlu_res.slots.get("in_seconds", "0") or 0)
                message = nlu_res.slots.get("message", "Reminder")
                msg = cmd_handlers.set_reminder(seconds, message)
                tr.add("cmd=set_reminder")
                resp = nlg.command_ack(msg)
            elif action == "open" and ("path" in nlu_res.slots or "url" in nlu_res.slots or "app" in nlu_res.slots):
                # disambiguate based on available slots (from coref)
                if "path" in nlu_res.slots:
                    msg = cmd_handlers.open_file(nlu_res.slots["path"])
                    tr.add("cmd=open_file")
                    resp = nlg.command_ack(msg)
                elif "url" in nlu_res.slots:
                    msg = cmd_handlers.open_url(nlu_res.slots["url"])
                    tr.add("cmd=open_url")
                    resp = nlg.command_ack(msg)
                else:
                    msg = cmd_handlers.open_app(nlu_res.slots["app"])
                    tr.add("cmd=open_app")
                    resp = nlg.command_ack(msg)
                self._remember_object(nlu_res.slots)
            else:
                # ambiguous: ask clarify and set pending context
                self.state["pending"] = {"type": "confirm", "text": text}
                resp = nlg.clarify("What should I open? A file, a URL, or an app?")
                # inbox capture for unresolved command
                try:
                    self.ensure_ltm().log_event("inbox", f"clarify: {text}")
                except Exception:
                    pass
            self.stm.add("nova", resp)
            # inbox capture for denied/error command responses
            try:
                if isinstance(resp, str) and (resp.startswith("[denied]") or resp.startswith("[error]")):
                    self.ensure_ltm().log_event("inbox", f"command-unresolved: {text} -> {resp}")
            except Exception:
                pass
            return resp + (f"\n(trace: {tr.render()})" if self.verbose else "")

        # Questions
        if nlu_res.intent == "QUESTION":
            ltm = self.ensure_ltm()
            fact: Optional[str] = None
            cites: List[str] = []
            key_for_store: Optional[str] = None
            if nlu_res.slots.get("qtype") == "capital_of":
                key = f"capital:{nlu_res.slots.get('country','')}"
                found = ltm.get_facts(key)
                if found:
                    fact = found[0][2]
                    try:
                        cites = ltm.get_citation_urls_for_key(key)
                    except Exception:
                        pass
                    tr.add("memory=hit")
                else:
                    tr.add("internet=aggregate")
                    summary, citations = aggregate_sources(nlu_res.text)
                    if summary:
                        fact = summary
                        cites = [c.get("url", "") for c in citations if c.get("url")]
                        try:
                            store_key = f"capital:{nlu_res.slots.get('country','')}"
                            srcs = [(c.get("url", ""), c.get("name", "")) for c in citations if c.get("url")]
                            if srcs:
                                ltm.add_fact_with_sources(store_key, summary, srcs)
                            else:
                                ltm.add_fact(store_key, summary)
                        except Exception:
                            pass
                key_for_store = key
            if fact is None and not nlu_res.slots.get("qtype"):
                tr.add("internet=aggregate")
                summary, citations = aggregate_sources(nlu_res.text)
                if summary:
                    fact = summary
                    cites = [c.get("url", "") for c in citations if c.get("url")]
                    try:
                        store_key = key_for_store or f"answer:{nlu_res.text}"
                        srcs = [(c.get("url", ""), c.get("name", "")) for c in citations if c.get("url")]
                        if srcs:
                            ltm.add_fact_with_sources(store_key, summary, srcs)
                        else:
                            ltm.add_fact(store_key, summary)
                    except Exception:
                        pass
            resp = nlg.answer_fact(nlu_res.text, fact, sources=cites)
            self.stm.add("nova", resp)
            # inbox capture for unknown answers
            if fact is None:
                try:
                    self.ensure_ltm().log_event("inbox", f"question: {nlu_res.text}")
                except Exception:
                    pass
            return resp + (f"\n(trace: {tr.render()})" if self.verbose else "")

        # Default chat
        reply = nlg.smalltalk("Got it.")
        self.stm.add("nova", reply)
        return reply + (f"\n(trace: {tr.render()})" if self.verbose else "")
