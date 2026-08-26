# R3-1NFORCE 

R3-1NFORCE is a Flask web app for tracking deadlines, class schedules, notes, announcements, and a shared class fund.

## Use the website

### Home and calendar

The home page shows deadlines and the class schedule. Use the Month, Week, and Day controls to change the view, the previous/next controls to move through dates, and Today to return to the current date. Click a deadline to view its details.

Recurring classes are shown in Week and Day views. Month view is focused on deadlines. Schedule times and deadline entry are interpreted in `Asia/Manila`; deadlines are stored as UTC timestamps.

To add or edit a deadline, choose the corresponding action and enter the PIN when prompted. A deadline includes a title, course, description, deadline date/time, difficulty, and optional attachment. Deleting a deadline also requires the PIN.

### Tasks

Open **Tasks** from the navigation bar to browse, filter, complete, edit, or delete deadlines. Use the calendar on the home page for date-based planning. A task can be opened from its calendar entry to see its full description and attachment.

### Notes

Open **Notes** to read notes or filter them by course. Creating, editing, and deleting a note requires the PIN. Notes support formatted captions and file attachments; image and video attachments can be previewed in the media viewer.

### Class fund

Open **Class fund** to select a wallet and view its balance, deposits, withdrawals, and audit history. Adding a wallet, recording a deposit or withdrawal, editing payers, and changing a withdrawal status require the PIN. Withdrawals start as `pending` and can later be marked as spent or cancelled.

Amounts are displayed in Philippine pesos (`PHP`). Enter positive amounts and provide a reason for every entry.

### Announcements and polls

Open **Announcements** to read announcements, links, attachments, and polls. Voting asks for a school ID. A school ID can vote only once per announcement, and it must be present in `valid_school_ids.txt` (or the corresponding configured data source).

### Search

Use the search field in the navigation bar to search notes, announcements, and deadlines. Results can be filtered by type. Read-only search does not require the PIN.

## Complete function guide

### Post an announcement

1. On **Home**, select the `+` button beside the dashboard.
2. Enter an announcement title and message.
3. Optionally add a link and one attachment.
4. To add a poll, open the poll controls and enter at least two different choices.
5. Select **Post**. The PIN is requested before the form opens.

Posted announcements appear on Home and in **Announcements** history. Anyone with a valid school ID can select a poll choice once per announcement.

### Add or manage a task

1. Open **Tasks**.
2. Select **Add task** and enter the title, course, description, Manila date/time, and difficulty.
3. Optionally attach a file, then select **Save task**.
4. Select a task on the calendar to view it. Use **Edit** or **Delete** for changes; both require the PIN.

The calendar can be viewed by Month, Week, or Day. Use **No classes** to cancel one recurring course on a selected date. Existing exceptions appear in that date's schedule and can be restored with the PIN.

### Add or manage a note

1. Open **Notes** and optionally choose a course filter.
2. Select the `+` button.
3. Enter a title, choose a course, write the caption, and optionally attach files.
4. Select **Post note**. The PIN is requested first.
5. Use **Edit** or **Delete** on an existing note and confirm with the PIN.

Captions support formatting, links, colors, highlights, lists, and emojis. Images and videos can be previewed from the note feed.

### Set up the class fund

1. Open **Class fund**.
2. Select **Add wallet**, enter a wallet name, optionally associate a course, and provide the PIN.
3. Select **Add payer** to create a contributor, then provide the PIN if prompted.
4. Select a wallet from the wallet selector.
5. Select the `+` button to record a movement.
6. Choose **Deposit** or **Withdraw**, enter the amount, wallet, payer, reason, and any attachment, then submit with the PIN.

The page shows the balance, deposit total, withdrawal total, entries, and audit history. Pending withdrawals can be marked **spent** or **cancelled**. Use **Edit payers** on an entry to update its payer list; this also requires the PIN.

### Browse announcements and vote

Open **Announcements** from an announcement history link or navigate to `/announcements`. Read the full announcement, open its link or attachment, and select a poll choice. Enter a school ID when prompted. Only IDs listed in `valid_school_ids.txt` can vote, and each ID can vote once per announcement.

