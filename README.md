# Goal Tracker

Goal Tracker is a personal goal-tracking web app built for goals that do not all look the same.

Some goals are simple daily habits. Some are target numbers. Some are one-time tasks. Some are "stay under a limit except on specific days." This project is meant to handle all of those in one system without feeling rigid or generic.

## What Makes It Interesting

Instead of treating every goal like the same checkbox list, Goal Tracker is designed to support very different kinds of progress:

- daily habits like `30 minutes of cardio every day`
- target goals like `240 lbs by April 30`
- performance goals like `row 2km in under 12 minutes`
- restraint goals like `no drinking until April 30, except on specific dates`
- one-off tasks with subtasks

The bigger idea is that the app should not just store updates. It should make progress visible and motivating.

## What The App Aims To Show

- clear status for each goal
- history over time, not just the latest number
- dashboards made from reusable widgets
- reminders when something important has not been logged
- future forecasting where it actually helps
- shareable visual widgets for showing progress outside the app

## Example Experience

Imagine using one app to track all of these at once:

- your weight, with multiple weigh-ins in one day
- your cardio habit, tracked day by day until a deadline
- your best 2km row attempts over time
- a no-drinking streak that correctly skips approved exception dates

That is the kind of flexibility this project is being built around.

## Project Status

The project is in the foundation stage right now.

What already exists:

- a working web app shell
- first-account bootstrap, invited sign-up, and sign-in flow
- a signed-in app shell with session restoration
- admin-managed invitation codes for creating additional accounts
- optional example-data account signup seeded with starter metrics, realistic history, goals, and a dashboard that exercises multiple widget types, with revision-based upgrades for existing example accounts at server startup and during auth traffic
- reusable metrics with quick number/date updates
- metric archiving, with archived metrics hidden by default
- goal archiving, with archived goals hidden by default
- goal creation and editing backed by existing or newly created metrics, including date-based compliance goals with exception dates and success thresholds
- saved dashboards with reusable metric and goal widgets, including target-date goal charts with selectable forecast algorithms plus completion, success, and risk widgets, plus separate mobile and desktop widget layouts
- a default dashboard per user, plus an edit mode for arranging widgets
- browser-local timestamp rendering with profile-configured day-boundary timezone semantics
- a backend API foundation
- a landing page that successfully calls the API and renders application status
- architecture documents covering the long-term product design

What comes next:

 - reminders, richer forecast explanations, and richer progress views
- sharing dashboards and widgets outside the app

## Why This Project Exists

A lot of goal apps are either too simple to be useful or so specialized that they only work for one kind of tracking. The goal here is to build something that can handle real life:

- habits
- health metrics
- performance milestones
- abstinence rules
- procrastinated tasks

and still feel like one coherent product.

## For Builders

The public-facing overview stays here in the README.

Technical implementation details, architecture notes, and developer workflow live in:

- [`docs/architecture`](./docs/architecture/README.md)
- [`docs/development.md`](./docs/development.md)
