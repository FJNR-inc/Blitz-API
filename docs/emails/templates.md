# Email templates

Here is the list of all variables you can use in your Email Service Provider for each email template used inside 
the project.

!!! warning
    Multiple emails are not migrated to ESP's template and need a developer to be updated at this time. If one of the 
    emails you want to change is not listed here do not hesitate to contact the support team to plan the migration 
    of the email you need.

## WELCOME_VIRTUAL_RETREAT
This email is sent when a user reserve a place to a virtual retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_START_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_START_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| RETREAT_END_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_END_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| LINK_TO_BE_PREPARED | Link to know how to prepare
| LINK_TO_USER_PROFILE | -

## WELCOME_PHYSICAL_RETREAT
This email is sent when a user reserve a place to a physical retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_START_TIME | Format examples: 2020-01-25 01:05
| RETREAT_END_TIME | Format examples: 2020-01-25 01:05

## REMINDER_VIRTUAL_RETREAT
This email is sent 1 day before a virtual retreat to all user with a reservation on that retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_START_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_START_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| RETREAT_END_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_END_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| LINK_TO_BE_PREPARED | Link to know how to prepare
| LINK_TO_USER_PROFILE | -

## REMINDER_PHYSICAL_RETREAT
This email is sent 7 days before a physical retreat to all user with a reservation on that retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_START_TIME | Format examples: 2020-01-25 01:05
| RETREAT_END_TIME | Format examples: 2020-01-25 01:05

## THROWBACK_VIRTUAL_RETREAT
This email is sent 1 day after a virtual retreat to all user with a reservation on that retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_START_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_START_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| RETREAT_END_DATE | Format examples: 3 janvier 2020 (in french only)
| RETREAT_END_TIME | Format examples: 1h30, 12h30, 1h00, 1h05
| LINK_TO_REVIEW_FORM | -
| LINK_TO_BE_PREPARED | Link to know how to prepare
| LINK_TO_USER_PROFILE | -

## THROWBACK_PHYSICAL_RETREAT
This email is sent 1 day after a physical retreat to all user with a reservation on that retreat

| Variable | Description |
| --- | --- |
| USER_FIRST_NAME | -
| USER_LAST_NAME | -
| USER_EMAIL | -
| RETREAT_NAME | -
| RETREAT_PLACE | -
| RETREAT_START_TIME | Format examples: 2020-01-25 01:05
| RETREAT_END_TIME | Format examples: 2020-01-25 01:05
