"""
generate_v2_dataset.py

One-off generator for the v2 dataset growth pass (docs/DESIGN.md §0/§6).

Produces data/intents.jsonl with >= 30 examples per intent (target
800-1000 total across 24 intents), including:
  - short/long phrasings
  - formal/casual register
  - questions vs commands
  - incomplete/fragment phrases
  - different word orders
  - hard negatives for confusable intent pairs identified in the v1
    confusion matrix (GET_DEADLINES vs GET_COURSE_DEADLINES,
    PRACTICE_TOPIC vs QUIZ_TOPIC, DELETE_DEADLINE vs MARK_NO_CLASS, etc.)

This is a data-authoring tool, not part of the runtime pipeline. Run once,
inspect the output, then run:
    python python/dataset.py --version v2 --seed 42

Usage:
    python python/generate_v2_dataset.py
"""

import json
import os
import random

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
OUT_PATH = os.path.join(DATA_DIR, "intents.jsonl")

COURSES = ["HDL", "LCD", "CS101", "Networks", "Thesis"]
TOPICS = [
    "binary trees", "recursion", "finite automata", "2's complement",
    "database normalization", "dynamic programming", "karnaugh maps",
    "hash tables", "TCP handshakes", "joins in SQL", "OSI layers",
    "Boolean algebra", "regular expressions", "sorting algorithms",
    "SQL joins", "combinational logic", "binary search trees",
    "graph traversal", "process scheduling", "linked lists",
]
DATES = ["today", "tomorrow", "Friday", "Monday", "next week", "this week", "next Monday"]
TIMES = ["6 PM", "5 PM", "9 AM", "noon", "10:30 AM", "3 PM"]
DEADLINE_IDS = [3, 7, 12, 21]
AMOUNTS_DEPOSIT = [(500, "500 pesos"), (1200, "1200"), (2000, "₱2,000"), (300, "300 peso")]
AMOUNTS_EXPENSE = [(150, "150", "printing"), (800, "800", "food for the event"),
                   (450, "₱450", "supplies"), (1000, "1000 peso", "venue rental")]

rng = random.Random(42)


def date_entity(word):
    if word in ("Friday", "Monday", "next Monday"):
        return word if word == "next Monday" else word
    return word


def to_24h(t):
    mapping = {"6 PM": "18:00", "5 PM": "17:00", "9 AM": "09:00", "noon": "12:00",
               "10:30 AM": "10:30", "3 PM": "15:00"}
    return mapping[t]


records = []


def add(text, intent, entities=None):
    records.append({"text": text, "intent": intent, "entities": entities or {}})


# ---------------------------------------------------------------------------
# GET_SCHEDULE (no date entity -- general/weekly schedule, contrasted with
# GET_TODAY_SCHEDULE / GET_TOMORROW_SCHEDULE below)
# ---------------------------------------------------------------------------
for t in [
    "What's my schedule?", "Show me my class schedule", "Can you pull up my schedule",
    "schedule pls", "What classes do I have this week", "give me my full weekly timetable",
    "I need to see my class schedule", "what's my timetable look like",
    "can I see my classes", "pull up my full schedule please",
    "I'd like to view my class schedule", "show my weekly classes",
    "what does my week look like class-wise", "display my schedule",
    "gimme my schedule", "may I see my class timetable",
    "what classes am I taking this semester", "list out my classes",
    "can you show my overall schedule", "I want to check my timetable",
    "show classes", "full schedule please", "let me see my classes",
    "what's the full weekly schedule", "view my timetable",
    "hey can you show me my schedule", "need my class timetable asap",
    "could I get a look at my schedule", "show me all my classes for the week",
    "what's the deal with my schedule this week",
]:
    add(t, "GET_SCHEDULE")

# ---------------------------------------------------------------------------
# GET_TODAY_SCHEDULE
# ---------------------------------------------------------------------------
for t in [
    "What do I have today?", "Show me today's classes", "do I have class today",
    "What's on my plate today", "today's schedule please", "Any classes today?",
    "what am I attending today", "do I have any classes today",
    "give me today's timetable", "what's today looking like class-wise",
    "am I free today or do I have class", "today's classes pls",
    "what do my classes look like today", "is there class today",
    "show today's schedule", "today, what do I have",
    "gimme today's classes", "what's happening in class today",
    "any lectures today", "do I need to go to class today",
    "check today's schedule for me", "what's on for today",
    "today's timetable", "what classes today",
    "class schedule for today please", "let me know what I have today",
    "today schedule check", "what's my day look like",
    "do I have anything today", "quick check: classes today?",
]:
    add(t, "GET_TODAY_SCHEDULE", {"date": "today"})

