"""Business logic layer (services).

Services orchestrate operations by combining repository calls, external
API clients, and domain model validation. They sit between the route
handlers (routers/) and the data access layer (repositories/).

The key benefit of this separation:
- Routers stay thin (parse request, call service, return response).
- Services contain testable business logic with no HTTP concerns.
- Repositories handle pure data access with no business rules.
"""
