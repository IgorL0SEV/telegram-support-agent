# TOOLS.md - ╨Ы╨╛╨║╨░╨╗╤М╨╜╨░╤П ╨╜╨░╤Б╤В╤А╨╛╨╣╨║╨░ ╨░╨│╨╡╨╜╤В╨░

## ╨У╨╗╨░╨▓╨╜╤Л╨╣ skill

```text
telegram-support-operator
telegram-support-analyst
```

╨д╨░╨╣╨╗╤Л:

```text
~/.openclaw/skills/telegram-support-operator/SKILL.md
~/.openclaw/skills/telegram-support-analyst/SKILL.md
```

## ╨а╨░╨▒╨╛╤З╨░╤П ╨┤╨╕╤А╨╡╨║╤В╨╛╤А╨╕╤П ╨░╨│╨╡╨╜╤В╨░

```text
~/.openclaw/workspace/telegram-support-agent
```

## ╨С╨░╨╖╨░ ╨╖╨╜╨░╨╜╨╕╨╣

```text
knowledge_base/faq.md
policies/support_policy.md
```

## ╨Ф╨░╨╜╨╜╤Л╨╡

```text
data/orders_sample.csv
data/customer_context.csv
data/quality_questions.csv
db/init/001_schema.sql
db/init/002_seed.sql
```

## ╨Ы╨╛╨║╨░╨╗╤М╨╜╤Л╨╣ Supabase

╨Ъ╨╛╨╜╤В╨╡╨╣╨╜╨╡╤А╤Л:

```text
openclaw-support-supabase-db
openclaw-support-pg-meta
openclaw-support-studio
```

╨Я╨╛╨┤╨╜╤П╤В╤М Supabase:

```bash
docker compose up -d
scripts/apply_db.sh
```

Supabase Studio:

```text
http://localhost:54325/project/default
```

╨Я╨╛╨┤╨║╨╗╤О╤З╨╡╨╜╨╕╨╡ ╨║ ╨▒╨░╨╖╨╡:

```text
host: localhost
port: 54324
database: postgres
user: supabase_admin
password: postgres
```

╨Я╨╛╨╗╨╜╨╛╤Б╤В╤М╤О ╨┐╨╡╤А╨╡╤Б╨╛╨╖╨┤╨░╤В╤М Supabase DB ╨╕╨╖ init-╤Д╨░╨╣╨╗╨╛╨▓:

```bash
scripts/reset_db.sh
```

╨Я╤А╨╕╨╝╨╡╨╜╨╕╤В╤М ╤Б╤Е╨╡╨╝╤Г ╨╕ ╨┤╨░╨╜╨╜╤Л╨╡ ╨▒╨╡╨╖ ╤Г╨┤╨░╨╗╨╡╨╜╨╕╤П volume:

```bash
scripts/apply_db.sh
```

╨Я╤А╨╛╨▓╨╡╤А╨╕╤В╤М ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╡:

```bash
python3 scripts/support_db.py health
```

## ╨С╤Л╤Б╤В╤А╤Л╨╣ ╨┐╨╛╨╕╤Б╨║ ╨┐╨╛ ╨▒╨░╨╖╨╡ ╨╖╨╜╨░╨╜╨╕╨╣

```bash
python3 scripts/support_lookup.py "╨║╨░╨║ ╨╛╤Д╨╛╤А╨╝╨╕╤В╤М ╨▓╨╛╨╖╨▓╤А╨░╤В"
python3 scripts/support_lookup.py "╤В╨╛╨▓╨░╤А ╨┐╤А╨╕╤И╤С╨╗ ╤А╨░╨╖╨▒╨╕╤В╤Л╨╣"
python3 scripts/support_lookup.py "╨╝╨╛╨╢╨╜╨╛ ╨▒╨╡╤А╨╡╨╝╨╡╨╜╨╜╤Л╨╝ ╤Н╤В╨╛╤В ╨║╤А╨╡╨╝"
```

## ╨Ч╨░╨┐╤А╨╛╤Б╤Л ╨░╨╜╨░╨╗╨╕╤В╨╕╨║╨░ ╨║ ╨С╨Ф

```bash
python3 scripts/support_db.py order ORD-1042
python3 scripts/support_db.py customer @anna_care
python3 scripts/support_db.py tickets
python3 scripts/support_db.py metrics
python3 scripts/support_db.py delayed
python3 scripts/support_db.py faq ╨▓╨╛╨╖╨▓╤А╨░╤В
python3 scripts/support_db.py sql "SELECT status, count(*) FROM orders GROUP BY status"
```

`sql` ╨┐╤А╨╕╨╜╨╕╨╝╨░╨╡╤В ╤В╨╛╨╗╤М╨║╨╛ `SELECT` ╨╕╨╗╨╕ `WITH`.

## ╨Ч╨░╨┐╤Г╤Б╨║ ╤З╨╡╤А╨╡╨╖ dashboard

