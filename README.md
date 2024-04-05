# Quickstart

Here is quick description of the structure of the Flask app for accessing withings' developer API through Oauth 2.0. The full documentation
of the API is [here](https://developer.withings.com/)

It has been tested on pythonanywhere and below are instructions for setting up your own instance.

## Setup pythonanywhere Flask server

1. Log in or create a free account at pythonanywhere (https://www.pythonanywhere.com/)
2. Click on "Web" tab and "Add a new web app"
3. Select Flask Python Web framework when prompted (select Python 3.10)
4. IMPORTANT make sure the path is /home/{user}/withings_api_dev/app.py, where {user} is your pythonanywhere username. The withings_api_dev directory can be replaced by another name so long as app.py and project.conf is copied there.

## Clone repository

Open up a bash console from the pythonanywhere dashboard and execute:
```
git clone https://github.com/jasonwong-lab/withings_api_dev.git
```

## Create a withings developer account

If you haven't already, create a developer account on withings' api [here](https://account.withings.com/partner/add_oauth2)
with the following parameters:
* callback url = https://{user}.pythonanywhere.com/get_token

If you try to test the callback url, it won't work for now. It is OK to continue.

Keep a note of the client_id and client_secret these will need to be used for project configuration file.

## Create project.conf

project.conf contains information required to access withings API. As it contains it contains authentication information for your withings developer account, it is part of .gitignore.

In the pythonanywhere bash console, make a copy of project.template.conf and enter  your client_id and client_secret from the developer account just created.

Also enter any string for {state} and https://{user}.pythonanywhere.com/get_token for callback_uri.
```
cp project.template.conf project.conf
nano project.conf
```

## Testing the app

Open a web browser and go to https://{user}.pythonanywhere.com

The following will happened:
* You are redirected to account.withings.com with a prompt to log in.
* After logging in the user will be asked to accept sharing data with the app.
* The logged user are is redirected to the "callback_uri" on your domain with two parameters: "code" and "state".
* The app can then use the "code" (which is the Authorization token) to genenerate a access token.
* With this access token you can get the data from the user, or even subscribe to a notification features.
* As an example the app finally list the devices of the user (if any) in JSON format.


NB: This is an example for communicating with Withings' developer API. To develop other functions see full API documentation (https://developer.withings.com/api-reference/)