## R3-1N assistant

The assistant bar is available at the bottom of every page. Use it to query schedules, spending, and deadlines. Use the navigation search field to search notes, announcements, and deadlines.

### Normal Rein commands

Normal Rein commands are read-only. Type one of these in the assistant bar:

| Command | Result |
| --- | --- |
| `What is my schedule for today?` | Shows today's recurring classes and no-class exceptions. |
| `Schedule today` | Same as the schedule question above. |
| `My schedule today` | Same as the schedule question above. |
| `Deadlines today` | Lists deadlines due today. |
| `Deadlines this week` | Lists deadlines due during the current week. |
| `Deadlines this month` | Lists deadlines due during the current month. |
| `To do for HDL today` | Lists today's tasks for the named course. |
| `To do for LCD on 2026-08-25` | Lists tasks for a course on an ISO date. |
| `To do for DDC from 2026-08-25 to 2026-08-31` | Lists tasks for a course across an ISO date range. |
| `Class fund used today` | Lists spent withdrawals recorded today. |
| `Class fund used this week` | Lists spent withdrawals recorded this week. |
| `Class fund use this month` | Lists spent withdrawals recorded this month. |

Use one of these course names where a course is required: `HDL`, `LCD`, `DDC`, `CEDD`, `FOSS`, `TRW`, `Elec`, or `Engr Econ`.

### Rein Mastercontrol commands

Mastercontrol is for changes. First send this exact activation phrase:

```text
Rein Mastercontrol please
```

Then send one command from this list. Rein requests the PIN for the command and does not display or retain it in the conversation.

| Command format | Example |
| --- | --- |
| `Set deadline <date/time> for <course> titled <title> for <reason>` | `Set deadline tomorrow 6 PM for HDL titled Lab report for submit the final report` |
| `No classes <course> on <date>` | `No classes LCD on 2026-08-25` |
| `Deposit <amount> to <wallet or course> for <reason>` | `Deposit 500 to HDL for class materials` |
| `Withdraw <amount> to <wallet or course> for <reason>` | `Withdraw 125 to HDL for printing` |

The deposit and withdrawal commands require a course wallet that already exists. The website form is required for announcements, notes, attachments, payers, and wallet creation because those features are not assistant commands.

Dates support ISO values and common phrases such as `today`, `tomorrow`, weekdays, and `August 24, 2026`. Deadlines are interpreted in `Asia/Manila`, stored as UTC instants, and displayed in Manila time. Assistant-created deadlines use `Medium` difficulty and the reason as their description. Withdrawals begin as pending budget entries.

To cancel a class for one course on one date, use `No classes`. The exception can be restored from the schedule view after PIN verification.

## Security checklist

- Use a private PIN and set it through `TASK_PIN`.
- Do not commit `.env`, database files, uploaded files, or deployment secrets.
- Do not paste the PIN into assistant messages, issue reports, screenshots, or chat logs.
- Keep `SUPABASE_SECRET_KEY` server-side only.
- Use HTTPS and platform-managed secrets when deploying publicly.

## Deployment

`run:app` is the configured Vercel entry point. A deployment also needs a persistent PostgreSQL `DATABASE_URL`, the private `TASK_PIN`, and Supabase Storage settings if attachments should persist outside the app filesystem. Configure these values in the hosting provider's environment settings, then deploy the project using that provider's normal workflow.

The assistant uses the persistent Rust earLLM service described in [docs/earllm_integration.md](docs/earllm_integration.md). For local development, start it before Flask:

```powershell
cd earLLM/rust
cargo run --release -- serve --bind 127.0.0.1:8787
```

Set `EARLLM_URL` and `EARLLM_TIMEOUT` in the Flask environment. `127.0.0.1` is local-only. Vercel cannot host the long-running Rust listener as a sidecar, so production requires a separately hosted earLLM service reachable through a private or authenticated HTTPS URL. Do not deploy with the local default URL.
