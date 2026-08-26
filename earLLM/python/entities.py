import re
KNOWN_COURSES=["HDL","LCD","CS101","Networks","Thesis"]
KNOWN_TOPICS=["binary search trees","database normalization","dynamic programming","combinational logic","regular expressions","sorting algorithms","process scheduling","finite automata","karnaugh maps","TCP handshakes","graph traversal","Boolean algebra","joins in SQL","hash tables","linked lists","SQL joins","binary trees","OSI layers","recursion","2's complement","3's complement"]
KNOWN_TOPICS=sorted(KNOWN_TOPICS,key=len,reverse=True)
DATE_WORDS=["next Monday","next Tuesday","next Wednesday","next Thursday","next Friday","next Saturday","next Sunday","today","tomorrow","yesterday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday","this week","next week","this month"]
TIME_RE=re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",re.I)
AMOUNT_RE=re.compile(r"(?:₱|php\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(?:pesos?|php)?",re.I)
ID_RE=re.compile(r"\b(?:deadline|note|poll)\s*#?\s*(\d+)\b",re.I)

def _boundary(text, phrase): return re.search(r"(?<![A-Za-z0-9])"+re.escape(phrase)+r"(?![A-Za-z0-9])",text,re.I)
def extract_course(t):
    return next((c for c in KNOWN_COURSES if _boundary(t,c)),None)
def extract_topic(t):
    return next((x for x in KNOWN_TOPICS if _boundary(t,x)),None)
def extract_date(t): return next((x for x in DATE_WORDS if _boundary(t,x)),None)
def extract_time(t):
    m=TIME_RE.search(t)
    if not m:return None
    h=int(m.group(1)); minute=int(m.group(2) or 0); ap=m.group(3).lower()
    if not 1<=h<=12 or minute>59:return None
    if ap=="pm" and h!=12:h+=12
    if ap=="am" and h==12:h=0
    return f"{h:02d}:{minute:02d}"
def extract_id(t,kind="deadline"):
    m=re.search(rf"\b{kind}\s*#?\s*(\d+)\b",t,re.I); return int(m.group(1)) if m else None
def extract_amount(t):
    # Prefer numbers adjacent to currency words/symbols, then a standalone number for money intents.
    m=re.search(r"(?:₱|php\s*)([0-9][0-9,]*(?:\.\d+)?)|([0-9][0-9,]*(?:\.\d+)?)\s*(?:pesos?|php)\b",t,re.I)
    if not m:return None
    raw=(m.group(1) or m.group(2)).replace(",",""); x=float(raw); return int(x) if x.is_integer() else x
def extract_title(t):
    patterns=[r"\btitled\s+(.+?)(?=\s+(?:tomorrow|today|on|due|at)\b|[,.]|$)",r"\b(?:called|named)\s+(.+?)(?=\s+(?:tomorrow|today|on|due|at)\b|[,.]|$)",r"\b(?:lab report|project|assignment|exam|quiz|report|proposal)\b"]
    for p in patterns:
        m=re.search(p,t,re.I)
        if not m:continue
        if m.lastindex:return m.group(1).strip(" .,")
        return m.group(0)
    return None
def extract_description(t):
    m=re.search(r"\bfor\s+(.+?)\s*$",t,re.I); return m.group(1).strip(" .,") if m else None

ENTITY_EXTRACTORS={
"CREATE_DEADLINE":["course","date","time","title"],"UPDATE_DEADLINE":["deadline_id","course","date","time"],"DELETE_DEADLINE":["deadline_id","course"],"MARK_NO_CLASS":["course","date"],"GET_COURSE_DEADLINES":["course"],"RECORD_DEPOSIT":["amount"],"RECORD_EXPENSE":["amount","description"],"SEARCH_NOTES":["topic"],"LEARN_TOPIC":["topic"],"EXPLAIN_TOPIC":["topic"],"QUIZ_TOPIC":["topic"],"PRACTICE_TOPIC":["topic"],"CREATE_NOTE":["title"],"UPDATE_NOTE":["note_id","title"],"DELETE_NOTE":["note_id"],"CREATE_POLL":["title"],"VOTE_POLL":["poll_id"],"DELETE_POLL":["poll_id"]}

def extract_entities(text,intent):
    out={}
    for k in ENTITY_EXTRACTORS.get(intent,[]):
        v=None
        if k=="course":v=extract_course(text)
        elif k=="date":v=extract_date(text)
        elif k=="time":v=extract_time(text)
        elif k=="amount":v=extract_amount(text)
        elif k=="topic":v=extract_topic(text)
        elif k=="deadline_id":v=extract_id(text,"deadline")
        elif k=="note_id":v=extract_id(text,"note")
        elif k=="poll_id":v=extract_id(text,"poll")
        elif k=="title":v=extract_title(text)
        elif k=="description":v=extract_description(text)
        if v is not None:out[k]=v
    return out
SUPPORTED_ENTITY_TYPES=["course","date","time","amount","deadline_id","topic","title","description","note_id","poll_id"]