# ---------------------------------------------------------------------------
# GET_TOMORROW_SCHEDULE
# ---------------------------------------------------------------------------
for t in [
    "What do I have tomorrow?", "show tomorrow's classes", "do I have class tomorrow",
    "What's my schedule for tomorrow", "tomorrow's classes?",
    "am I attending anything tomorrow", "do I have any classes tomorrow",
    "give me tomorrow's timetable", "what's tomorrow looking like class-wise",
    "is there class tomorrow", "tomorrow's schedule please",
    "what am I attending tomorrow", "show tomorrow's schedule",
    "tomorrow, what do I have", "gimme tomorrow's classes",
    "what's happening in class tomorrow", "any lectures tomorrow",
    "do I need to go to class tomorrow", "check tomorrow's schedule for me",
    "what's on for tomorrow", "tomorrow's timetable",
    "what classes tomorrow", "class schedule for tomorrow please",
    "let me know what I have tomorrow", "tomorrow schedule check",
    "what's my day look like tomorrow", "do I have anything tomorrow",
    "quick check: classes tomorrow?", "will I have class tomorrow",
    "next day schedule please",
]:
    add(t, "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"})

# ---------------------------------------------------------------------------
# GET_DEADLINES (general -- no course, no narrow date window)
# hard negatives vs GET_COURSE_DEADLINES and GET_WEEK_DEADLINES: keep these
# course-agnostic and date-agnostic on purpose.
# ---------------------------------------------------------------------------
for t in [
    "What deadlines do I have?", "Show me all my deadlines", "list my pending deadlines",
    "what's due", "Can you give me my deadlines", "anything due soon?",
    "what am I supposed to turn in", "show all pending deadlines",
    "give me the full deadline list", "what assignments are due",
    "do I have anything due", "what's outstanding right now",
    "show my to-do list of deadlines", "any deadlines coming up at all",
    "list everything that's due", "what's left to submit",
    "deadlines please", "give me a rundown of what's due",
    "what do I still need to turn in", "show pending assignments",
    "what's on my deadline list", "anything I'm missing that's due",
    "give me the deadline overview", "what haven't I submitted yet",
    "show me what's outstanding", "list all my pending work",
    "what do I owe in terms of assignments", "deadlines overview please",
    "what's due across all my classes", "give me every deadline I have",
]:
    add(t, "GET_DEADLINES")

# ---------------------------------------------------------------------------
# GET_COURSE_DEADLINES -- always names a course
# ---------------------------------------------------------------------------
course_deadline_templates = [
    "What deadlines do I have for {c}?",
    "show me {c} deadlines",
    "anything due in {c} class",
    "what's due for {c}",
    "list deadlines for my {c} course",
    "what does {c} have due",
    "give me the {c} deadline list",
    "any {c} assignments due",
    "what's outstanding in {c}",
    "show pending {c} deadlines",
    "what am I missing in {c}",
    "{c} deadlines please",
    "anything due specifically for {c}",
    "what's left to submit for {c}",
    "check {c} for pending deadlines",
    "give me {c}'s deadline rundown",
    "what does {c} still need from me",
    "show what's due only in {c}",
]
for c in COURSES:
    templates_for_c = rng.sample(course_deadline_templates, 8)
    for t in templates_for_c:
        add(t.format(c=c), "GET_COURSE_DEADLINES", {"course": c})

