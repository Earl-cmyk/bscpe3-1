## R3-1N assistant

Say `Rein Mastercontrol please` in the assistant bar before a mutating command. R3-1N requests the PIN for each command and does not display or retain it.

Supported commands:

- `Set deadline <date/time> for <course> titled <title> for <reason>`
- `No classes <course> on <date>`
- `Deposit <amount> for <reason>`
- `Withdraw <amount> for <reason>`

Dates support ISO values and common phrases such as `today`, `tomorrow`, weekdays, and `August 24, 2026`. Deadlines are interpreted in `Asia/Manila`, stored as UTC instants, and displayed/grouped in Manila time. Withdrawals begin as pending budget entries.

Recurring classes are static. They appear visually in Week and Day calendar views only; Month view remains deadline-focused. A no-class exception applies to one course on one date and can be restored with the PIN.
