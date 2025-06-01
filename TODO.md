
TODO : re implement the logic that prevents a lead being created with an email that already belongs to an exiting lead

TODO: figure out millionverifier or find another service

TODO: if an errror is recieved from a third party api call that involves rate limiting or account billing limits or token limits we should have a slack note

TODO: implement logic that will halt the queue if a rate limiting error is recieved from an api integration. 

TODO: event tracking - everything that happens to a campaign creates an event
    * create 
    * start
    * n leads fetched
    * ENRICH_LEAD job completed / failed
    * api error recieved 



TODO: campaign report based on event data, 
    * create a cron job that executes every minute
    * the cron job grabs all the events for the campaign and compiles a report (json) object
    * the json object should contain the display data for the client dash
    * actually for the first pass, the api endpoint should just do what the cron job would do. ( then we assess the performance )
    * as the reports get more complex and require more data processing, we implement the cronjob  



TODO: migrate / merge prod config , prod ready checklist

TODO: Deploy and test on heroku


TODO: create roles ( permissions later ) admin and client

TODO: relate users to orgs: users belong to orgs

TODO: implement role based access control at the api surface: admins get everything - clients can only see the dash associated with their org

TODO: implement MVP client dash: make a plan for the first few metrics visualizations, need design
