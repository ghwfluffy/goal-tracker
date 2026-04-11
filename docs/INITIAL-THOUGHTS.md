# Goal Tracker Project

im looking to build a web app that i can use to track my goals.

i want to be able to define SMART goals and have some mechanism for tracking progress through manual updates.

i want it to be very customizeable to any type of goal that i want to do

# example goals:

## do 30 minutes of cardio a day

would require me to check some box each day (or whenever i get around to it on a future day) that tracks i did it. and maybe a nice status display for the goal would look like a calendar with every day check or X depending on if it confirmed i did it or confirmed i didnt do it.

## reach 100 lbs weight

or another goal might be a numeric tracked like weight. so i would update it periodically and it could track it and display in a graph and even with a progress bar till complete.

## complete a task

sometimes i have to do something one off and i just procrastinate forever. maybe there can be a way to make a goal that is simply to complete that task (and it can even have sub-tasks i can check off towards the final goal).

## dont watch tv on non-designated days

ability to track that only on pre-designated days (special occassions) tv watching did not occur. maybe something like this even works as a rolling window. so it shows progress for the last 90 days, and what percentage on goal i am. if i have followed the allotment for 9 of the last 10 days then my score is 90% until that one day falls out the other end of the rolling window

## others

in the design / planning phase i welcome suggestions about other possibilities i could support

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

## Tech Stack

I want to have a docker compose project in the main directory. i want a ./api dir that is a python application that handles the REST API. and a ./web dir with the vue SPA that handles the front-end / devserver.

### Python back-end

- Ubuntu noble container
- Python3
    - fully type hinted
    - ./api/lint.sh that runs mypy, flake8, and ruff on the files
- fastapi runs REST APIs
- pydantic used for API validation
- sqlalchemy and alembric used for database schema and ORM
- enrypoint runs uvicorn with reload flag for hot reloading
- docker compose mounts in source files for hot reloading to work

### Database

- PostgreSQL 18 container
- read credentials from .env file to compose file
- ./db/init.sql will provision just user
- separate db-backup compose service that periodically backs up to a mounted directory in ./backups using the BACKUP_GID/UID configured in .env

### Web front-end

- Vue 3 + Vite
- PrimeVue
- Pinia
- Vue Router
- Typescript
- Compose runs devserver and exposes as port 8081 to host
- ./web/build.sh will build and validate the typescript

### Ingress

- Nginx
- Sits infront of uvicorn to handle TLS and serve prod web distributables
- Has rate limitting to help prevent DDOS
- config in ./nginx
- Separate container that runs first that gets ACME PKI and periodically updates them
    - hostname from .env

### AGENTS.md

The base AGENTS.md should remain concise but contain everything the agent must always know to do. the agent knows to run python linter and typescript build whenever making changes.

#### Documentation

./docs

The agent will know to document everything always. it will always document design decisions, or things useful for debug, reasoning stuff exists, etc. anything that would be useful for a future agent to know that makes more sense to document than to lookup in the code. the agent should know when it is corrected it should document the design decision or coding style change it was corrected about.

### README.md

The README should be maintained and look nice for public facing README on github. it should contain a good general explanation of the project, its feature set, the tech stack, and basic information on how to get the project running. the README should be maintained when a high level feature is added. The README should reference the docs for more info.

## Development details

### Back-end

Prefer these packages:
apscheduler
cryptography
fastapi
flake8
mypy
pdfplumber
pillow
psycopg2-binary
pydantic
python-multipart
pyyaml
ruff
sqlalchemy
types-PyYAML
uvicorn

### Front-End

- Try to never "re-invent the wheel". Use components provided by the front-end libraries
- Be consistent. If a button or table is done in some specific way it should be turned into a component and used everywhere

### Database Schema

- entirely created and managed by the python layer
- every change to db schema updates a "dbversion" tracker in a configuration table in the db
- ability to make a user account as "example data" which will prefill in example data for every new feature for easy testing
    - able to check when registering account

### Auth

- The system should support multiple accounts that login with username and password
- The first account to be created is marked as administrator
    - user registration requires a registration code that is CRUD by the admin account, except first account
- The cookie contains an signed payload with state information and is good for an hour
- Session signing key:
  - from `SESSION_KEY` env var (preferred)
  - generated at startup if missing
  - warning is logged when using default `changeme`
- administrator accounts have ability to CRUD user accounts
- users can change their password, set a profile picture, and delete themselves
- all user input should be strictly validated and sanitized to be safe before going into the database.
    - images uploaded by user should be resized to minimal size and saved as newly rendered PNGs

### Testing

Some sort of unit test and API testing framework should be used for both the front-end and the back-end code, and it should be maintained extended religiously when new features and fixes are added. it should be easily run as part of the agent's loop, and the agent should know to run it when making any changes.