# ---------------------------------------------------------------------------
# GET_WEEK_DEADLINES -- always a week-scoped date, no specific course
# ---------------------------------------------------------------------------
week_templates = [
    ("What's due this week?", "this week"),
    ("show deadlines for the week", "this week"),
    ("what do I have due next week", "next week"),
    ("weekly deadline roundup please", "this week"),
    ("anything due before the week ends", "this week"),
    ("give me next week's deadlines", "next week"),
    ("what's on the docket for this week", "this week"),
    ("show me everything due this coming week", "next week"),
    ("what's due over the next 7 days", "this week"),
    ("weekly rundown of deadlines", "this week"),
    ("what am I facing next week deadline-wise", "next week"),
    ("this week's deadline list please", "this week"),
    ("give me a week-by-week deadline check", "this week"),
    ("what's due for the rest of the week", "this week"),
    ("next week deadlines, what do I have", "next week"),
    ("show this week's pending work", "this week"),
    ("what's due between now and Sunday", "this week"),
    ("give me a 7-day deadline outlook", "this week"),
    ("what's coming due next week specifically", "next week"),
    ("show me this week's full deadline picture", "this week"),
    ("deadlines for the upcoming week please", "next week"),
    ("what should I expect due this week", "this week"),
    ("roll up all deadlines for next week", "next week"),
    ("what's on deck this week", "this week"),
    ("week-ahead deadline summary please", "next week"),
    ("show me what's due within the week", "this week"),
    ("next 7 days, what's due", "this week"),
    ("give me the weekly deadline digest", "this week"),
    ("what's due looking forward to next week", "next week"),
    ("summarize this week's deadlines for me", "this week"),
    ("what do I owe by end of week", "this week"),
    ("upcoming week deadlines, run it down for me", "next week"),
]
for t, d in week_templates:
    add(t, "GET_WEEK_DEADLINES", {"date": d})

# ---------------------------------------------------------------------------
# SEARCH_NOTES vs LEARN_TOPIC vs EXPLAIN_TOPIC vs QUIZ_TOPIC vs PRACTICE_TOPIC
# These five share a `topic` slot and are the intents most likely to be
# confused with each other, so give each a distinct set of trigger verbs
# plus explicit hard-negative pairs that swap verbs across topics.
# ---------------------------------------------------------------------------
search_templates = [
    "Find my notes on {t}",
    "search my notes for {t}",
    "do I have notes about {t}",
    "look up my notes on {t}",
    "pull up notes about {t}",
    "find anything I've written on {t}",
    "search for {t} in my notes",
    "do I have anything saved on {t}",
    "look for my {t} notes",
    "check my notes for {t}",
    "did I write anything about {t}",
    "any notes on {t} I've saved",
    "pull my {t} notes up",
    "find where I wrote about {t}",
    "search saved notes: {t}",
]
learn_templates = [
    "How do I use {t}?",
    "teach me about {t}",
    "I want to learn {t}",
    "can you help me understand {t}",
    "what is {t}",
    "I need to learn {t} from scratch",
    "walk me through {t}",
    "help me get started with {t}",
    "I'm trying to learn {t}",
    "can you teach me {t}",
    "introduce me to {t}",
    "how does {t} work, teach me",
    "I want to understand {t} better",
    "get me up to speed on {t}",
    "help me learn the basics of {t}",
]
explain_templates = [
    "Explain how {t} works",
    "can you explain {t}",
    "explain {t} like I'm five",
    "break down how {t} works",
    "give me a clear explanation of {t}",
    "explain the concept of {t}",
    "can you break down {t} for me",
    "explain {t} in simple terms",
    "what's the explanation behind {t}",
    "clarify how {t} works for me",
    "explain {t} step by step",
    "can you simplify {t} for me",
    "give me a plain-english explanation of {t}",
]
quiz_templates = [
    "Quiz me on {t}",
    "give me a quiz on {t}",
    "test my knowledge of {t}",
    "can you quiz me on {t}",
    "give me a graded quiz about {t}",
    "quiz time: {t}",
    "run a quiz on {t}",
    "test me on {t}",
    "I want a quiz covering {t}",
    "score my understanding of {t} with a quiz",
    "give me multiple choice questions on {t}",
    "put together a quiz about {t}",
]
practice_templates = [
    "Give me practice problems on {t}",
    "I want to practice {t}",
    "practice questions for {t} please",
    "let's do some practice on {t}",
    "give me exercises on {t}",
    "I need to drill {t}",
    "hook me up with practice problems for {t}",
    "give me some drills on {t}",
    "let's practice {t} together",
    "I want more reps on {t}",
    "practice set for {t} please",
    "give me untimed practice on {t}",
]

