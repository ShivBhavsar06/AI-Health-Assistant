# Deploying HealthMate AI on Render (free tier)

This guide hosts the Flask app on [Render](https://render.com) (free web service) with a
[TiDB Cloud Starter](https://tidbcloud.com) database (free, MySQL-compatible, no credit card).

**Architecture**

```
Browser ──HTTPS──> Render free web service (gunicorn + Flask) ──TLS──> TiDB Cloud Starter (MySQL)
                                 │
                                 └── uploads/ (ephemeral, cleared on restart)
```

Everything below fits free plans. Expect the caveats in [Free-tier limitations](#free-tier-limitations).

---

## 1. Create the database (TiDB Cloud Starter)

1. Sign up at <https://tidbcloud.com> (no credit card).
2. Create a **Starter** instance. MySQL-compatible is the default; pick the region closest to
   your users (for India, `ap-southeast-1` / Singapore).
3. In the instance's **Connect** dialog, copy:
   - host (`gateway01.<region>.prod.aws.tidbcloud.com`)
   - port (`4000`)
   - username (looks like `3pTAoNNegb47Uc8.root` — include the prefix)
   - password (click **Generate password** and save it)
   - default database name (usually `test`)
4. The app creates its tables but **not** the database. Use `test`, or create one in the
   TiDB SQL editor: `CREATE DATABASE ai_health_management;`
5. Download the **CA certificate** shown in the Connect dialog (e.g. `isrgrootx1.pem`).
   You will upload it to Render.
6. Optional: set the instance's monthly spending limit to **$0** so it can never bill you.

> TiDB requires TLS. The app connects with TLS whenever `DB_SSL_CA` is set.

## 2. Push the deployment files

`render.yaml` (Render blueprint), `gunicorn`, and the TLS-aware config are already committed
in this repo. Push the commit if it is not on GitHub yet:

```powershell
git push
```

## 3. Create the Render service

1. Sign up at <https://render.com> with GitHub and grant access to `AI-Health-Assistant-`.
2. **New → Blueprint**, select the repository. Render reads `render.yaml` and asks for the
   `sync: false` values:

   | Variable | Value |
   | --- | --- |
   | `DB_HOST` | TiDB host from step 1 |
   | `DB_PORT` | `4000` |
   | `DB_NAME` | `test` (or a database you created) |
   | `DB_USER` | `3pTAoNNegb47Uc8.root` |
   | `DB_PASSWORD` | TiDB password |
   | `DB_SSL_CA` | leave blank for now (see next step) |
   | `OPENROUTER_API_KEY` | optional — leave blank to disable AI features |
   | `OPENROUTER_SITE_URL` | your `https://<service>.onrender.com` URL |

   `DB_SSL_REQUIRE=True` is already set by the blueprint, so the first deploy connects over
   TLS even before a CA certificate exists.

3. After the first deploy, open the service → **Environment → Secret Files → Add Secret File**:
   - Filename: `isrgrootx1.pem`
   - Contents: the CA certificate downloaded in step 1

   Then set `DB_SSL_CA=/etc/secrets/isrgrootx1.pem` and click **Manual Deploy → Deploy latest
   commit**. Secret files are mounted read-only at `/etc/secrets/`, which is why the path starts
   there. This step upgrades the connection from encrypted to fully verified.

4. `SECRET_KEY` is generated automatically, `DEBUG=False`, and cookies are marked secure —
   all set by the blueprint.

### Manual setup instead of the blueprint

| Setting | Value |
| --- | --- |
| Environment | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --access-logfile -` |
| Instance type | Free |
| Environment variables | as in the table above, plus `PYTHON_VERSION=3.12.7`, `DEBUG=False`, `SESSION_COOKIE_SECURE=True`, and a unique `SECRET_KEY` |

## 4. Create the administrator account

Free Render services have **no shell**, so run the CLI against the cloud database from your
machine. The tables are created automatically the first time the app boots, so open the
Render URL once before doing this.

With the same database values in your local `.env`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "from run import app"
flask --app run.py create-admin
```

Then sign in at `https://<your-service>.onrender.com/admin/login`.

## 4b. AI features (optional, still $0)

AI is disabled when `OPENROUTER_API_KEY` is empty; everything else keeps working. To enable
it for free, the app accepts any OpenAI-compatible provider — no paid OpenAI key required:

| Provider | Get a key | `OPENROUTER_BASE_URL` | `OPENROUTER_MODEL` |
| --- | --- | --- | --- |
| Groq (no card, fast) | <https://console.groq.com/keys> | `https://api.groq.com/openai/v1` | `openai/gpt-oss-120b` |
| Google AI Studio (no card) | <https://aistudio.google.com/apikey> | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash` |
| OpenRouter (`:free` models) | <https://openrouter.ai/keys> | `https://openrouter.ai/api/v1` | a model ending in `:free` |

Set those three variables in Render → Environment (and in local `.env` to test). Notes:

- Groq requires phone verification and allows ~30 requests/min, 1,000/day.
- Google's free tier may use prompts for product improvement outside the EEA/UK/CH — avoid it
  for real patient data.
- Image-based report summaries need a vision model (Gemini or an OpenRouter vision model).

## 5. Verify

- `https://<your-service>.onrender.com/` loads the landing page.
- Sign up as a patient, log out, log back in.
- Admin login works.
- AI chat only responds if `OPENROUTER_API_KEY` is set.

## Free-tier limitations

| Behaviour | Impact |
| --- | --- |
| Service sleeps after 15 min without traffic | First visit after idle takes ~1 minute. |
| Ephemeral filesystem | Uploaded reports/photos disappear on every restart, redeploy, or wake-up. Records saved in MySQL are unaffected. |
| No SMTP on ports 25/465/587 | Password-reset/OTP emails cannot be sent. With no `MAIL_*` variables set, the OTP is printed to the Render **Logs** instead. |
| 750 instance hours/month | ~31 days of a single service; fine for one app. |
| 512 MB RAM / 0.1 CPU | Enough for a demo; large report generation is slow. |
| TiDB free quota | 5 GiB storage and 50M request units per month; set the spending limit to $0. |

Anything that must survive restarts needs a paid plan (persistent disk) or object storage
(e.g. S3/R2). The app already stores all health data in MySQL, so only file uploads are at risk.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `(1045, "Access denied for user ...")` | Use the full TiDB username including the instance prefix; re-check the password. |
| `SSL connection error` / `certificate verify failed` | Confirm the secret file is named exactly `isrgrootx1.pem`, `DB_SSL_CA=/etc/secrets/isrgrootx1.pem` is set, and the deploy was restarted after adding the file. |
| `Can't connect to MySQL server` | Keep `DB_PORT=4000` and ensure the Render service is in a region near the database. |
| Build fails on Python version | Remove the `PYTHON_VERSION` env var to use Render's current default, then redeploy. |
| 500 on every page | Check **Logs**; the most common cause is a wrong `DATABASE_URL`/`DB_*` value. |

## Using a different MySQL host

Set `DATABASE_URL` instead of the `DB_*` variables (it takes precedence):

```
DATABASE_URL=mysql+pymysql://user:password@host:3306/database
```

URL-encode special characters in the password. If the provider requires TLS without a
downloadable CA, set `DB_SSL_REQUIRE=True` and `DB_SSL_VERIFY=False` to encrypt without
certificate pinning.
