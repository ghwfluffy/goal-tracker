# Goal Tracker Project

im looking to build a web app that i can use to track my goals.

i want to be able to define SMART goals and have some mechanism for tracking progress through manual updates.

# example goals:

## do 30 minutes of cardio a day

would require me to check some box each day (or whenever i get around to it on a future day) that tracks i did it. and maybe a nice status display for the goal would look like a calendar with every day check or X depending on if it confirmed i did it or confirmed i didnt do it.

## reach 100 lbs weight

or another goal might be a numeric tracked like weight. so i would update it periodically and it could track it and display in a graph and even with a progress bar till complete.

# Status / Progression Display

some goal types might have an end date like `do 30 minutes of cardio a day every day this month` has an end date progress can be measured off, or maybe `hit this weight by this date` has two kinds of progress, there's the percent progress from my starting measurement to the goal, and also the starting time to the end goal time. this can be used to provide feedback on if im currently at risk of not meeting my goal

## Projection / Forecast

if there is no end date, or even if there is, there can also be a forecast algorithm that takes the previous data inputs and uses them to predict the upcoming values to predict when a goal will be met or what the progress will look like.

### Algorithms

inside of `./different-project_weightloss-goal-graph/` is an old project that helped a lot in weightloss tracking and kept me inspired to try to stay on track with the projected weight. the algorithm used for the forecast changed. originally it was simple: calculate the slope of start to last measurement, and then calculate the end date based on how long it would take to get from there to the desired weight. and then it just drew a simple line from start -> last measurement -> now (projected data based on now time) -> projected final. and eventually when we started reaching the end the algorithm became more detailed, projecting each day-over-day change by weekday using historical day-over-day change weighted with more recent weeks counting as higher weight. i think in the new goal we will want to support multiple forecast algorithms.

### Countdowns

Also inside of `./different-project_weightloss-goal-graph/` project i added a feature where there was a sort of countdown at the bottom. it would icons remaining for number of days, weeks, training sessions (Mon, Tue, Thur, Sat). That was a nice feature to help motivate near the end

## Dashboards / Widgets

there should be some way i can create widgets that display the graphs/progress/forecast/history/etc and be able to view them on a dashboard. maybe i could have multiple dashboards like: health, finances, work, personal development, etc.

### Linkable

i really enjoyed (and probably drove my coworkers nuts with) linking the weightloss-goal-graph into chat and it would render a png of the progress and embed it into the chat without having to be clicked. that should definitely be possible for each widget. some easy button that is clickable that copies to clipboard and auto-appends a cache breaking unused argument on the end like `?t=1775916807` so the chat server doesnt try to re-use the previously cached rendered png.