def sample_topic_combos(templates, n_target):
    """Sample (template, topic) pairs without full cross-product blowup, but
    make sure every template AND every topic appears at least once so we keep
    variety in verbs, register, and topic surface forms."""
    combos = [(tpl, t) for tpl in templates for t in TOPICS]
    rng.shuffle(combos)
    chosen = []
    seen_tpl, seen_topic = set(), set()
    remaining = combos[:]
    # first pass: guarantee coverage of every template and every topic
    for tpl, t in combos:
        if tpl not in seen_tpl or t not in seen_topic:
            chosen.append((tpl, t))
            seen_tpl.add(tpl)
            seen_topic.add(t)
            remaining.remove((tpl, t))
        if len(seen_tpl) == len(templates) and len(seen_topic) == len(TOPICS):
            break
    # second pass: fill up to n_target from the remainder
    rng.shuffle(remaining)
    while len(chosen) < n_target and remaining:
        chosen.append(remaining.pop())
    return chosen[:n_target]


for tpl, t in sample_topic_combos(search_templates, 38):
    add(tpl.format(t=t), "SEARCH_NOTES", {"topic": t})
for tpl, t in sample_topic_combos(learn_templates, 38):
    add(tpl.format(t=t), "LEARN_TOPIC", {"topic": t})
for tpl, t in sample_topic_combos(explain_templates, 36):
    add(tpl.format(t=t), "EXPLAIN_TOPIC", {"topic": t})
for tpl, t in sample_topic_combos(quiz_templates, 36):
    add(tpl.format(t=t), "QUIZ_TOPIC", {"topic": t})
for tpl, t in sample_topic_combos(practice_templates, 36):
    add(tpl.format(t=t), "PRACTICE_TOPIC", {"topic": t})

# ---------------------------------------------------------------------------
# GET_ANNOUNCEMENTS / GET_POLLS / GET_FUND_BALANCE / GET_FUND_TRANSACTIONS
# ---------------------------------------------------------------------------
for t in [
    "Any new announcements?", "show me the latest announcements",
    "did the org post anything new", "check announcements",
    "what's the latest announcement", "anything announced recently",
    "show announcements", "what did the org post",
    "give me the announcement feed", "is there a new announcement",
    "any updates posted", "show me what's been announced",
    "did anyone post an announcement", "what's new on the announcement board",
    "let me see recent announcements", "org announcements please",
    "check for new posts", "any news from the org",
    "show the announcement history", "what have they announced lately",
    "pull up announcements", "recent org announcements please",
    "anything posted this week", "give me the announcement rundown",
    "show me all announcements", "did I miss any announcements",
    "check if there's anything new posted", "what's the announcement situation",
    "anything new from the officers", "what's the latest from the org",
    "catch me up on announcements", "any bulletins posted lately",
    "show me the announcement board", "did they announce anything today",
    "give me a heads up on any new posts",
]:
    add(t, "GET_ANNOUNCEMENTS")

for t in [
    "Are there any active polls?", "show me the current polls",
    "any polls I haven't answered", "what polls are open right now",
    "is there a poll I need to vote on", "show active polls",
    "any new polls posted", "give me the poll list",
    "check for open polls", "what's being voted on",
    "any polls I missed", "show me polls I haven't voted in",
    "poll check please", "are there polls to answer",
    "what polls are currently running", "list current polls",
    "did the org post a new poll", "show unanswered polls",
    "any voting happening right now", "check polls for me",
    "what am I supposed to vote on", "give me open polls",
    "are there polls open", "show all active polls right now",
    "poll status please", "anything to vote on today",
    "is voting open on anything", "what's the poll situation right now",
    "give me open votes", "any surveys I need to fill out",
    "show me current voting options", "catch me up on any polls",
]:
    add(t, "GET_POLLS")

for t in [
    "What's our fund balance?", "how much money do we have left",
    "check the org fund balance", "current balance please",
    "what's the current fund total", "how much is in the org account",
    "give me the fund balance", "show current balance",
    "what's our remaining budget", "how much money is left in the fund",
    "balance check please", "what does the fund look like right now",
    "how much do we currently have", "show me the org's current balance",
    "check how much money we have", "fund balance right now",
    "what's left in the treasury", "give me the treasury balance",
    "how much cash do we have on hand", "current fund status please",
    "org balance check", "how much money is in the account",
    "what's the org's balance today", "show total funds available",
    "give me the current financial balance",
    "how are we doing money-wise", "what's left in our funds",
    "give me a balance update", "how much have we got saved up",
    "check our current funds", "what's our financial standing right now",
]:
    add(t, "GET_FUND_BALANCE")

