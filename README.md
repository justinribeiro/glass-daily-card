Send a card to Google Glass daily via App Engine + Cron
================

This sample is an App Engine application that sends a daily card to Google Glass. It uses Google+ Sign In to handle authentication and then uses App Engine's cron to send a card to uses at the defined time.

### Prerequisites

1. Create a new project in the [Google Developers Console](https://console.developers.google.com),
2. Enable Mirror API and Google+ API. Note, this differs from the other Glass quickstarts (they make reference to the deprecated profile.info scope and don't require Google+).
3. Create a new client id for web application under APIs & auth > Credentials. Make sure to add your redirect uri as http://localhost:8080/oauth2callback for local testing and https://SOMENAME.appspot.com/oauth2callback for deployment.

### Setup

1. Clone this repo
```
git clone https://github.com/justinribeiro/glass-daily-card.git
```

2. Install the requirements so that our project will run (Flask, kvsession, httplib2, et cetera)
```
pip install -r requirements.txt -t lib

3. Replace client_secrets.json with the credentials you created in step 3 of the prerequisites (use "Download JSON" button).
4. Replace the content for the google-signin-clientid meta tag in templates/base.html with your web application client id. Maybe visit the link in the comment above that line and learn more about page level configuration for Google+ Sign In.
5. Run the application via
```
dev_appserver.py .
```
6. Browse to http://localhost:8080/ to see the application running.

### Scheduling cards to send

Because this is a bare bones sample application, it has no admin interface. Instead, we rely on the Datastore Viewer to manage the  CronCards data. To get started:

1. Create a CronCard. The model, while defined in the application (see models.py), doesn't exist in the datastore because we have inserted any data. To do so, visit http://localhost:8080/samplesforcron which will insert a single CronCard into our datastore with the date set to today.
2. Edit or Adding CronCards. By navigating to the local admin panel (http://localhost:8000/) we can view, edit and add to the CronCards data store as needed. This would be under the "Cloud Datastore" in production App Engine.

### Running the cron job

1. The cron job is scheduled via cron.yaml. To understand more about how cron works on App Engine, I highly recommend the [documentation](https://developers.google.com/appengine/docs/python/config/cron).
2. In development, the cron job will not run at the defined time. You need to kick the job off manually to test via the local admin console http://localhost:8000/

### General questions
Some general questions that are highly likely to come up.

#### Why doesn't it send HTML?
Because I specifically set the body of the timeline card to text. You can change it html if you like.

#### Why can't I define custom menu options?
It's a sample application to get you started, you can add as many menu options as you like if you want to expand the code. View the timelinecard_body in dailyjob() in main.py to see how the menu options are setup.