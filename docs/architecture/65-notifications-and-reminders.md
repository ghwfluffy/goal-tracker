# Notifications And Reminders

## Purpose

The system should remind users when expected actions are still outstanding.

Primary examples:

- mark a daily goal as completed
- enter a metric value such as `weight`
- update a weekly task before its deadline window closes

## Design Goals

- reminders should be useful, not noisy
- reminder timing should respect user timezone
- reminder state should be durable and auditable
- reminder rules should work for both goals and standalone metrics
- notification delivery should start simple and be extensible later

## Core Concepts

### Reminder Source

A reminder may originate from:

- a goal
- a metric
- a system event

For this product, goals and metrics are the important sources.

### Reminder Rule

A reminder rule describes when a reminder should be generated.

Examples:

- if a daily goal is still unconfirmed by 8:00 PM local time
- if a metric expected each morning has not been entered by 10:00 AM local time
- if a weekly checklist item is still incomplete on the last day of the week

### Notification Record

A notification record captures the generated reminder or system message.

Useful fields will likely include:

- user
- source type and source identifier
- notification type
- generated time
- scheduled delivery time
- delivery status
- read or dismissed timestamps
- expiration timestamp when relevant

## Reminder Scheduling

Reminder generation should be driven by deterministic rules.

Important timing inputs:

- user timezone
- goal or metric schedule
- goal start date
- date-only end dates resolved as end-of-day in the goal timezone
- grace window
- quiet hours if the user configures them later

## Start-Date Interaction

Goal start dates matter to reminders.

Expected behavior:

- reminders for a goal do not begin before the goal start date
- once the goal is active, reminder generation follows the goal cadence and reminder settings
- historical metric data may exist before the goal start date, but reminder responsibility begins at the goal start date
- exception dates should suppress reminder generation for excluded scheduled days

## Notification Channels

Initial design direction:

- in-app notifications should be first-class
- the model should allow later expansion to email or other channels if desired

The first implementation does not need to commit to mobile push support.

## Notification States

Likely states:

- pending
- delivered
- read
- dismissed
- expired
- failed

These states should be enough to reason about reminder behavior and future retries if needed.

## Noise Control

The system should avoid becoming spammy.

Current design direction:

- reminder rules should be explicit, not implicit magic
- repeated reminders should be constrained
- reminders should stop once the required action is completed
- users should eventually be able to manage reminder preferences

## Auditability

Meaningful reminder generation and delivery actions should be auditable, especially if background jobs are responsible for creating or expiring notifications.

## Open Design Items

These details still need concrete approval later:

- exact reminder-rule schema
- whether reminders attach directly to goals and metrics or through a shared rule table
- first-phase channel support beyond in-app
- quiet-hours and snooze behavior
