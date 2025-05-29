


# Your job is to create an extreamly detailed set of step by step instructions for an ai agent to perform the following task:

    * We need to create a unified application logging system and patterns according to the specifications below.


# Here is detailed information about what needs to happen for the code change to be successful:

**Current State:** There is currently no organized logging system in the app. 

**Detailed Description:**
- What functionality needs to be added/modified/removed:
    * we need to implement a unified logging system that will be used throuout the app in all the containers. 

- Why this change is needed:
    * consistent logging patterns help us debug and understand the system, in prod it is critical for application monitoring

- How it should work from a user perspective:
    * from a developer perspective ( also a user ) the logging system should be simple to use, easy to understand, and clearly documented. The logs themselves should strike a balance between being readable by a human, and verbose enough to allow visibility in to the processes that need to be interrogated. 

## 3. Technical Requirements
**Must Have:**
- [ ] A single logging system that is use throuought the app
- [ ] clear documentation of the system and how to use it
- [ ] follow the conventions and patterns described in the files below

## 4. Files & Components Involved
**Files to keep in context, create, or modify:**

- `documentaion/LOGGING.md`
- `/app/core/logging_config.py`
- the docker configuration will need to map :  ./logs:/app/logs  ( or something equivalent in function ). All of the application log files should land there

- Please create `logger.py` - 
```
from __future__ import annotations
import logging
from typing import Optional

# Ensure central logging is initialised once this module is imported
from server.utils.logging_config import init_logging  # noqa: F401


def get_logger(name: Optional[str] = None) -> logging.Logger:  # pragma: no cover
    """Return a logger that is guaranteed to be configured.

    If *name* is omitted, the root "app" logger is returned.  This helper exists so
    that modules can simply do::

        from server.utils.logger import get_logger
        logger = get_logger(__name__)
    """
    if name is None:
        name = "app"
    return logging.getLogger(name) 
```

## 5. Expected Behavior
**Before:** Usnorganized logging  / printing . multiple sources of information
**After:** Unified logging patterns, easy to access and parse single source of truth for application information that is evolved during runtime.

**User Flow:**
1. Developers should be able to easily view / tail logs from a single file that has docker logs and application logs.
2. it should be easy for ai agents to acces this information to add it to the chat context. 

## 7. Testing Requirements
**Integration Tests:** 
* please create a small ( 5 ish ) suite of simple ( not over engineered ) tests to proove the functionallity 
**Manual Testing Steps:**
* in the plan you are creating, outline simple steps that an Ai agent can take to prove the new logging system is working as intended

## 8. Dependencies & Setup
**New Dependencies:** 
* please add any new dependencies to the appropriate requirements file ( base. prod etc ), and ensure the are installed properly.
**Environment Variables:** here are the env vars that will be present in the .env file for you to work with. please document them in the plan and the final documentation in the project
```
LOG_DIR=./logs
LOG_LEVEL=INFO
LOG_ROTATION_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
LOG_SERVICE_HOST=localhost
LOG_SERVICE_PORT=8765
LOG_BUFFER_SIZE=1000
```

**Build/Deploy Changes:** [Any changes to build process]

## 9. Examples & References
**Similar Implementations:** [Point to existing code that does something similar]
**External References:** [Links to documentation, examples, etc.]
**Mockups/Wireframes:** [Visual references if applicable]

## 10. Success Criteria
* pleae create a list of success criteria for this plan 

---

Plese generate the plan for this task! Thanks!