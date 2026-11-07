"""Scope guard: Sahayi is a wellbeing assistant, not a general or coding assistant.

Two layers around the LLM, so this does not depend on the model following its prompt:
  1. is_coding_request(): blocks an obvious coding/technical request before the model is called.
  2. looks_like_code(): replaces a reply that contains code with the refusal.
The input check needs a request verb next to a coding term, so an emergency such as "a python bit me" is never blocked.
"""
import re

OFF_TOPIC_REPLY = "I can only help with how you are feeling and staying safe. How are you today?"

_EN_TERMS = (r"python|javascript|java|c\+\+|c#|html|css|sql|php|react|node\.?js|bash|powershell|typescript|golang|rust|"
             r"coding|source code|algorithm|web ?server|snake game|regex|api|recursion|compile")
_ML_TERMS = r"പൈത്തൺ|ജാവ|കോഡ്|കോഡിംഗ്|പ്രോഗ്രാമിംഗ്|പ്രോഗ്രാം"
_EN_VERBS = (r"write|create|make|build|generate|explain|show|give|debug|fix|teach|implement|develop|"
             r"how do|how to|how can")
_ML_VERBS = r"എഴുത|ഉണ്ടാക്ക|പഠിപ്പിക്ക|വിശദീകരിക്ക"

# English words need word boundaries ("developer" is not "develop"); Malayalam has no spaces-based boundaries.
_T = rf"(?:\b(?:{_EN_TERMS})\b|{_ML_TERMS})"
_V = rf"(?:\b(?:{_EN_VERBS})\b|{_ML_VERBS})"
_LANGS = r"python|javascript|java|bash|sql|c\+\+|php|html|css|react|node\.?js"

_REQUEST = re.compile(
    rf"{_V}.{{0,60}}?{_T}"
    rf"|{_T}.{{0,60}}?{_V}"
    r"|\bcode (?:a|an|me|the|this)\b|\b(?:in|using) (?:python|javascript|java|c\+\+|sql|html)\b"
    r"|\b(?:debug|refactor)\b"
    rf"|\b(?:{_LANGS})\s+(?:script|program|code|query|function|snippet|app|file|page|tutorial|example|class)\b",
    re.I | re.S)
_CODE_REPLY = re.compile(r"```|^\s*(?:def |import |from \w+ import |class \w+[:(]|function |#include|SELECT .* FROM|<html|console\.log|print\()",
                         re.I | re.M)


def is_coding_request(text: str) -> bool:
    return bool(_REQUEST.search(text or ""))


def looks_like_code(reply: str) -> bool:
    return bool(_CODE_REPLY.search(reply or ""))
