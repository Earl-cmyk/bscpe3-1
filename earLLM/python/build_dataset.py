"""
build_dataset.py

Generates data/intents.jsonl for Reinitialized.

Each record:
{
  "text": "...",
  "intent": "CREATE_DEADLINE",
  "entities": {"course": "HDL", "title": "Lab Report", "date": "tomorrow"}
}

This is intentionally hand-authored (not templated) so phrasing stays
naturalistic per section 6 of the project spec (short/long, formal/casual,
questions/commands, incomplete phrases, different word orders).

Run:
    python python/build_dataset.py
Writes:
    data/intents.jsonl
"""

import json
import os

# Each entry: (text, intent, entities_dict)
EXAMPLES = [
    # ---------------- GET_SCHEDULE ----------------
    ("What's my schedule?", "GET_SCHEDULE", {}),
    ("Show me my class schedule", "GET_SCHEDULE", {}),
    ("Can you pull up my schedule", "GET_SCHEDULE", {}),
    ("schedule pls", "GET_SCHEDULE", {}),
    ("What classes do I have this week", "GET_SCHEDULE", {}),
    ("give me my full weekly timetable", "GET_SCHEDULE", {}),
    ("I need to see my class schedule", "GET_SCHEDULE", {}),

    # ---------------- GET_TODAY_SCHEDULE ----------------
    ("What do I have today?", "GET_TODAY_SCHEDULE", {"date": "today"}),
    ("Show me today's classes", "GET_TODAY_SCHEDULE", {"date": "today"}),
    ("do I have class today", "GET_TODAY_SCHEDULE", {"date": "today"}),
    ("What's on my plate today", "GET_TODAY_SCHEDULE", {"date": "today"}),
    ("today's schedule please", "GET_TODAY_SCHEDULE", {"date": "today"}),
    ("Any classes today?", "GET_TODAY_SCHEDULE", {"date": "today"}),

    # ---------------- GET_TOMORROW_SCHEDULE ----------------
    ("What do I have tomorrow?", "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"}),
    ("show tomorrow's classes", "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"}),
    ("do I have class tomorrow", "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"}),
    ("What's my schedule for tomorrow", "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"}),
    ("tomorrow's classes?", "GET_TOMORROW_SCHEDULE", {"date": "tomorrow"}),

    # ---------------- GET_DEADLINES ----------------
    ("What deadlines do I have?", "GET_DEADLINES", {}),
    ("Show me all my deadlines", "GET_DEADLINES", {}),
    ("list my pending deadlines", "GET_DEADLINES", {}),
    ("what's due", "GET_DEADLINES", {}),
    ("Can you give me my deadlines", "GET_DEADLINES", {}),
    ("anything due soon?", "GET_DEADLINES", {}),

    # ---------------- GET_COURSE_DEADLINES ----------------
    ("What deadlines do I have for HDL?", "GET_COURSE_DEADLINES", {"course": "HDL"}),
    ("show me LCD deadlines", "GET_COURSE_DEADLINES", {"course": "LCD"}),
    ("anything due in Networks class", "GET_COURSE_DEADLINES", {"course": "Networks"}),
    ("what's due for CS101", "GET_COURSE_DEADLINES", {"course": "CS101"}),
    ("list deadlines for my Thesis course", "GET_COURSE_DEADLINES", {"course": "Thesis"}),

    # ---------------- GET_WEEK_DEADLINES ----------------
    ("What's due this week?", "GET_WEEK_DEADLINES", {"date": "this week"}),
    ("show deadlines for the week", "GET_WEEK_DEADLINES", {"date": "this week"}),
    ("what do I have due next week", "GET_WEEK_DEADLINES", {"date": "next week"}),
    ("weekly deadline roundup please", "GET_WEEK_DEADLINES", {"date": "this week"}),

    # ---------------- SEARCH_NOTES ----------------
    ("Find my notes on binary trees", "SEARCH_NOTES", {"topic": "binary trees"}),
    ("search my notes for recursion", "SEARCH_NOTES", {"topic": "recursion"}),
    ("do I have notes about finite automata", "SEARCH_NOTES", {"topic": "finite automata"}),
    ("look up my notes on 2's complement", "SEARCH_NOTES", {"topic": "2's complement"}),
    ("pull up notes about database normalization", "SEARCH_NOTES", {"topic": "database normalization"}),

    # ---------------- LEARN_TOPIC ----------------
    ("How do I use 3's complement?", "LEARN_TOPIC", {"topic": "3's complement"}),
    ("teach me about binary search trees", "LEARN_TOPIC", {"topic": "binary search trees"}),
    ("I want to learn dynamic programming", "LEARN_TOPIC", {"topic": "dynamic programming"}),
    ("can you help me understand karnaugh maps", "LEARN_TOPIC", {"topic": "karnaugh maps"}),
    ("what is normalization in databases", "LEARN_TOPIC", {"topic": "normalization"}),

    # ---------------- EXPLAIN_TOPIC ----------------
    ("Explain how a hash table works", "EXPLAIN_TOPIC", {"topic": "hash table"}),
    ("can you explain TCP handshakes", "EXPLAIN_TOPIC", {"topic": "TCP handshakes"}),
    ("explain recursion like I'm five", "EXPLAIN_TOPIC", {"topic": "recursion"}),
    ("break down how joins work in SQL", "EXPLAIN_TOPIC", {"topic": "joins in SQL"}),

    # ---------------- QUIZ_TOPIC ----------------
    ("Quiz me on data structures", "QUIZ_TOPIC", {"topic": "data structures"}),
    ("give me a quiz on OSI layers", "QUIZ_TOPIC", {"topic": "OSI layers"}),
    ("test my knowledge of Boolean algebra", "QUIZ_TOPIC", {"topic": "Boolean algebra"}),
    ("can you quiz me on regular expressions", "QUIZ_TOPIC", {"topic": "regular expressions"}),

    # ---------------- PRACTICE_TOPIC ----------------
    ("Give me practice problems on sorting algorithms", "PRACTICE_TOPIC", {"topic": "sorting algorithms"}),
    ("I want to practice SQL joins", "PRACTICE_TOPIC", {"topic": "SQL joins"}),
    ("practice questions for combinational logic please", "PRACTICE_TOPIC", {"topic": "combinational logic"}),

    # ---------------- GET_ANNOUNCEMENTS ----------------
    ("Any new announcements?", "GET_ANNOUNCEMENTS", {}),
    ("show me the latest announcements", "GET_ANNOUNCEMENTS", {}),
    ("did the org post anything new", "GET_ANNOUNCEMENTS", {}),
    ("check announcements", "GET_ANNOUNCEMENTS", {}),

    # ---------------- GET_POLLS ----------------
    ("Are there any active polls?", "GET_POLLS", {}),
    ("show me the current polls", "GET_POLLS", {}),
    ("any polls I haven't answered", "GET_POLLS", {}),

    # ---------------- GET_FUND_BALANCE ----------------
    ("What's our fund balance?", "GET_FUND_BALANCE", {}),
    ("how much money do we have left", "GET_FUND_BALANCE", {}),
    ("check the org fund balance", "GET_FUND_BALANCE", {}),
    ("current balance please", "GET_FUND_BALANCE", {}),

    # ---------------- GET_FUND_TRANSACTIONS ----------------
    ("Show me recent fund transactions", "GET_FUND_TRANSACTIONS", {}),
    ("list the last few expenses", "GET_FUND_TRANSACTIONS", {}),
    ("what did we spend money on recently", "GET_FUND_TRANSACTIONS", {}),
    ("transaction history for the fund", "GET_FUND_TRANSACTIONS", {}),

    # ---------------- CREATE_DEADLINE ----------------
    ("Add an HDL deadline for tomorrow.", "CREATE_DEADLINE", {"course": "HDL", "date": "tomorrow"}),
    ("Can you add a deadline for HDL tomorrow?", "CREATE_DEADLINE", {"course": "HDL", "date": "tomorrow"}),
    ("Please create an HDL lab report deadline.", "CREATE_DEADLINE", {"course": "HDL", "title": "lab report"}),
    ("I need to add Lab Report to HDL.", "CREATE_DEADLINE", {"course": "HDL", "title": "Lab Report"}),
    ("Put an HDL lab report due tomorrow at 6 PM.", "CREATE_DEADLINE",
     {"course": "HDL", "title": "lab report", "date": "tomorrow", "time": "18:00"}),
    ("Schedule an HDL deadline for tomorrow evening.", "CREATE_DEADLINE", {"course": "HDL", "date": "tomorrow"}),
    ("Add this assignment to the deadlines.", "CREATE_DEADLINE", {}),
    ("new deadline: Networks project, due Friday", "CREATE_DEADLINE", {"course": "Networks", "title": "project", "date": "Friday"}),
    ("set a deadline for the thesis proposal next Monday", "CREATE_DEADLINE", {"title": "thesis proposal", "date": "next Monday"}),

    # ---------------- UPDATE_DEADLINE ----------------
    ("Move the HDL deadline to Friday", "UPDATE_DEADLINE", {"course": "HDL", "date": "Friday"}),
    ("change deadline 7 to next week", "UPDATE_DEADLINE", {"deadline_id": 7, "date": "next week"}),
    ("can you push the lab report deadline back a day", "UPDATE_DEADLINE", {"title": "lab report", "date": "+1 day"}),
    ("update the Networks deadline time to 5 PM", "UPDATE_DEADLINE", {"course": "Networks", "time": "17:00"}),
    ("reschedule my thesis deadline", "UPDATE_DEADLINE", {"title": "thesis"}),

    # ---------------- DELETE_DEADLINE ----------------
    ("Could you remove deadline 7?", "DELETE_DEADLINE", {"deadline_id": 7}),
    ("delete the HDL deadline", "DELETE_DEADLINE", {"course": "HDL"}),
    ("cancel deadline 12 please", "DELETE_DEADLINE", {"deadline_id": 12}),
    ("get rid of the lab report deadline", "DELETE_DEADLINE", {"title": "lab report"}),
    ("remove that Networks deadline", "DELETE_DEADLINE", {"course": "Networks"}),

    # ---------------- MARK_NO_CLASS ----------------
    ("Can you mark LCD as having no class tomorrow?", "MARK_NO_CLASS", {"course": "LCD", "date": "tomorrow"}),
    ("no class for HDL today", "MARK_NO_CLASS", {"course": "HDL", "date": "today"}),
    ("mark Networks as cancelled tomorrow", "MARK_NO_CLASS", {"course": "Networks", "date": "tomorrow"}),
    ("there's no class in LCD this Friday", "MARK_NO_CLASS", {"course": "LCD", "date": "Friday"}),
    ("professor cancelled HDL tomorrow, update it", "MARK_NO_CLASS", {"course": "HDL", "date": "tomorrow"}),

    # ---------------- CREATE_ANNOUNCEMENT ----------------
    ("Post an announcement about the meeting on Friday", "CREATE_ANNOUNCEMENT", {"date": "Friday"}),
    ("make an announcement that the event is postponed", "CREATE_ANNOUNCEMENT", {}),
    ("announce that dues are due next week", "CREATE_ANNOUNCEMENT", {"date": "next week"}),
    ("can you post something about the general assembly", "CREATE_ANNOUNCEMENT", {}),

    # ---------------- CREATE_NOTE ----------------
    ("Save a note about today's lecture on TCP", "CREATE_NOTE", {"topic": "TCP"}),
    ("add a note: remember to review chapter 4", "CREATE_NOTE", {}),
    ("create a note titled midterm review", "CREATE_NOTE", {"title": "midterm review"}),
    ("jot down these notes on karnaugh maps", "CREATE_NOTE", {"topic": "karnaugh maps"}),

    # ---------------- CREATE_POLL ----------------
    ("Create a poll asking what time works for the meetup", "CREATE_POLL", {}),
    ("make a poll for the event date", "CREATE_POLL", {}),
    ("can you set up a poll about the venue", "CREATE_POLL", {}),

    # ---------------- RECORD_DEPOSIT ----------------
    ("Record a deposit of 500 pesos", "RECORD_DEPOSIT", {"amount": 500}),
    ("we received 1200 from membership dues, log it", "RECORD_DEPOSIT", {"amount": 1200}),
    ("add a deposit of ₱2,000 to the fund", "RECORD_DEPOSIT", {"amount": 2000}),
    ("log a 300 peso deposit from sponsorship", "RECORD_DEPOSIT", {"amount": 300}),

    # ---------------- RECORD_EXPENSE ----------------
    ("Record an expense of 150 for printing", "RECORD_EXPENSE", {"amount": 150, "description": "printing"}),
    ("we spent 800 on food for the event, log that", "RECORD_EXPENSE", {"amount": 800, "description": "food for the event"}),
    ("add an expense of ₱450 for supplies", "RECORD_EXPENSE", {"amount": 450, "description": "supplies"}),
    ("log a 1000 peso expense for the venue rental", "RECORD_EXPENSE", {"amount": 1000, "description": "venue rental"}),
]


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "intents.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for text, intent, entities in EXAMPLES:
            record = {"text": text, "intent": intent, "entities": entities}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    intents = sorted(set(intent for _, intent, _ in EXAMPLES))
    print(f"Wrote {len(EXAMPLES)} examples covering {len(intents)} intents to {out_path}")
    for i in intents:
        print(f"  - {i}")


if __name__ == "__main__":
    main()
