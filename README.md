# Hermes Muse 0.3.1

[简体中文](README.zh-CN.md) · [Design](docs/DESIGN.md) · [Acceptance guide](docs/ACCEPTANCE.md)

An assistant that only answers when you speak leaves a lot undone: the trip you mentioned on Monday, the reply you were waiting for, the decision you said you would make by month-end. Hermes Muse is a plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that lets Hermes follow up on those things itself. It was inspired by the proactive interactions in [Meta's Muse](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/).

In practice it looks like this:

- You say you are going to Hangzhou this weekend. Before you leave it checks the forecast and your calendar, and only speaks up if something changed enough to matter.
- You say you want to pick a bicycle by month-end. It keeps comparing options in the background, brings back what it found, and closes the goal only when you have actually decided.
- A reply you were waiting for arrives, or a meeting moves. The next check notices, reads the original mail or event, and tells you in your Bot Chat what happened and why it matters.
- "Done", "later" and "stop bringing this up" each do something different. When there is nothing worth saying, it stays quiet.

It is built on what Hermes already has: memory, Cron, Skills and subagents, with your existing model and memory backend. Reminders go to the current profile's Bot Chat. Hindsight, Obsidian and other named services are optional. This is an independent project, unaffiliated with Meta/Muse; its code and prompts are independently written.

## Plugin pages

Muse's Dashboard and Desktop page lets you choose a profile and browse its Feed, Ideas and Goals inside Hermes. It follows the host theme.

![Muse overview with Feed article list](docs/images/muse-dashboard-overview.png)
*Choose a profile, browse or search its Feed articles, and switch to Ideas or Goals. All screenshots use demo data.*

![Muse Feed article body](docs/images/muse-feed-article.png)
*Open a Feed article to read its Markdown-rendered text, with its sources listed below.*

![Muse Ideas](docs/images/muse-ideas.png)
*Ideas groups suggestions by the goal they relate to and links them back to its topic.*

![Muse Goals](docs/images/muse-goals.png)
*Goals lists open goals first, with status, next check and latest progress; done and cancelled goals are folded below.*

## Install

```sh
hermes plugins install xiaohei-info/hermes-muse --enable
```

Installation uses the selected profile. Use `hermes -p default plugins install xiaohei-info/hermes-muse --enable` for default, or replace `default` with a profile name such as `architect`. Each enabled profile gets its own state, six jobs and Bot Chat delivery; omitting `-p` follows the current profile selection.

If you maintain explicit `platform_toolsets` lists, include `muse` in the platforms where you use the plugin. An enabled plugin can otherwise load its prompts while its state tool remains unavailable.

Requires Hermes 0.21.5 and the relevant plugin APIs; see the [tested baseline](docs/ACCEPTANCE.md). First load creates the workspace, registers one Skill, one state tool (`muse_manage`) and six hooks, adds one system prompt section, and creates six recurring Cron jobs. There is no feature selection or separate initialization command. Without a running host, loading happens at the next Hermes start.

The system prompt section takes effect in new conversations. Background execution requires a running scheduler and an available model. Scheduled checks, research and content generation use the existing model and tools at their normal cost.

Mutation-lock acquisition waits at most two seconds per lock boundary, including local-thread contention. A busy boundary fails with `resource_busy` instead of waiting indefinitely; it does not clear the holder, roll back an earlier completed step, or authorize replay of an uncertain request. The bound is not an overall initialization or critical-section deadline. Inspect the original operation and coordinate active owners before recovery; never delete live lock files to bypass contention.

## Feature comparison

The plugin sets up its jobs and rules on first load, using the existing Hermes model and sources, with notifications handled in the current profile's Bot Chat.

| Muse feature | Native Hermes | With Hermes Muse |
| --- | --- | --- |
| Remember preferences and recent context | Built-in memory and user notes retain facts. Scheduled relationship upkeep and nightly review need their own setup. | Memory upkeep is ready to use: conversations, sourced facts and task outcomes inform relationship notes. A separate nightly review carries useful lessons into later conversations. |
| Notice important changes | Cron, session heartbeats and messaging are built in. You configure what to watch, when to notify, deduplication and frequency limits. | A ready-to-use patrol checks connected mail, calendars, reminders and devices, then weighs changes against your recent context. Weather, travel and interest news can prompt a message when they are useful. |
| Follow goals over time | Persistent tasks and a task board are built in. You organize long-term goals, progress, related watches and stopping conditions. | Follow plans agreed in conversation across days and close them on verified outcomes. After explaining the result, the parent marks the goal done and its future watches stop. |
| Prepare work in the background | Asynchronous subagents are built in. You configure which goals to research regularly and how to save and use the results. | Independent multi-step work goes to native asynchronous subagents while the main conversation stays available. Research batches finish and return without repeated status requests. |
| Offer relevant suggestions | Can suggest next steps using conversation and memory. Ongoing research, selection and storage need their own setup. | Prepares suggestions from goals and verified personal context, records evidence and feedback, and leaves new proposals for the user to choose. Accepted work keeps moving. |
| Personalized Feed | Search, writing and scheduled tasks are available. You assemble topic selection, article records, feedback and updates. | A local Feed is ready to use: existing memory, interests and feedback guide quiet article generation without requiring a saved goal. Search, discuss or delete articles through chat, or browse them on the Dashboard page. |
| Adjust reminders and stop following up | Can update preferences and stop jobs. You define how feedback affects reminders, goals and watches. | “Done,” “later” and “stop bringing this up” have distinct effects. Completion, cancellation or rescheduling prompts a fresh check of pending reminders; temporary interests expire after 14 days. |
| Handle everyday errands | Can use browser and external tools. Calling, booking and payment services and workflows need to be connected and configured. | The plugin does not supply calling, booking or payment workflows. Existing tools remain available. |

Feed articles can be browsed on the read-only [Dashboard and Desktop pages](#unified-dashboard-host). New research batches use native Hermes execution and result callbacks; restart recovery depends on the host, and unknown outcomes are never automatically replayed. Memory upkeep, verification and writing depend on the configured model and tools; see the [implementation details](docs/FEATURE-COVERAGE.md).

## Skill and tool

| Name | Purpose |
| --- | --- |
| [hermes-muse:companion](skills/companion/SKILL.md) | Shared procedures for conversations and background jobs, including thinking through a request’s practical consequences and carrying the plan into the task: connection and device checks, goals and interests, reminders and feedback, memory and relationships, Feed, delegation, checks of its own actions, subscribed daily briefings, and weekly/monthly reviews. |
| muse_manage | One tool with 40 actions ([interface](docs/INTERFACE.md)). Lets the assistant record and query source checks, goals, interests, reminders, feedback, Feed and research progress, keep source progress by connection, account and resource, distinguish complete, partial and failed checks, maintain expiry, stopping and delivery state, and inspect native tool receipts and unresolved mistakes. Lists are paged and requests and responses have size limits; goals use an optional integer revision; other managed changes retain revision/request-key replay. |

The Skill is registered with the plugin and its files stay in the plugin directory. Conversations load the relevant procedure as needed; all six recurring Cron jobs use the same Skill. Use normal conversation and let the assistant call the tool. When you change a task, it considers the purpose and practical consequences, updates the actual task and verifies the result before confirming. Checking frequency and notification frequency stay separate; the reply explains what matters in natural language, without a fixed script.

The [briefing procedure](skills/companion/references/briefings.md) also supports a daily overview on a schedule you request. It checks your connected sources, reads relevant mail threads and task details, and explains what needs attention. An existing report can use this procedure without creating another job. These subscriptions remain user-managed native Cron jobs; the plugin does not import them automatically or add a seventh default job. Updates preserve their schedule and configuration.

## Prompts

The plugin includes eight prompt files:

| File | Purpose |
| --- | --- |
| [receiving.md](prompts/receiving.md) | Shared Bot Chat handoff: turn internal findings into a direct response to the user, as a self-contained message from the same assistant, reading original sources when a missing detail affects the judgment, then explaining the verified findings without acknowledging the job or creating another reminder. |
| [system.md](prompts/system.md) | Take ownership of requests and changes, explain useful judgments in the user’s voice, keep the main conversation available, and retain unfinished commitments. |
| [proactive-watch.md](prompts/proactive-watch.md) | Discover available connections/devices, check changes and approaching deadlines, record source coverage, then verify and notify or remain silent. |
| [memory-upkeep.md](prompts/memory-upkeep.md) | Process new conversations and facts; check its own operations for mistakes, verify repairs, and update memory and progress. |
| [nightly-review.md](prompts/nightly-review.md) | Review conversations independently of hourly upkeep; update alignment, research goals and suggestions, check closure and unresolved mistakes, and review working lessons and skills. |
| [feed-pulse.md](prompts/feed-pulse.md) | Use native memory, preferences, current context and real sources to choose topics; quietly write only when there is new value. |
| [weekly-governance-review.md](prompts/weekly-governance-review.md) | Review outcomes and effort, missed sources, unfinished work and repeated reminders; suggest next-week adjustments. |
| [monthly-system-audit.md](prompts/monthly-system-audit.md) | Check whether instructions and recurring work still help, look for duplicate workflows and work that should have stopped, and suggest simplifications. |

Hermes appends `system.md` after the memory section through its plugin API; it takes effect in new conversations. `receiving.md` accompanies Bot Chat results and is also used by the receiving conversation hook. The six task files become the corresponding Cron job prompts and are used when those jobs run. Each plugin load refreshes these job prompts while preserving the user's schedule, model and pause settings.

## Accepted work and follow-through

A goal has one status: **active, done or cancelled**. When a checked result has been
explained to the user, call `goal_update(id=..., status="done", note="...")`.
Optional owner handles link native delegation, Cron, Paseo or external work; checking
an owner never dispatches again or automatically completes a goal. Due active goals
appear in `context(section="followups")`; ordinary turns get at most a short reminder.
Children and Cron can inspect/report, while private parent conversations own goals.
Goals need no request ID, reply hash, handoff or caller scope token. An optional integer
expected_revision prevents stale writes and returns the current goal on conflict.

## Calendar views and preparation

Ask “Show my next 30 days” for a rolling interval from now to the same local time 30 days later, or “Show this month” for the natural calendar month. Both use the active profile timezone. IANA timezones follow DST; a native fixed-offset timezone keeps that offset and explicitly reports that DST transitions are unavailable. Original all-day calendar dates stay visible alongside profile-date overlays. Daily schedules retain source/calendar names, recurring exceptions and cancellations, multi-day events, busy dates, overlaps and preparation reasons.

The existing patrol also reads the full next 30 days, including preparation opportunities on days 8–30. It retains the 30-minute schedule, quiet hours, relevance rules and notice lifecycle; distant events do not create extra watches or automatic daily alerts. All enabled authorized Apple, Google and other calendar accounts/resources are discovered and paged through existing tools. Missing collections/pages, unavailable permissions and errors remain coverage gaps; partial results never establish global free time.

The existing `muse_manage` tool adds stateless `calendar_window` and `calendar_view` actions, documented in the [calendar procedure](skills/companion/references/calendar.md). There is no calendar database, sync service, provider requirement or write permission. Rolling and natural-month checks have independent stable source resources and preserve legacy seven-day checkpoints. Dedup uses exact source/account/calendar and occurrence identity; cross-calendar UID copies remain separate unless resolved through original evidence. Matching titles/times never merge distinct events. Assembly validates reported connector observations; actual discovery, reads and preparation judgment remain the model's responsibility.

Apple PIM receipts also support a bounded observation mode: actual returned events remain visible with original UTC times, source provenance and explicitly labelled device all-day display dates. Source timezone, original recurrence identity, cancellation history and availability remain unavailable; Apple coverage stays partial even when all current query pages were read. No connector service or permission changes are needed. See the calendar procedure for the raw receipt format and its limits.

## Conversation hooks

| Hook | Purpose |
| --- | --- |
| pre_llm_call | Before the reply, records up to 8,000 user characters and source identity, and adds a state-tool pointer for goals, interests and feedback. Native Cron results, including other jobs, receive the shared guidance for a self-contained reply instead of becoming user signals. |
| post_llm_call | Associates owned Cron sessions with their native execution IDs for self-review. After replying to a user message of at least 80 characters, waits for five quiet minutes before scheduling memory upkeep. New input cancels the pending timer; at most three early triggers per day. |
| transform_llm_output | For a patrol/watch that used the state tool, replaces the final response with approved notice bodies or `[SILENT]`. Bot Chat notices and weekly/monthly reports include the same receiving guidance. Ordinary conversations and direct channel reports are unchanged. |
| post_tool_call | Captures minimal correlated memory/skill write feedback from actual native results, without copying memory bodies. |
| on_skill_lifecycle | Marks a recent `skill_manage` write receipt as observed by Hermes' skill lifecycle. Without a matching tool receipt nothing is inferred. Memory and skill writes are classified from their actual tool results (saved, waiting approval, submitted but unconfirmed, failed, unchanged, unknown), keeping only minimal correlation references. |
| on_session_end | Clears the current turn's busy flag so later reminders do not keep waiting on a conversation that has ended. |

User-signal hooks process private and local conversations, skipping groups, Cron, subagent input and completion callbacks. Older misclassified background messages remain as audit evidence outside the user-signal inbox. The output hook is bound to the current owned patrol/watch or governance execution; it does not modify ordinary replies. Delayed upkeep uses the existing memory Cron job. Unloading the plugin from the running process cancels its temporary timers.

Delegates are instructed to remain read-only under inherited host permissions; this is not a hard file/terminal/browser/MCP sandbox.

## Six recurring Cron jobs

| Job | Default schedule | Output |
| --- | --- | --- |
| muse-proactive-watch | Every 30 minutes | Source coverage, worthwhile reminders, evidence and delivery state |
| muse-memory-upkeep | Hourly | New facts and people/group notes |
| muse-nightly-review | Daily at 03:20 | Alignment, goal research, Ideas, working lessons and skill review |
| muse-feed-pulse | Hourly | Local Feed articles |
| muse-weekly-governance-review | Sunday at 21:15 | A concrete review of usefulness, execution and proposed adjustments |
| muse-monthly-system-audit | First day of the month at 10:40 | A short audit of priorities, instructions and recurring work |

The plugin does not pin a model or provider on its recurring jobs. Hermes resolves the model at each run: **per-job model → current profile’s `cron.model` → profile’s main model**. Without a Cron default, hourly background work can use the same expensive model as your main conversation. Set a background model before leaving the scheduler running.

Muse workers always use public native delegation, respecting the user’s delegation provider/model/reasoning/concurrency settings. The parent is only the unconfigured default (leave `delegation.provider` and `delegation.model` empty to keep the parent model); native stateless Cron joins results. Research allocates at most three workers within lower user limits. Audit workers read full paged current-profile evidence through muse_manage; the parent verifies and commits reviewed slots. Every page is preserved. No global configuration changes. See [exact boundaries](docs/CATALOG-COMPATIBILITY.md).

For example, merge this into the current profile’s `config.yaml`, using a model and provider available in your installation (`llm` here is a configured provider name):

```yaml
cron:
  model: gpt-6-luna
  model_provider: llm
agent:
  reasoning_overrides:
    gpt-6-luna: high
```

Hermes currently resolves reasoning from a per-job `reasoning_effort`, then the model-specific override, then `agent.reasoning_effort`; `cron.reasoning_effort` is not a supported setting on the tested baseline. The example sets `high` for Luna in this profile, including ordinary conversations that use Luna. Existing per-job model/reasoning choices take priority and survive plugin reloads. Cron defaults are read on the next run. Bot Chat’s receiving turn uses its own conversation model configuration and adds another model call; `cron.model` does not select that receiving model. The plugin does not write these model settings for you. Research workers follow Hermes delegation settings, including `delegation.model`; `cron.model` does not override their model. Audit uses parallel evidence review with direct parent review as fallback.

Schedules use the current Hermes timezone. Watches with an explicit expiry stop when due. Explicitly requested timed reminders and watches can create additional recorded Cron jobs; six is the permanent job count. A new repeating watch (interval or cron) must be provably at least 30 minutes apart or it is refused; a one-off schedule is exempt, and existing jobs are not rewritten. A patrol delivers approved notices in its own final response, with no extra delivery Cron. Deferred candidates stay for the next patrol. Delivery is checked against that execution’s persistent receipt, independently of later patrols.

All six fixed jobs call the model on schedule to inspect the information relevant to their work. Each patrol discovers available connections and devices and checks mail, calendars, reminders and other sources even without saved goals or interests. Each source reuses a stable record and a tested read recipe. Verified tool aliases reuse the established source record; duplicate observations are archived without advancing its successful checkpoint. Different accounts and collections stay separate. Reducing calls must preserve substantive content, sound judgment, proactive help, relevant context and timely follow-through. A failed read calls for diagnosis and recovery where possible in the same run; consequential gaps in ordinary monitoring can merit a notice even without a saved goal. A missing permission is checked before a protected query, and an unavailable source is never treated as an empty result. Expected and checked resources are recorded separately; a missing calendar, unfinished page or failed read cannot advance the successful checkpoint. Checks consume model calls; tools and subagents can add usage.

Before a notice is sent, the assistant reviews the newest native user/assistant conversation text; a newer message requires reading only that new text and a fresh review. A reviewed notice held for an hour by new messages or an active conversation is released to the remaining gates, so a busy conversation delays notices without starving them. Unsent versions of the same issue can be superseded without rewriting delivery history. Named source items retain their literal title, ID and due/timezone. The installation default no longer caps ordinary notices at one per day; quiet hours, deduplication and explicit user limits still apply. Only a byte-identical untouched old preference template is migrated.

Pending reminders expose what blocks them and their earliest policy window, not a promised delivery time. New evidence can change urgency; genuine urgency bypasses ordinary quiet hours, while snoozes and topic opt-outs remain binding. A routine financial email alone does not establish an emergency. A patrol checks the facts and prepares useful help before deciding to interrupt. Examples include weather affecting a trip, a moved meeting, substantive news on an interest, or an event, exhibition or booking window relevant to a known plan. Location, dates and personal relevance need evidence; routine forecasts and repeated headlines do not merit a message. Nothing worthwhile means silence. Ordinary proactive messages focus on one useful item and do not chase a reply because the user stayed quiet. These are model instructions; judgment depends on the model and available sources.

Conversations and background work share goals, interests and feedback. Accepted work can continue across days and close on verified outcomes; criteria that require user confirmation still require it. Completed, cancelled or rescheduled items are rechecked so stale pending reminders can be retired. Renewing an interest requires new user input, never the assistant's own research; snoozing does not extend its original expiry.

Hourly upkeep and nightly review keep separate progress. Hourly upkeep allocates disjoint durable operation pages to parallel native workers, which read complete scoped evidence and return conclusions. The parent checks those results and advances only contiguous substantively reviewed progress. Children may read the current profile, but cannot change Muse global state; no extra grant service is required. Existing active or unknown worker owners remain recoverable and are never relaunched. Nightly review verifies relevant findings and writes current alignment. Patrol and Feed check their own results without rescanning the full history. An audit backlog does not block verified notices or confirmed alignment updates. Both process their initial user-signal snapshot; 25 messages is a page size, not a work limit. New arrivals wait for the next run, and interrupted work retains its completed progress. Feed uses existing memory and current understanding; its hourly check does not require an article every time. Weekly and monthly jobs deliver reports at the depth their findings need; only the stored summary is capped at 2000 characters. They propose changes without applying them and do not run a separate Skill audit. Existing user-created reviews remain in place.

Bot Chat explains the subject, what happened, why it matters and what has been checked. When a missing detail changes the judgment, it reads the original mail, event or task through available authorized tools before replying. A thin summary is a reason to investigate, not a reason to hand the question back to you. Failed access is reported as a specific gap. You do not need to read the internal delivery or tool log to understand its reply. It owns verified background actions and mistakes, rather than speaking about another assistant’s report. It does not reply “received” to the background task or promise to investigate an already checked result. A question belongs only where your decision is needed; a remembered conversation must have evidence. The shared receiving prompt accompanies the delivered findings and is also used by the conversation hook. This guides the model’s response; it does not guarantee exact wording.

Task progress separates signal handling, operation review, artifacts and notification output. `muse_manage context` or `status` exposes `task_runs` with the current attempt and latest ended outcome of each job. Native Cron success means execution ended; it does not prove these stages finished. Interrupted work retains a partial outcome and saved assignments; completed slots are not repeated. Near the host turn limit, upkeep checkpoints and ends normally rather than launching another wave. Independent page receipts survive concurrent readers, repeated completion never moves progress backward, and evidence references remain available for seven days. Successful Skill/tool-discovery reads are excluded from the audit; failures and real changes remain. These records use the existing state database.

The latest review summaries are available through `muse_manage status`; full outputs stay in native Cron history. The next review can use them to check whether earlier suggestions led to useful changes.

## Files

The root is the active profile's `HERMES_HOME`, usually `~/.hermes`.

```text
$HERMES_HOME/
├── plugins/hermes-muse/             # plugin code and resources
│   ├── skills/companion/
│   │   ├── SKILL.md                # shared procedures
│   │   └── references/             # goals, reminders, memory, Feed, research, governance, communication
│   ├── prompts/                    # the eight prompts listed above
│   └── templates/                  # initial workspace files
├── muse/
│   ├── install.json                # job IDs and owned files
│   ├── install.lock
│   ├── audit.lock                  # Audit assignment lock
│   ├── state.db                    # source checks, cursors, interests, notices, Feed, research, findings
│   ├── AGENTS.md
│   ├── TOOLS.md                    # confirmed connections, devices and limits
│   ├── PROACTIVE_PREFERENCES.md
│   ├── memory/
│   │   ├── YYYY-MM-DD.md
│   │   ├── people/INDEX.md, <person>.md
│   │   └── groups/INDEX.md, <group>.md
│   ├── dreams/
│   │   ├── YYYY-MM-DD.md
│   │   └── alignment/derived/ALIGNMENT_SYNTHESIS.md
│   └── workspace/
│       ├── goals/<slug>/GOAL.md, files/, hidden_files/
│       └── your_files/feed/<id>.md
├── scripts/hermes-muse-*.py         # native Cron entrypoints
├── memories/USER.md, MEMORY.md      # existing native memory, when used
└── cron/                           # scheduling and execution records owned by Hermes
```

The memory, dreams and goal directories borrow Muse's organization. The ownership record, SQLite state, Feed storage and native memory paths are Hermes adaptations. First load adds missing workspace templates; goals, notes and articles are created during use. Reloading does not duplicate the recurring jobs.

Self-review reads native tool calls/results and owned Cron execution records, including persisted child sessions. Hourly upkeep checks new operations and unfinished repairs; nightly review carries verified lessons forward. Only checkpoints, session/execution references and findings are saved in the existing state database. The first pass covers the preceding 24 hours; later passes continue from the saved checkpoint. Missing history stays a coverage gap. Fixes use existing authority, and consequential errors need an actual user-facing correction before closure; there is no automatic rollback engine.

Nightly review can also maintain a short Working lessons section in `muse/AGENTS.md`, merging duplicate methods and updating stale ones while preserving user-written conventions. Personal facts and task logs stay in memory and goal records. Existing installations add the section only when useful; the whole file is not replaced.

Installation does not rewrite Hermes core, SOUL, native USER/MEMORY files, user project AGENTS files or the configured `agent.system_prompt` value. During use, the assistant saves new facts through existing memory tools.

Private/local user inputs retain their first 8,000 characters, truncation flag, turn/session identity and time; associated routes can include chat/user/thread/message IDs. The newest 500 remain; older rows are cleaned on a subsequent input only after both independent hourly and nightly cursors cover them. Unprocessed backlog can exceed 500 and retention time is not fixed. Idempotency journals and oversized tool results (kept in `state.db` so a repeated call replays and long results can be paged) may contain written content or tool output and have no automatic expiry. Native history, research result payloads, archived followup records, goals/memory/Feed and backups have separate retention; see [compatibility and data scope](docs/CATALOG-COMPATIBILITY.md). The plugin collects no telemetry and excludes group chats from personal companion workflows. See [SECURITY.md](SECURITY.md) for data scope.

## Use

**Recommended: use Hermes Muse from the current profile's Bot Chat.** Discuss goals, interests and feedback there. When background work produces something worth bringing up, the bot picks it up:

`Cron prepares a result → delivers to this profile's Bot Chat → the bot reads it → replies to the user in chat`

Receiving the result runs an assistant turn on that profile's model. Hermes can create the Bot Chat on first delivery if it does not exist; its native queue handles a busy chat. Feed writing and routine upkeep stay silent. Selected reminders and scheduled weekly/monthly reports enter this delivery flow.

The official installer displays the plugin's after-install notes, but has no plugin-defined channel/session picker. This version uses Bot Chat by default and does not require an external channel such as Telegram.

Talk about plans, interests and feedback normally. Patrols do not require you to create a goal first. For example:

```text
Create a bicycle-purchase goal, with a budget of $1,000 and a decision by month-end.
Check for a reply to this message until Friday.
I’m visiting Hangzhou this weekend. Let me know if the weather changes enough to affect the trip.
I follow space exploration. Important developments are welcome; I don’t need a daily news digest.
This reminder is done.
Stop reminders about this topic.
Show my calendar for the next 30 days, including preparation I should start early.
Show this month’s calendar with its original all-day dates.
List my current goals, interests and pending reminders.
Search my Feed for urban gardening articles.
```

The model identifies goals/interests and calls the state tool to record them. Goals need a clear user plan or commitment, without requiring the words “create a goal.” Temporary interests expire after 14 days by default and do not automatically create permanent monitoring. New user input can renew an interest; the assistant’s own research cannot. Delivery or model failures retain their state for inspection; there is no automatic resend to another channel. Ask what was checked, what failed or what remains open; the assistant can use `muse_manage status` to inspect the records.

## Remove

```sh
hermes plugins remove hermes-muse
```

Then ask Hermes to clean the associated tasks:

> Read this profile's muse/install.json. Pause and remove its recorded Cron jobs, check anything still running, and remove the recorded scripts/hermes-muse-* entrypoints. Also find user-managed Cron reports that load hermes-muse:companion and pause/remove them, or convert them to standalone instructions if I ask to keep them. Keep goals, articles, notes and memories, and report any incomplete cleanup.

Native remove does not guarantee cleanup of plugin-created Cron jobs. Leftover entrypoints go silent after deletion or disabling; already running work still needs checking. Reinstallation retains data, and ordinary reload does not resume tasks the user paused.

## Development and verification

```sh
python -m unittest discover -s tests -v
node --test tests/page_markdown.test.mjs
# In a Hermes environment:
python tests/native_smoke.py
hermes plugins validate . --json
```

Tests use temporary profiles without real model calls or messaging channels. The [acceptance guide](docs/ACCEPTANCE.md) lists checks for an actual installation.

The [official catalog application](https://github.com/NousResearch/hermes-agent/pull/134976) is pending review. Install from the repository address above in the meantime.

MIT licensed.

## Conversation preview and scheduling policy

Recent conversation context uses bounded previews with complete revision-checked paging; task-notice approval needs each session's newest 24,000 characters served, not the whole day's history. See the [conversation procedure](skills/companion/references/conversations.md). Cron watch creation respects `cron.allow_agent_scheduling`; local goal registration creates no job. New watch prompt/stop fields each allow 4,000 characters without truncation. New repeating watches must provably remain at least 30 minutes apart; one-off schedules are exempt. Existing jobs and user schedule edits are preserved.


## Scoped tools and plugin pages

**Platform limitation:** the secure content/lock implementation is POSIX-specific and breaks the Windows support of 0.1.x. Windows is not supported for now (POSIX file locks and descriptor-relative file access) and CI does not cover it; no unsafe fallback is provided. Restoring Windows requires a secure native-handle implementation, not disabling symlink checks.

Muse includes Dashboard and Desktop pages for the complete Feed, topics, ideas and goals. APIs are authenticated by Hermes and check the requested profile on every GET. Browsing creates no read state or model work. Desktop changes start as a draft in a selected originating chat; the user sends it through normal tool authorization. Install the same package on the Desktop device to obtain its entry; a remote backend install alone does not install the client entry. The pages follow the host theme, render Feed and goal text as safe Markdown (no raw HTML), list open goals first with closed ones folded, and explain an empty Ideas tab (Ideas appear only when the nightly review or a conversation adds one). The goals API accepts `status=open|closed`.

Use `muse_manage` for every Muse business object, locally or from a container. No new Muse bind mount is needed. `skill_view` provides instructions; it does not perform storage. See [all 40 actions](docs/INTERFACE.md) and [content usage](skills/companion/references/content.md). Goals use an optional integer expected_revision. For other managed mutations, read the object revision and supply expected_revision and a stable request_id. Conflict means reread/merge. Unknown outcome means inspect the original operation, never repeat it with a new key.

Before planned disable/removal, call installation_prepare with the original user signal, current installation revision and request key while the plugin remains enabled. The user signal must be a whole-message imperative naming Muse and matching the operation, such as “Please disable Muse now.” / “请停用Muse插件” or “Please uninstall Muse now.” / “请卸载Muse插件”. Questions, quotes, unrelated deletion and deferred/conditional requests are refused. It pauses only verified owned jobs and returns requires_host_action; then use Hermes native disable/remove. Direct disable makes remaining launchers harmless but cannot promise automatic task cleanup. Data and user-paused jobs remain preserved.

Workers use public native delegation and respect delegation.* routing/reasoning/concurrency. New repeating watches are at least 30 minutes; ambiguous cron patterns are refused, once is exempt, existing schedules remain. Cron Feed-brief edits wait for the next existing tick.

Memory acknowledgements follow actual receipts: saved, waiting approval, submitted but unconfirmed, failed, unchanged or unknown. The plugin stores only minimal correlation references. Approval completion, provider durability and automatic background-event merging remain host/provider contract limits; no core patches or new daemons are installed.

## Unified Dashboard host

Install and enable the full Muse package in the default Hermes profile using Hermes plugin management. The Dashboard discovers this package and serves its authenticated page/API. The page initially lists registered profiles only; explicitly select one to view its Feed, Ideas and Goals. Browsing is read-only for every profile: the page and its API cannot install, enable, disable or remove Muse in any profile, including other profiles on this host.

To use Muse in another registered profile, install and enable it in that profile with Hermes plugin management (for example `hermes -p <profile> plugins install …`); the page then lists it as enabled and can read it. No cross-profile administration exists in the page, its API, muse_manage or native children.

Profile paths come from Hermes root/home and registry APIs, including custom HERMES_HOME. Read requests use explicit Views without changing process environment or initializing stores. Desktop retains current-profile reads and chat drafts.

With terminal.backend=docker, only terminal execution enters Docker. Muse tools and namespaced companion skills remain dispatched by Hermes on the host, against the same active profile; no Muse mounts, copies or Docker-specific path branch is needed. A whole Hermes instance running in another container or remote HOME is a separate installation: equal profile names do not share state, and this page does not manage remote instances.

## Bounded maintenance context

context/status now return a section directory instead of an unbounded aggregate. Collection pages share content_read cursors and revisions; large metadata is explicitly paged through metadata_ref. Maintenance signal windows store references and served ranges in existing records: new arrivals after through wait for the next window, edits/backdated arrivals invalidate it, and checkpoints reject unread signals including timestamp ties. See companion references/context.md for the exact flow. Old flat context consumers must migrate in the same release.

Conversation descriptors discover current revisions and first missing offsets without marking a hidden preview read. Exact unchanged prefixes keep their coverage on append; new text inside the newest 24,000 characters must be read before notification review. Quiet hours and transport confirmation are unchanged. Due-goal pages use live ordered goal IDs; continue with next_cursor, and start a new pass to include newly inserted earlier IDs.

Feed body corrections already exist in feed_update(title/content/sources); this release documents and natively verifies the authorized CAS/replay path rather than introducing another writer. Finding creation uses expected_revision=absent and request_id. Oversized successful semantic mutations return a read reference, preserving their durable replay result instead of reporting a post-commit size error. The 256 KiB ceiling remains a transport/performance budget, not a model context or permission boundary. No model/provider changes, daemon, Cron or additional database.

Notification preparation held by new conversation text returns the exact conversation_read calls for that text without marking hidden previews as served. Read the actual body pages before relevance review. Large committed preferences and installation results use singleton `content_ref` receipts; delivery payloads that cannot fit are rejected before reserving dispatch/budget (the candidate may remain pending).

Semantic mutation receipts are bounded after adding revision/recovery fields. Normal completion, pending recovery and replay use the same final-envelope serializer; the journal stores that exact bounded receipt. Older oversized successful receipts are converted to pageable success references on replay without repeating the mutation.

### Final tool response and recovery

Every action validates the whole request (512 KiB, nesting and control-token bounds) before journal, track, bind or dispatch. Oversized content/question/watch input is rejected before work. `window` belongs only to memory-upkeep/nightly-review. The final 256 KiB envelope includes revision/recovery fields and errors.

Committed large results use `result_is_reference/content_ref`; large native errors remain `ok:false` with a bounded reason and `error_ref`. Follow these refs with `content_read`; retain revision and concatenate body pages before interpreting the JSON. `kind=tool_result` is an immutable exact tool envelope in existing profile records, accessible only by its originating private session and ID (no collection or Dashboard exposure). It does not authorize a side effect, certify served conversation evidence, or claim native task completion. Ordinary object references still use their existing domain access. Pure reads do not create receipt records; invalid input is rejected with a bounded explanation.

The following actions additionally accept an optional `request_id` (1..128 characters): delegate, research_start, research_status, watch_stop, operations_read, operations_batch, operations_complete, operations_commit, review_complete, run_complete, notification_prepare, notification_queue, notification_handoff. Use it for a logical state-changing call; identical arguments/key return its exact completed receipt. A key with changed arguments/origin is rejected. A pending/interrupted call returns outcome_unknown without repeating work; inspect native evidence or its existing checkpoint, never create a new key to redispatch unknown execution. This reuses mutation_request, releases the lock during native work, and does not replace CAS or existing own content/install journals. Calls without a key retain their existing recovery contract and must not be blindly retried.

`research_start` large results reference the saved research object; `research_status` may reference the exact observed envelope. Both can be fully read via content_read pages without another dispatch. An allocation receipt (operations_read/batch) is not substantive review: read its refs and actual evidence before committing a checkpoint.

Scheduled source coverage follows explicit user requirements and the profile's declared responsibilities. The optional free-text `Coverage scope` section in PROACTIVE_PREFERENCES.md refines sources/exclusions; it adds no schema or runtime policy branch. A general assistant without exclusions retains full 30-day calendar/pagination/advance preparation, mail, reminders and useful travel coverage even without goals. Specialist roles do not probe unrelated personal sources; unavailable or failing in-scope sources retain honest gaps/recovery. See companion [Coverage scope](skills/companion/references/proactivity.md#coverage-scope). Native permissions and existing delivery/checkpoint rules remain authoritative. Reload refreshes shipped Cron prompts while preserving the profile's existing preference prose, task IDs, schedules, pauses and targets. Model compliance needs post-deployment observation; static/isolated fixtures do not establish it.


## Upgrading goals to 0.3.0

Installation archives old goal files and followup records under
`muse/archive/followup-0.2.x/` and maps completed→done, cancelled→cancelled,
active→active, retaining progress and owner. Pure views never initialize or migrate.
For offline rehearsal/rollback use `python -m hermes_muse.migration --home <home>`
(or `--rollback`). Back up first and stop writers; rollback refuses new goal edits.
A completed rollback retains its archive; the next upgrade starts a fresh archive and preserves the prior cycle under `followup-0.2.x-<id>`.
No data is erased and no unknown external effect is resent. Windows remains unsupported.
