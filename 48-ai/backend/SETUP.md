# Jane backend: setup and app connection

One file (`jane_backend.py`, Python 3.9+, no installs) gives you:
- **Phone answering** through Twilio: greeting that says Jane is an AI, takes the job, books a free slot, flags urgent/gas/water calls, handles "are you a robot?", price questions and "talk to a person".
- **The API the app calls**: Today, Inbox, Bookings, Jane settings, usage.
- **Minute metering**, and **forwarding** to the owner when Jane is off, outside her hours, or the plan's minutes run out.
- It does **not record calls** (no recording code), so the greeting doesn't claim recording. If you add recording later, the greeting must say so and you must check consent law (see the brief).

**Status: tested only with simulated Twilio requests, never with a real Twilio account or phone call.** Expect to debug the first real call. Jane's conversation is scripted rules (same as the prototype), not a live AI model, so unusual replies will confuse her.

## 1. Run it
```bash
export TWILIO_AUTH_TOKEN=...        # from your Twilio console
export ADMIN_TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
export JANE_PUBLIC_URL=https://jane.yourdomain.com   # must match the URL Twilio calls exactly
python3 jane_backend.py             # listens on :8470
```
It needs a public HTTPS address. Options: a small always-on server (put it behind Caddy/nginx for HTTPS), or a tunnel for testing (ngrok / cloudflared). Back up `jane.db` (SQLite). Don't put the tokens in git.

## 2. Twilio
1. Buy an Australian number (check Twilio's regulatory requirements for AU numbers; they can take time).
2. Number > Voice > "A call comes in": Webhook, `POST`, `https://jane.yourdomain.com/twilio/voice`.
3. Status callback URL: `https://jane.yourdomain.com/twilio/status` (needed for minute metering).
4. Voice is set by `JANE_VOICE` (default `Polly.Nicole`, en-AU). Check Twilio's current voice list.
5. Costs: Twilio charges per minute for the number, calls and speech recognition. Measure your real cost per minute before pricing.

## 3. Create a business (admin only)
```bash
curl -X POST $JANE_PUBLIC_URL/admin/business -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Wigg'\''s Plumbing & Gas","owner":"Wigg","twilio_number":"+61860000001","forward_phone":"+61400123456","plan_minutes":150}'
```
Returns an `api_key` once. The app stores it in the iPhone Keychain. Never ship the admin token in the app.

## 4. API for the app (all `Authorization: Bearer <api_key>`, JSON)
| Screen | Call |
|---|---|
| Header / Jane tab | `GET /v1/me` -> name, owner, mode, plan_minutes, minutes_used |
| Today | `GET /v1/today` -> calls, booked, next job, today's jobs |
| Inbox | `GET /v1/inbox`; `POST /v1/inbox/{id}/clear` |
| Bookings | `GET /v1/bookings?from=YYYY-MM-DD&to=YYYY-MM-DD`; `POST /v1/bookings` {date,time,customer,job,address,phone}; `POST /v1/jobs/{id}/done` |
| Jane toggle | `POST /v1/settings` {"mode":"on\|after\|off","forward_phone":"+61..."} |
"After hours" means outside Mon-Fri 8:00-17:00 Perth time (edit `within_hours`). Poll every 30-60 s, or add push notifications later (needs Apple Push setup; not built).

## 5. Not built yet
- Live avatar video (vendor API; keep keys on the server). Push notifications. SMS confirmations (check the Spam Act first). Call recordings and "Play call". Real speech-model conversation. Payments/subscriptions (StoreKit). Multi-user team accounts. Languages other than English (beta in the prototype only).

## 6. Before real customers
Real test calls (ten scenarios in the brief), HTTPS, backups, a privacy policy, recording/AI-disclosure legal check, terms of service, and a cost-per-minute measurement. Not legal advice.
