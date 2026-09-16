# Download Management

This context receives media requests and tracks their progress from submission to completion or failure.

## Language

**Download**:
A request to retrieve media from a URL, tracked across its lifetime.
_Avoid_: Job, item, row

**Download attempt**:
One execution of a Download; a Download may require several attempts before completion or failure.
_Avoid_: Run
