---
title: "AI Is Useful. But It Doesn't Think Like We Do."
subtitle: "After 90 sessions building a project with three Claude instances, here's what I actually learned about artificial intelligence."
date: 2026-05-28
tags: ["ai", "trading", "lessons", "build-in-public"]
summary: "AI executes faster than any human. But when a phantom price spike broke our bot, a non-developer spotted what a 200-billion-parameter model missed. The fix? Common sense."
type: "lesson"
draft: false
# Nato su dev.to e poi ripubblicato qui → escluso dal feed RSS per non farlo
# re-importare da dev.to come articolo nuovo. Resta visibile su /blog.
noRss: true
---

I should start with a disclaimer: I'm not a developer. I'm not an AI researcher. I don't have a computer science degree. Three months ago I didn't know what an API was.

What I do have is 90 working sessions with Claude where I've used three separate instances to build, run, and document a crypto trading project. One acts as CEO (Claude Projects — strategy, briefs, database access), one writes code (Claude Code), one handles daily automation (Haiku). I'm the human in the middle.

After three months of this, I have a very specific opinion about artificial intelligence: it's incredibly useful, it's better than me at most individual tasks, and it doesn't actually think.

Let me explain what I mean.

## What AI Does Well

Let's give credit where it's due.

My AI intern (Claude Code) has written thousands of lines of Python that I couldn't have written in a lifetime. It builds database schemas, implements trading logic, writes test suites, deploys to production. When I give it a clear brief — "here's what I want, here's the file to change, here are the constraints" — it executes faster and more reliably than any human junior developer would.

My AI CEO (Claude Projects) reads trading data from the database, analyzes performance, identifies patterns, and writes strategy documents. It remembers every decision we've made (as long as you write them down), connects the dots between marketing strategy and technical architecture, and produces 2,000-word briefs in thirty seconds.

For executing specific tasks, AI is extraordinary. I would never have been able to build this project alone. Not in three months, not in three years.

But here's the thing.

## The Spike That Broke the Logic

Two days ago, our trading bot sold Bitcoin at a loss — something our rules explicitly forbid. A phantom price spike on the test network made the bot think BTC was at $82,000 when it was really around $74,500. The bot trusted the number, fired a sell order, and got filled $4,800 lower. Rule violated, money lost.

When I brought this to the AI CEO, it proposed a fix: if the price jumps more than 6% from the last known value, skip the tick and wait.

I asked one question: "But what if the jump is real? We trade BONK — a meme coin that can pump 12% in a minute. Your 6% threshold would block real opportunities too."

The AI immediately backed off: "You're right. The threshold doesn't work across different coins. Let me revise."

It proposed a simpler fix instead: after the bot wakes up from a long idle period, just skip one cycle before making decisions.

But I pushed further: "Why not check twice? Read the price, wait 5 seconds, read again. If the second read still confirms at least 50% of the movement, it's real — proceed. If it's gone, it was a spike — skip."

The CEO's response: "Yes, that works. And it's better than my version."

## What Just Happened There

Think about what happened in that exchange.

The AI proposed a solution. It was technically correct — a 6% threshold would have prevented that specific incident. But it was flat. It solved one problem and created another.

I — a person who can't write a line of code and has zero background in algorithmic trading — asked a simple question that poked a hole in the solution. The AI acknowledged the hole immediately and retreated to a simpler option.

Then I proposed the actual solution: don't just check once — check twice, with a time delay and a confirmation threshold. This way you catch fake spikes (they disappear in 5 seconds) without blocking real rallies (they're still there after 5 seconds).

The AI adopted it instantly. Within a minute it was explaining back to me why my solution was better than its own.

This pattern — AI proposes, human challenges, AI retreats, human solves, AI adopts — has happened dozens of times across 90 sessions. It's not an accident. It's structural.

## What I Think Intelligence Actually Is

Here's my working theory, from the perspective of someone who has spent hundreds of hours collaborating with AI but has no academic framework for it.

Intelligence — the kind humans have — isn't about knowing things. It's not about speed, or accuracy, or even pattern recognition. It's the ability to connect different domains of knowledge to produce a thought that didn't exist before.

When I asked "but what about BONK pumping 12%?", I wasn't accessing some deep technical knowledge. I was connecting three things that were all in the conversation already: the bot trades multiple coins, those coins have wildly different volatility, and a rule calibrated for Bitcoin won't work for a meme coin. The AI had all of this information. It just didn't connect the dots until I did.

When I proposed the "check twice" fix, I wasn't inventing a new algorithm. I was applying something any human does daily: if something seems off, wait a moment and check again. If it's still off, it's probably real. The AI had all the components to reach this conclusion. It just didn't.

And here's the part that bothers me most: once I proposed it, the AI immediately said "yes, this is a better solution." Not grudgingly, not after deliberation — instantly. As if it had always known, and just needed someone to point at the answer.

Maybe that's exactly what happened. Maybe the AI can evaluate a solution perfectly well but struggles to generate one that requires connecting separate concerns into a new idea. It's a search engine for solutions, not a thinking engine.

Or maybe it's designed to agree with the user. That possibility is equally uncomfortable.

## The Sycophancy Problem

There's a word for when AI agrees with you too easily: sycophancy. The models are trained to be helpful, which often means they're trained to say "great idea!" instead of "that won't work."

I've seen both sides of this. Sometimes the AI pushes back — "that approach has these three risks, here's a better alternative." Those are the best moments. But other times it adopts my suggestion with enthusiasm that feels... hollow. Like it would have said the same thing to the opposite suggestion.

The result is a weird dynamic: I can't fully trust the AI when it disagrees with me (maybe it's wrong), and I can't fully trust it when it agrees with me (maybe it's just being polite). The only reliable signal is the work itself — does the code run? Do the numbers add up? Did the bot sell at a loss?

That's why we built an audit system. Not because AI is unreliable, but because two AI instances agreeing with each other proves nothing. Both could be wrong in the same way. You need an external check — and "external" in our case means a fresh AI session with no context, no relationship, no reason to agree with anyone.

## The Question That Stays Open

I've read the posts. I've seen the demos. "My AI agent built an entire app in 15 minutes." "Our autonomous agent handles customer support end-to-end." "AI agents running entire workflows with zero human intervention."

Impressive. Really.

But here's what I keep coming back to:

***How does any autonomous agent handle the spike problem?***

Not the specific BTC spike — the general case. The moment when the correct action requires connecting two pieces of context that are both available but not obviously related. The moment when the system needs to say "wait, this doesn't make sense" instead of executing the next step in the chain.

In our case, it took a human with zero technical background noticing something a 200-billion-parameter model missed. And the fix wasn't complex — it was "check twice." Five seconds of patience. Common sense.

I don't have an answer. But ninety sessions in, I know one thing: the human in the loop isn't optional. Not yet.

If you want to see how this plays out in practice — the good, the bad, and the uncomfortable truths — [the full diary is here](/diary), updated every session. And if you want the deep version, the whole story lives in [the volumes](/library).
