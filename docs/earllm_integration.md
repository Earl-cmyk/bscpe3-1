# earLLM Integration

## Architecture

Rein is a Flask application. It owns authentication, PIN verification, authorization, business validation, database access, Mastercontrol actions, confirmation, and audit logging. Notes are stored and searched by Rein, including SQLite FTS support.

earLLM is a local Rust service that loads the existing model artifact once at startup. It performs intent classification and deterministic entity extraction. It has no Rein database credentials, PIN access, authorization privileges, or mutation functions.

The boundary is:

```text
User -> Rein Flask -> earLLM -> intent/entities/confidence -> Rein router
                                      |                    |
                                      |                    +-- reads and note grounding
                                      |                    +-- Mastercontrol prepare -> PIN -> confirmation -> execute
                                      +-- never performs actions
```

## Protocol

The configured `EARLLM_URL` points to the service base URL. Rein sends:

```http
POST /predict
Content-Type: application/json

{"text":"Could you remove deadline 7?"}
```

The existing Rust server returns:

```json
{
  "intent": "DELETE_DEADLINE",
  "confidence": 0.99,
  "confidence_band": "high",
  "entities": {"deadline_id": 7}
}
```

Rein also recognizes the service health endpoint `GET /health`, which returns `{"ok":true,"service":"reinitialized"}`. The Flask adapter validates the response as untrusted input before routing it.

## Intent contract

Supported mappings use existing Rein behavior:

| earLLM intent | Rein behavior |
| --- | --- |
| `GET_SCHEDULE`, `GET_TODAY_SCHEDULE`, `GET_TOMORROW_SCHEDULE` | Schedule read |
| `GET_DEADLINES`, `GET_COURSE_DEADLINES`, `GET_WEEK_DEADLINES` | Deadline read |
| `LEARN_TOPIC`, `SEARCH_NOTES` | Note-grounded learning/search |
| `CREATE_DEADLINE` | Mastercontrol `create_deadline` |
| `DELETE_DEADLINE` | Mastercontrol `delete_deadline` |
| `MARK_NO_CLASS` | Mastercontrol `add_no_class_exception` |
| `RECORD_DEPOSIT`, `RECORD_EXPENSE` | Mastercontrol transaction proposal |

Other model labels are returned as unavailable until Rein has a corresponding supported handler and complete entity contract. No generated learning answer is produced by earLLM.

## Entity contract

The Rust service returns entities such as `course`, `date`, `time`, `amount`, numeric IDs, `title`, `description`, and `topic`. Rein validates types, lengths, positive IDs and amounts, and allowed courses. It combines separate date/time values before using the existing `Asia/Manila` date helpers. Courses are resolved against Rein's configured course list and aliases rather than the Rust service's legacy course list.

Missing required entities produce clarification or Mastercontrol validation errors. Model output never directly reaches a database function without Rein validation.

## Security boundary

Reads execute only through Rein read helpers. Mutations create a normalized proposal and must use:

1. Mastercontrol argument validation.
2. Server-side PIN verification.
3. A short-lived confirmation token.
4. Explicit user confirmation.
5. Single-use token consumption.
6. Existing database dispatch and audit logging.

The chat message alone cannot mutate data. PIN values are not sent to earLLM, stored in browser storage, or written to logs. earLLM has no database connection and cannot call Mastercontrol.

## Local deployment

Start the persistent Rust service once:

```powershell
cd earLLM/rust
cargo run --release -- serve --bind 127.0.0.1:8787
```

In another terminal, configure the local service explicitly and start Rein:

```powershell
$env:EARLLM_URL = "http://127.0.0.1:8787"
$env:EARLLM_TIMEOUT = "2.0"
python run.py
```

Do not spawn Rust per chat request. The model is loaded by the persistent server. If earLLM is unavailable, normal non-assistant website operations continue and assistant requests receive a controlled unavailable response.

## Production

`127.0.0.1` is for local development only. The current serverless/Vercel-oriented Flask deployment cannot run the long-lived Rust listener as a sidecar. Production therefore requires a separately hosted earLLM service, reachable from Flask through a private or authenticated HTTPS URL. Configure that URL with `EARLLM_URL` and set an appropriate `EARLLM_TIMEOUT`; do not commit it or credentials to the repository.

The Rust service currently does not provide application authentication or TLS itself. Production hosting must provide network isolation, HTTPS, access control, health monitoring, and resource limits. If the Flask host cannot make private outbound requests to the service, the deployment architecture must be changed before enabling the integration.

## Limitations

The existing model artifact and Rust architecture are unchanged. Some intents do not have complete Rein handlers or entities, including richer announcement/poll workflows and general explanation, practice, or quiz responses. Those requests are deliberately reported as unavailable or require clarification rather than being guessed or fabricated.
