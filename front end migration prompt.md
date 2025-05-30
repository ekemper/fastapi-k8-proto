


# Your job is to create an extreamly detailed set of step by step instructions for an ai agent to perform the following task:

There is a front end directory with a fully functional react app - we need to integrate the api calls that it makes with the api in this project

IMPORTANT: we will only be updating the logic on the front end app.


## In creating the plan, the following rules must be observed and followed:

    * Make a comprehensive assessment of the entire application codebase, its archetecture, patterns, tests, services, and documentation. You will need to incorporate this knowledge into the plan you are creating. 

    * The current patterns, conventions, and configuration for this app should be maintained at all cost. If there are specific changes to establihed patterns, these should be documented. Please make copious use of doc strings and comments in source code to add context for decisions that are made. If there is significant change - please create a markdown document in the documentation directory to reestablish the source of truth for the pattern. 

    * The instructions should break the process down in to discrete, testable steps.

    * Each step should have a clear goal, a clear set of actions to be performed by the ai agent, and a strategy for confirming that the actions were sucessfull. ( either running tests, curling an endpoint, manual testing, or checking for specific rows in a database table. )

## The following instruction MUST BE followed as part of the implementation of the plan that you are creating. Please add them to the general rules / instructions section of the plan:

    * In interacting with the User, always make a technical, critical assessment for any queries, statements, ideas, questions... Don't be afraid to question the user's plan. 

    * Always ask for more clarification if needed from the user when implementing the steps of the plan. 
    
    * NEVER MAKE SHIT UP - always provide rationale for a desiscion. 

    * In cases where there are code edits, the ai agent is to perform the changes.

    * In cases where there are commands to be run, the ai agent is to run them in the chat window context and parse the output for errors and other actionable information.

    * When createing and running migrations, run the commands in the api docker container.

    * Pay particular attention to the api testing  logic ( routes, service, model, tests). Always run the tests after making changes to the api.

    * When running individual tests, run them in the api docker container: use ' Docker exec api pytest...'

    * When running the whole suite of tests, use 'make docker-test'.

    * Lets leave the unit tests out of the picture for the moment - we need a comprehensive set of functional api layer tests - the tests should hit the api and then check the database for results. 

    * When planning code edits, plan to update the tests immediately.

    * For the plan you create, please create a md document in the root of the project and put the instructions there for safe keeping


# Here is detailed information about what needs to happen for the code change to be successful:

## Context & Overview
**Project Type:** [e.g., fastAPI, React frontend, Full-stack web app, etc.]
**Technology Stack:** [e.g., Python/fastAPI, React/TypeScript, PostgreSQL, etc.]
**Current State:** there is a well formed api for user auth, campaigns, organizations, leads, and jobs.

**Detailed Description:**
- What functionality needs to be added/modified/removed
    * the front end web app needs to have full api integration with  auth, orgs, campaigns, and jobs
- How it should work from a user perspective
    * all of the front end features for auth, orgs , campaigns and jobs should function with the api communication that is defined in the api logic
- the cors implementation will have to be updated to allow api comms from the frontend running locally
- review the docker configuration is properly implemented, ensure that best patterns and practices are followed
- if there any env vars that need to be updated or created, use the env.example as a reference. please create any new env vars in the env.example file and I will add them manually to the actual .env
- if you need to reference env vars, the example file is up to date with all that is available in the actual .env. Or, you can use `cat .env`
- do not otherwise fuck with the .env file please


## Technical Requirements
**Must Have:**
- [ ] create a comprehensive list pf api endpoints that are available and compare that to the api endpoints that are used by the front end. document gaps in support for the front end requirements.
- [ ] update the request and respons shapes that are expected by the front end to match what is defined in the schemas for each endpoint
- [ ] 

**Constraints:**
- do not create any front end test yet. we will tackle that later
- ignore the events logic on the front end for now

##  Files & Components Involved
- the entire frontend directory will be useful context
- all of the schemas for the endpoints
- the routes files will be important context for defining the api surface to compare to the expectations of the frontend

##  Expected Behavior
**Before:** there is currently no front end integrated
**After:** the front end features related to orgs, auth, campaigns, leads, and jobs will work


##  API/Interface Changes
IMPORTANT - there will be no back end changes here. do not modify the actual api endpoints. 
- if in the process of following this implementation plan we find that there are backend updates needed, create a document in the root of the dorectory to keep track of them

##  Testing Requirements
I will manually test the front end


## 10. Success Criteria
The change will be considered complete when:
- [ ] create a list of measurable outcomes 

but in addition,

- [ ] [All tests pass]
- [ ] [Documentation is updated]
- [ ] [No breaking changes to existing functionality]

---

# Please create the plan for this task and document it!