1. ╨Ю╤В╨║╤А╨╛╨╣ dashboard:

```bash
openclaw dashboard
```

2. ╨Т╤Л╨▒╨╡╤А╨╕ ╨░╨│╨╡╨╜╤В╨░:

```text
telegram-support-agent
```

3. ╨Ю╤В╨┐╤А╨░╨▓╤М ╨╛╨▒╤А╨░╤Й╨╡╨╜╨╕╨╡ ╨║╨╗╨╕╨╡╨╜╤В╨░:

```text
╨Ъ╨╗╨╕╨╡╨╜╤В @anna_care ╤Б╨┐╤А╨░╤И╨╕╨▓╨░╨╡╤В: "╨У╨┤╨╡ ╨╝╨╛╨╣ ╨╖╨░╨║╨░╨╖ ORD-1042?"
╨б╤Д╨╛╤А╨╝╨╕╤А╤Г╨╣ ╨╛╤В╨▓╨╡╤В ╨║╨╗╨╕╨╡╨╜╤В╤Г ╨╕ ╨▓╨╜╤Г╤В╤А╨╡╨╜╨╜╤О╤О ╨╖╨░╨╝╨╡╤В╨║╤Г.
```

╨Я╤А╨╛╨▓╨╡╤А╨║╨░ ╨░╨╜╨░╨╗╨╕╤В╨╕╨║╨╕:

```text
╨Я╤А╨╛╨▓╨╡╤А╤М ╨▓ ╨▒╨░╨╖╨╡ ╨╖╨░╨║╨░╨╖ ORD-1042 ╨╕ ╤Б╤Д╨╛╤А╨╝╨╕╤А╤Г╨╣ ╨╛╤В╨▓╨╡╤В ╨║╨╗╨╕╨╡╨╜╤В╤Г ╨┐╨╛ ╤Б╤В╨░╤В╤Г╤Б╤Г ╨┤╨╛╤Б╤В╨░╨▓╨║╨╕.
```

```text
╨Я╨╛╨║╨░╨╢╨╕ ╨╝╨╡╤В╤А╨╕╨║╨╕ ╨┐╨╛╨┤╨┤╨╡╤А╨╢╨║╨╕ ╨╕ ╤Б╨┐╨╕╤Б╨╛╨║ ╨┐╤А╨╛╤Б╤А╨╛╤З╨╡╨╜╨╜╤Л╤Е ╨┤╨╛╤Б╤В╨░╨▓╨╛╨║.
```

## ╨Ч╨░╨┐╤Г╤Б╨║ ╨╕╨╖ ╤В╨╡╤А╨╝╨╕╨╜╨░╨╗╨░

```bash
openclaw agent --agent telegram-support-agent --message "╨Ъ╨╗╨╕╨╡╨╜╤В ╤Б╨┐╤А╨░╤И╨╕╨▓╨░╨╡╤В: ╨Ъ╨░╨║ ╨╛╤Д╨╛╤А╨╝╨╕╤В╤М ╨▓╨╛╨╖╨▓╤А╨░╤В, ╨╡╤Б╨╗╨╕ ╤В╨╛╨▓╨░╤А ╨╜╨╡ ╨┐╨╛╨┤╨╛╤И╤С╨╗? ╨б╤Д╨╛╤А╨╝╨╕╤А╤Г╨╣ ╨╛╤В╨▓╨╡╤В ╨║╨╗╨╕╨╡╨╜╤В╤Г ╨╕ ╨▓╨╜╤Г╤В╤А╨╡╨╜╨╜╤О╤О ╨╖╨░╨╝╨╡╤В╨║╤Г."
```

## ╨Ъ╤Г╨┤╨░ ╨╖╨░╨┐╨╕╤Б╤Л╨▓╨░╤В╤М ╤Н╤Б╨║╨░╨╗╨░╤Ж╨╕╨╕

```text
logs/escalation_log.md
```

╨Х╤Б╨╗╨╕ ╨╛╨▒╤А╨░╤Й╨╡╨╜╨╕╨╡ ╤В╤А╨╡╨▒╤Г╨╡╤В ╤З╨╡╨╗╨╛╨▓╨╡╨║╨░, ╨░╨│╨╡╨╜╤В ╨┤╨╛╨╗╨╢╨╡╨╜ ╤Б╤Д╨╛╤А╨╝╨╕╤А╨╛╨▓╨░╤В╤М ╨▓╨╜╤Г╤В╤А╨╡╨╜╨╜╤О╤О ╨╖╨░╨╝╨╡╤В╨║╤Г ╨╕ ╨┐╤А╨╕ ╨╜╨╡╨╛╨▒╤Е╨╛╨┤╨╕╨╝╨╛╤Б╤В╨╕ ╨┤╨╛╨▒╨░╨▓╨╕╤В╤М ╨╖╨░╨┐╨╕╤Б╤М ╨▓ ╨╢╤Г╤А╨╜╨░╨╗.