for t in [
    "Show me recent fund transactions", "list the last few expenses",
    "what did we spend money on recently", "transaction history for the fund",
    "show recent deposits and expenses", "give me the transaction log",
    "what's the recent spending history", "show all recent fund activity",
    "list recent deposits", "what transactions happened recently",
    "give me a rundown of recent spending", "show the fund's transaction history",
    "what came in and out of the fund recently", "recent fund activity please",
    "show me where the money went", "list recent fund movements",
    "what's the latest transaction history", "give me recent deposits and withdrawals",
    "show recent financial activity", "transaction log please",
    "what expenses were logged recently", "show recent income and expenses",
    "give me the last few fund transactions", "recent transaction history",
    "show fund transactions from this week",
    "what's been deposited or spent lately", "give me the recent ledger",
    "show me recent debits and credits", "walk me through recent fund activity",
    "what came through the account recently", "give me the past week of transactions",
]:
    add(t, "GET_FUND_TRANSACTIONS")

# ---------------------------------------------------------------------------
# CREATE_DEADLINE
# ---------------------------------------------------------------------------
create_deadline = [
    ("Add an {c} deadline for {d}.", {"course": "{c}", "date": "{d}"}),
    ("Can you add a deadline for {c} {d}?", {"course": "{c}", "date": "{d}"}),
    ("Please create an {c} lab report deadline.", {"course": "{c}", "title": "lab report"}),
    ("I need to add Lab Report to {c}.", {"course": "{c}", "title": "Lab Report"}),
    ("Put an {c} lab report due {d} at {tm}.",
     {"course": "{c}", "title": "lab report", "date": "{d}", "time": "{tm24}"}),
    ("Schedule an {c} deadline for {d} evening.", {"course": "{c}", "date": "{d}"}),
    ("Add this assignment to the deadlines.", {}),
    ("new deadline: {c} project, due {d}", {"course": "{c}", "title": "project", "date": "{d}"}),
    ("set a deadline for the thesis proposal {d}", {"title": "thesis proposal", "date": "{d}"}),
    ("create a deadline for {c} homework due {d}", {"course": "{c}", "title": "homework", "date": "{d}"}),
    ("I have an {c} deadline to add, due {d}", {"course": "{c}", "date": "{d}"}),
    ("please log a new deadline for {c}", {"course": "{c}"}),
    ("add a due date for {c} project", {"course": "{c}", "title": "project"}),
    ("can you set up a deadline, {c}, {d} at {tm}",
     {"course": "{c}", "date": "{d}", "time": "{tm24}"}),
    ("new {c} assignment due {d}, add it", {"course": "{c}", "date": "{d}"}),
    ("track a new deadline for me: {c} report", {"course": "{c}", "title": "report"}),
    ("add deadline", {}),
    ("please make a deadline entry for {c}", {"course": "{c}"}),
]
for tpl, ent_tpl in create_deadline:
    c = rng.choice(COURSES)
    d = rng.choice(DATES)
    tm = rng.choice(TIMES)
    text = tpl.format(c=c, d=d, tm=tm)
    entities = {}
    for k, v in ent_tpl.items():
        if v == "{c}":
            entities[k] = c
        elif v == "{d}":
            entities[k] = d
        elif v == "{tm24}":
            entities[k] = to_24h(tm)
        else:
            entities[k] = v
    add(text, "CREATE_DEADLINE", entities)
# a few more with varied courses/dates to broaden coverage
for c in COURSES:
    for d in ["tomorrow", "Friday", "next Monday"]:
        add(f"add a {c} deadline due {d}", "CREATE_DEADLINE", {"course": c, "date": d})
        add(f"create a new deadline for {c}, due {d}", "CREATE_DEADLINE", {"course": c, "date": d})

