[![Build Status](https://travis-ci.org/FJNR-inc/Blitz-API.svg?branch=develop)](https://travis-ci.org/FJNR-inc/Blitz-API)
[![Coverage Status](https://coveralls.io/repos/github/FJNR-inc/Blitz-API/badge.svg?branch=develop)](https://coveralls.io/github/FJNR-inc/Blitz-API?branch=develop)
[![Updates](https://pyup.io/repos/github/FJNR-inc/Blitz-API/shield.svg)](https://pyup.io/repos/github/FJNR-inc/Blitz-API/)


# Blitz API

 - Free software : MIT license
 - Front-end repository : https://github.com/FJNR-inc/Blitz-Website

## Issue manager

Issues are handled in a [Redmine instance](https://genielibre.com/projects/blitz-paradisio).
Feel free to create an account there to begin contributing!

---

# Quickstart

We're going to install and configure the latest develop build of this API.

## Clone the project

First of all, you need to clone the project on your computer with :

```
git clone https://github.com/FJNR-inc/Blitz-API.git
```

## Create a virtual environment

[Virtualenv](https://virtualenv.pypa.io/) provides an isolated Python environment, which are more practical than installing packages system-wide. They also allow packages to be installed without administrator privileges.

1. Create a new virtual environment
```
virtualenv env
```

2. Activate the virtual environment
```
. env/bin/activate
```

You need to ensure the virtual environment is active each time you want to launch the project.

## Install all requirements

Your OS will need SQLite3 (<3.26) for unit testing.

Requirements of the project are stored in the `requirements.txt` file.
Requirements for development related actions are stored in the `requirements-dev.txt` file.
You can install them with:

**WARNING** : Make sure your virtual environment is active or you will install the packages system-wide.
```
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Configure the database

Django has a system of database migration. You first need to apply all existing "migrations" to update your local database.

```
python manage.py migrate
```

**Note:** The project uses a squlite3 file as database to simplify developement. Once in production, feel free to switch to a DB server.

## Test the installation

You can now launch an instance of the API and visit the included admin website.

To login into the admin page, you'll need to create a superuser:
```
python manage.py createsuperuser
```
You can now launch the instance with:
```
python manage.py runserver
```

You can now [visit the homepage](http://localhost:8000/) to validate the installation.

```
http://localhost:8000/ and http://localhost:8000/admin
```

## Custom settings - NOT IMPLEMENTED YET

If you need to have custom settings on your local environment, you can override global settings in `apiBlitz/local_settings.py`.

## Deployment process

1. Activate Deploy screen on frontend

![deploy_page](doc_images/deploy_page.png)

Need to be execute in frontend repository
```
npm run deploy:prod:deploy_page
```

2. Deploy api code
```
./utils/deploy_prod.sh
```

3. Deploy frontend
```
npm run deploy:prod
```