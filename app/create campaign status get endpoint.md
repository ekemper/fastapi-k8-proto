


# Your job is to create an extreamly detailed set of step by step instructions for an ai agent to perform the following task:

create an api endpoint to get the status of a campaign. 


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

**Current State:** currently the api does not have a route to get the status of a campaign. 



**Detailed Description:**
- create an api endpoint to get the status of a campaign. 
- the endpoint should return a json object with the following fields:
    - campaign_id
    - campaign_name
    - campaign_status

## Technical Requirements
**Must Have:**
- [ ] correct error handling, use the patterns from the existing endpoints as a guide.
- [ ] a new schema definition for the response object.
- [ ] a new schema definition for the request object.
- [ ] functional api tests for the new endpoint. No unit tests are needed.just functional tests. just a set of functional api layer tests - the tests should hit the api and then check the database for results


**Constraints:**
- Follow the existing patterns and conventions for the api.
- use the existing tests as a guide for the new tests.
- the new endpoint should be added to the same file as the other campaign endpoints
- it should be a protected route. use the auth middleware to protect the route. like the other campaign endpoints.


## Files & Components Involved
**Primary Files to Modify:**
- `app/services/campaign.py`
- `app/api/endpoints/campaigns.py`

**Related Files (may need updates):**
- `main.py` - to register the new endpoint



**Data Models:**
- there are no new models or changes to existing models 

## Success Criteria
The change will be considered complete when:
- [ ] the files have been updated with the new endpoint
- [ ] [All tests pass]
- [ ] [Documentation is updated]
- [ ] [No breaking changes to existing functionality]

---

# Please create the plan for this task and document it!