# ---------------------------------------------------------------------------
# UPDATE_DEADLINE
# ---------------------------------------------------------------------------
for c in COURSES:
    d = rng.choice(DATES)
    add(f"Move the {c} deadline to {d}", "UPDATE_DEADLINE", {"course": c, "date": d})
    add(f"reschedule the {c} deadline to {d}", "UPDATE_DEADLINE", {"course": c, "date": d})
    add(f"update the {c} deadline time to {rng.choice(TIMES)}", "UPDATE_DEADLINE", {"course": c})
    add(f"push the {c} deadline back a day", "UPDATE_DEADLINE", {"course": c})
for i in DEADLINE_IDS:
    add(f"change deadline {i} to next week", "UPDATE_DEADLINE", {"deadline_id": i, "date": "next week"})
    add(f"move deadline {i} to Friday", "UPDATE_DEADLINE", {"deadline_id": i, "date": "Friday"})
    add(f"can you reschedule deadline {i}", "UPDATE_DEADLINE", {"deadline_id": i})
for t in [
    "can you push the lab report deadline back a day",
    "reschedule my thesis deadline",
    "move my thesis proposal deadline to next week",
    "change the due date on the lab report",
    "shift the project deadline forward a couple days",
    "update the time on the lab report deadline",
    "can we push my deadline later",
    "I need to move a deadline, the thesis one",
    "change the lab report due date to next Friday",
    "edit the deadline for the group project",
]:
    add(t, "UPDATE_DEADLINE")

# ---------------------------------------------------------------------------
# DELETE_DEADLINE -- hard negatives vs MARK_NO_CLASS: "remove/cancel X" phrased
# about a deadline (delete) vs about a class session (no class).
# ---------------------------------------------------------------------------
for i in DEADLINE_IDS:
    add(f"Could you remove deadline {i}?", "DELETE_DEADLINE", {"deadline_id": i})
    add(f"cancel deadline {i} please", "DELETE_DEADLINE", {"deadline_id": i})
    add(f"delete deadline {i}", "DELETE_DEADLINE", {"deadline_id": i})
    add(f"get rid of deadline {i}", "DELETE_DEADLINE", {"deadline_id": i})
for c in COURSES:
    add(f"delete the {c} deadline", "DELETE_DEADLINE", {"course": c})
    add(f"remove the {c} deadline", "DELETE_DEADLINE", {"course": c})
    add(f"cancel the {c} deadline", "DELETE_DEADLINE", {"course": c})
    add(f"get rid of the {c} deadline entry", "DELETE_DEADLINE", {"course": c})
for t in [
    "get rid of the lab report deadline",
    "remove that Networks deadline",
    "delete the thesis proposal deadline",
    "I don't need that deadline anymore, remove it",
    "take that deadline off my list",
    "clear the lab report deadline",
    "erase the project deadline",
    "delete that old deadline entry",
]:
    add(t, "DELETE_DEADLINE")

# ---------------------------------------------------------------------------
# MARK_NO_CLASS
# ---------------------------------------------------------------------------
for c in COURSES:
    for d in ["today", "tomorrow", "Friday"]:
        add(f"Can you mark {c} as having no class {d}?", "MARK_NO_CLASS", {"course": c, "date": d})
        add(f"no class for {c} {d}", "MARK_NO_CLASS", {"course": c, "date": d})
        add(f"mark {c} as cancelled {d}", "MARK_NO_CLASS", {"course": c, "date": d})
for t in [
    "there's no class in LCD this Friday",
    "professor cancelled HDL tomorrow, update it",
    "class got cancelled for Networks today",
    "our CS101 professor isn't holding class tomorrow",
    "no class today, mark it in the schedule",
    "Thesis class is cancelled this week",
    "remove HDL from tomorrow's schedule, no class",
    "HDL is cancelled tomorrow, not deleted just no class",
    "mark that there's no LCD session today",
    "flag Networks as no-class for tomorrow",
    "cancel HDL class for tomorrow (not the deadline, the class)",
    "there won't be class in CS101 tomorrow",
]:
    add(t, "MARK_NO_CLASS")

