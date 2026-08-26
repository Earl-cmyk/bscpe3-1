# Rein integration contract

Reinitialized is a local NLU service. It returns a prediction and does not perform application mutations.

## Start

```bash
cd rust
cargo run --release -- serve --bind 127.0.0.1:8787
```

## Request

```http
POST /predict
Content-Type: application/json

{"text":"Could you remove deadline 7?"}
```

## Response

```json
{
  "intent": "DELETE_DEADLINE",
  "confidence": 0.99,
  "confidence_band": "high",
  "entities": {
    "deadline_id": 7
  }
}
```

## Flask-side rule

Treat the response as untrusted input. Validate the intent against the application's allowlist and validate every entity against the existing Mastercontrol schema.

For reads:

```text
Reinitialized -> Rein read service
```

For mutations:

```text
Reinitialized
  -> Rein Mastercontrol prepare
  -> PIN authentication
  -> confirmation
  -> single-use action token
  -> execution
  -> audit
```

Never allow the NLU service to receive a database connection, SQL string, PIN, or Mastercontrol secret.
