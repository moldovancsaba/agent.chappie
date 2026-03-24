# Handover: 2026-03-24 Task Learning Loop Priority

## Why this handover exists

The app is now much more stable and usable than it was earlier in the project:

- the worker is private and supervised
- the app shell is credible
- the knowledge surface is sharper
- tasks are more evidence-driven
- live delete/hold controls exist across task cards, knowledge cards, source cards, and draft segments

That means the next important work is no longer basic rendering, shell design, or surface cleanup.

The next important work is making the system learn from operator correction in a way that feels immediate and useful.

## Current truth in plain English

Today, the system can already do some of the mechanics:

- You can mark a task as done.
- You can adjust a task.
- You can delete a task.
- You can delete a task and teach the system what to avoid.
- You can hold a task for later.
- The checklist can regenerate.
- Feedback is stored locally.

But the product is still not fully behaving like the intended learning action engine.

The missing feeling is:

- "I told the system this task was wrong, and it immediately got smarter."

That is the product gap to close next.

## The highest-priority unresolved work

### 1. Decline and replace for task cards

What it should mean:

- If You reject a task card, We should immediately produce a replacement.
- The replacement should not just be the same task with slightly different words.
- The checklist should still show exactly 3 tasks.

Why it matters:

- Right now, rejection is recorded, but the experience is still not consistently strong enough to feel like the system is reacting intelligently in the moment.

What good looks like:

- You reject task 2.
- Task 2 disappears.
- A new task appears in its place.
- The new task uses a different angle, channel, or mechanism.

### 2. Delete and teach for task cards

What it should mean:

- If You delete a task and explain why, We should both remove it now and learn from that explanation later.

Examples:

- "too vague"
- "wrong competitor"
- "wrong page"
- "not for this week"
- "overlaps with task 1"

Why it matters:

- Silent delete is useful for cleanup.
- Delete-and-teach is useful for compounding product quality.
- This is how the system stops repeating the same class of bad task.

What good looks like:

- You click `Delete and teach`.
- You write: "avoid homepage copy tasks when the pricing page is the real battleground."
- The next regenerated task does not come back as another homepage-copy task.

### 3. Comment-driven regeneration

What it should mean:

- Comments should influence the next generated task even if You do not fully rewrite the task yourself.

Why it matters:

- In real usage, operators often know what is wrong before they know the perfect rewrite.
- Comments are a high-signal teaching input.

Examples of useful comments:

- "too broad"
- "we need a concrete asset, not a messaging idea"
- "wrong audience"
- "this is a trust move, not a pricing move"
- "this belongs in onboarding email, not homepage hero"

What good looks like:

- You comment on a weak task.
- The regenerated task changes channel, specificity, or move type because of that comment.

### 4. Persistent local task feedback

What it should mean:

- Feedback must live in the local Mac mini brain, not just in transient UI state.
- The worker should use those stored signals later.

Why it matters:

- Without persistence, the system only improves per commit.
- With persistence, it can improve per project and per user interaction.

Current direction:

- local `task_feedback`
- local `replacement_history`
- local `generation_memory`

Still needed:

- stronger use of those stores during ranking, phrasing, and replacement generation

### 5. Exactly 3 tasks after replacement

What it should mean:

- If a task is rejected, deleted, or held, the list should still remain at exactly 3 visible tasks unless the source itself was explicitly removed and the evidence base changed.

Why it matters:

- The product promise is not just "recommend something."
- The product promise is "keep the operator supplied with 3 current moves."

What good looks like:

- one task disappears
- one replacement appears
- the list stays stable and useful

## The real product goal behind all of this

The goal is not only to let the user click more buttons.

The goal is to make Agent.Chappie feel like this:

- it proposes 3 moves
- You correct it
- it learns immediately
- it proposes better moves
- that improvement compounds with use

That is the difference between:

- a recommendation interface
- and a learning action system

## What not to spend time on next

Do not spend the next phase mainly on:

- shell polish
- more cosmetic spacing tweaks
- more badge refinements
- more card decoration
- dashboard-like additions

Those may still happen later, but they are not the main blocker now.

## Suggested next implementation order

1. Strengthen immediate replacement after reject/delete/hold
2. Make comments change regenerated output more aggressively
3. Make edited tasks teach preferred patterns more strongly
4. Add clear regression tests for all three feedback paths
5. Re-run pressure testing with feedback scenarios, not just source-ingestion scenarios

## Minimum proof the next owner should return

At minimum, the next pass should return:

1. one case where a rejected task is replaced immediately
2. one case where `Delete and teach` prevents a similar task from reappearing
3. one case where a comment changes the regenerated task
4. one case where an edited task becomes a preferred future pattern
5. proof that the list stays at exactly 3 tasks after replacement

## Current version boundary

At the moment of this handover, the task and intelligence surfaces are materially improved, but the learning loop is still the most important unfinished product behavior.

That is the next milestone.