# explicit hard-negative contrast pairs for DELETE_DEADLINE vs MARK_NO_CLASS
add("remove HDL from my schedule tomorrow, no class that day", "MARK_NO_CLASS", {"course": "HDL", "date": "tomorrow"})
add("remove the HDL deadline, it's cancelled", "DELETE_DEADLINE", {"course": "HDL"})
add("cancel HDL tomorrow", "MARK_NO_CLASS", {"course": "HDL", "date": "tomorrow"})
add("cancel the HDL deadline", "DELETE_DEADLINE", {"course": "HDL"})

# ---------------------------------------------------------------------------
# CREATE_ANNOUNCEMENT / CREATE_NOTE / CREATE_POLL
# ---------------------------------------------------------------------------
for t in [
    "Post an announcement about the meeting on Friday",
    "make an announcement that the event is postponed",
    "announce that dues are due next week",
    "can you post something about the general assembly",
    "let everyone know the meeting moved to Friday",
    "put up an announcement about elections",
    "announce the new officer list",
    "post that the venue changed",
    "make an announcement for the fundraiser",
    "I need to announce something to the org",
    "put out an announcement about the deadline extension",
    "announce that the event was rescheduled",
    "post an update about the budget meeting",
    "let members know about the schedule change",
    "announce the winner of the raffle",
    "post something about tomorrow's GA",
    "share an announcement about the workshop",
    "put out a notice about the new deadline",
    "tell everyone the meeting is cancelled",
    "post an announcement for the recruitment drive",
    "make an org-wide announcement about dues",
    "announce that applications are now open",
    "post a notice about the volunteer sign-up",
    "announce the schedule for finals week",
    "put up a notice that membership renewal is open",
    "share news about the upcoming social event",
    "announce that the officer elections start Monday",
    "post an announcement about room changes",
    "let the org know the deadline was extended",
    "announce that the workshop slots are full",
    "post about the change in event schedule",
]:
    add(t, "CREATE_ANNOUNCEMENT")

for t in [
    "Save a note about today's lecture on TCP",
    "add a note: remember to review chapter 4",
    "create a note titled midterm review",
    "jot down these notes on karnaugh maps",
    "make a note about the recursion lecture",
    "write down a note for later on hash tables",
    "save this as a note: check office hours",
    "take a note about today's class",
    "add a quick note about SQL joins",
    "create a note for the study group meeting",
    "jot this down: review OSI layers before quiz",
    "save a note titled exam prep",
    "note to self: finish the thesis outline",
    "add a note about the group project ideas",
    "write a note summarizing today's lesson",
    "save a quick note about the assignment instructions",
    "create a note with today's key takeaways",
    "jot down a reminder about the quiz format",
    "make a note about what the professor said",
    "add a note recapping the study session",
    "write down a note before I forget this",
    "save a note with the homework instructions",
    "create a note called project ideas",
    "jot down what was covered in lecture today",
    "add a note about the group meeting outcomes",
    "save my thoughts on today's reading as a note",
    "make a note of the professor's office hours",
    "add a note listing key formulas from class",
    "create a note about tips from the review session",
    "jot a quick note about the exam coverage",
]:
    add(t, "CREATE_NOTE")

for t in [
    "Create a poll asking what time works for the meetup",
    "make a poll for the event date",
    "can you set up a poll about the venue",
    "start a poll for choosing the theme",
    "put together a poll for the meeting time",
    "make a poll asking who's attending",
    "create a poll about the fundraiser idea",
    "set up a vote for the new logo",
    "poll the members about the schedule change",
    "start a poll on where to hold the event",
    "create a quick poll for snack preferences",
    "set up a poll to pick the meeting day",
    "make a poll for choosing between two venues",
    "start a poll to gauge interest in the workshop",
    "create a poll for choosing the next officer",
    "set up a poll about the event format",
    "make a poll asking for feedback on the last event",
    "poll everyone on the best time to meet",
    "start a vote on the merch design",
    "create a poll for picking the T-shirt color",
    "set up a poll about the field trip destination",
    "make a poll to decide the fundraiser theme",
    "start a poll asking about dietary restrictions",
    "create a poll for the general assembly agenda",
    "make a poll about preferred meeting platform",
    "set up a poll for choosing event sponsors",
    "create a poll asking which day works best",
    "start a poll on the budget allocation",
    "make a poll for choosing the guest speaker",
    "set up a poll about the community service project",
]:
    add(t, "CREATE_POLL")

# ---------------------------------------------------------------------------
# RECORD_DEPOSIT / RECORD_EXPENSE
# ---------------------------------------------------------------------------
for amt, phrase in AMOUNTS_DEPOSIT:
    add(f"Record a deposit of {phrase}", "RECORD_DEPOSIT", {"amount": amt})
    add(f"log a deposit of {phrase}", "RECORD_DEPOSIT", {"amount": amt})
    add(f"we received {phrase} from membership dues, log it", "RECORD_DEPOSIT", {"amount": amt})
    add(f"add a deposit of {phrase} to the fund", "RECORD_DEPOSIT", {"amount": amt})
for t in [
    "add a 600 pesos deposit from sponsorship",
    "log a 250 peso membership fee deposit",
    "record that we got 900 from the bake sale",
    "we deposited 1500 today, please log it",
    "add this deposit: 700 from ticket sales",
    "put in a deposit of 2500 from the sponsor",
    "log a 400 peso deposit from merch sales",
    "record a 1800 deposit from the fundraiser",
    "we got 350 from raffle tickets, log the deposit",
    "add a deposit, 950 pesos, from alumni donation",
    "record a 3000 peso deposit from the school grant",
    "log the 200 peso deposit from t-shirt sales",
    "we collected 1100 in dues, please deposit it",
    "add a deposit of 175 from bake sale leftovers",
]:
    add(t, "RECORD_DEPOSIT")

for amt, phrase, desc in AMOUNTS_EXPENSE:
    add(f"Record an expense of {phrase} for {desc}", "RECORD_EXPENSE", {"amount": amt, "description": desc})
    add(f"log an expense of {phrase} for {desc}", "RECORD_EXPENSE", {"amount": amt, "description": desc})
    add(f"we spent {phrase} on {desc}, log that", "RECORD_EXPENSE", {"amount": amt, "description": desc})
for t in [
    "add an expense of 200 for decorations",
    "log a 600 peso expense for transportation",
    "record that we spent 350 on snacks",
    "put in an expense of 1200 for the venue deposit",
    "we paid 500 for printing flyers, log the expense",
    "add a 900 peso expense for catering",
    "log a 250 expense for supplies restock",
    "record 1100 spent on the photobooth",
    "we used 400 for prizes, log that expense",
    "add an expense entry, 650 pesos for tarpaulins",
    "record that we paid 300 for permits",
    "log a 700 peso expense for transportation rental",
    "we spent 550 on certificates, log the expense",
    "add an expense of 950 for the guest speaker",
    "record an expense of 275 for cleaning supplies",
    "log 480 spent on banners for the event",
    "add an expense of 620 for equipment rental",
    "we paid 190 for parking, log the expense",
]:
    add(t, "RECORD_EXPENSE")

# ---------------------------------------------------------------------------
# Cross-intent hard negatives (spec: GET_DEADLINES vs GET_COURSE_DEADLINES,
# PRACTICE_TOPIC vs QUIZ_TOPIC already covered structurally above by giving
# every topic all five verbs; add a few explicit lexical-overlap traps)
# ---------------------------------------------------------------------------
add("what's due for all my classes, not just one", "GET_DEADLINES")
add("what's due, just for HDL though", "GET_COURSE_DEADLINES", {"course": "HDL"})
add("quiz me, not practice, on sorting algorithms", "QUIZ_TOPIC", {"topic": "sorting algorithms"})
add("I want practice problems, not a quiz, on OSI layers", "PRACTICE_TOPIC", {"topic": "OSI layers"})
add("just explain it, don't quiz me, on recursion", "EXPLAIN_TOPIC", {"topic": "recursion"})
add("teach me first before I take a quiz on joins in SQL", "LEARN_TOPIC", {"topic": "joins in SQL"})

random_state = rng.getstate()
rng.shuffle(records)

os.makedirs(DATA_DIR, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

from collections import Counter
counts = Counter(r["intent"] for r in records)
print(f"Wrote {len(records)} examples across {len(counts)} intents to {OUT_PATH}")
for intent in sorted(counts):
    print(f"  {intent}: {counts[intent]}")
under_30 = {k: v for k, v in counts.items() if v < 30}
if under_30:
    print("\nWARNING: intents below 30 examples:", under_30)
