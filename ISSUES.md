# Issues Analysis

> **Instructions**: Use this template to document all issues you find in the codebase.
> Replace the example entries with your actual findings. Add as many issues as you find.
> Rename this file to `ISSUES.md` before submitting.


## Summary

| Type | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Product Issues | 0 | 0 | 3 | 1 | 4 |
| Code Issues | 0 | 3 | 8 | 4 | 15 |

---

## Product Issues

> Product issues are user-facing problems: broken functionality, missing validation, poor UX, data integrity risks visible to users.

### [P1] Missing Confirmation Dialog

**Severity**: Medium

**Location**: `problems/templates/problems/index.html` (migrate buttons)

**Description**:
When clicking "Migrate to Storage/Azure", the action executes immediately without asking for confirmation. This could lead to accidental data overwrites.

**Impact**:
- Users might accidentally overwrite test cases
- No way to cancel a mistaken click
- Potential data loss

**Suggested Fix**:
Add a JavaScript confirmation dialog before form submission for destructive actions.

---

### [P2] Unrendered HTML Tags

**Severity**: Low

**Location**: `problems/templates/problems/index.html`

**Description**:
Raw HTML tags (specifically `<p>`) are not being stripped or rendered correctly in the UI for fields like Description, Input Format, and Output Format. Users see `<p>Some text</p>` instead of formatted text.

**Impact**:
- Poor User Experience.
- Makes the problem statement harder to read.

**Suggested Fix**:
Use the Django `|safe` filter in the template if the HTML is trusted, or use `strip_tags` if plain text is desired.

---

### [P3] No User Feedback on Migration Errors

**Severity**: Medium

**Location**: Migration flows, UI

**Description**:
When a migration fails (e.g., due to API error, storage error, or DB error), the user is not shown a clear error message or feedback. The UI may remain unchanged or show a generic message.

**Impact**:
- Users may think migration succeeded when it failed.
- Frustration and wasted time troubleshooting.
- Data integrity risk if users proceed based on incorrect state.

**Suggested Fix**:
Show clear, actionable error messages in the UI when migration fails. Log errors with context and provide retry options.

---

### [P4] Slow PostgreSQL Flow

**Severity**: Medium

**Location**: Database migration, test case saving

**Description**:
The PostgreSQL flow for saving or updating test cases is slow, especially for large problems. This causes delays in migration and poor user experience.

**Impact**:
- Long wait times for users during migration.
- Increased risk of timeouts or failed migrations.
- Frustration for users with large datasets.

**Suggested Fix**:
Optimize database queries and use bulk operations where possible. Add progress indicators in the UI. Consider asynchronous processing for large migrations.

---

## Code Issues

> Code issues are technical: bugs, security, performance, code quality.

### [C1] Unused Imports

**Severity**: Low

**Location**: `problems/views.py:6-8`

**Description**:
```python
from bs4 import BeautifulSoup  # Never used
from django.core.cache import cache  # Never used
```
These imports are declared but never used in the file.

**Impact**:
- Slightly increases memory usage
- Makes code harder to understand (suggests these modules are used when they're not)
- May cause confusion during code review

**Suggested Fix**:
Remove unused imports. Consider using a linter (flake8, ruff) to catch these automatically.

---

### [C2] Test Case Truncation in DB

**Severity**: High

**Location**: `PolygonMigration/problems/views.py` (Line ~523)

**Description**:
Code intentionally truncates input and output to 260 bytes when saving to `ProblemTestCase` table.
```python
truncated_input = input_data[:260]
truncated_output = output_data[:260]
```

**Impact**:
- Database does not store full test cases.
- Cannot be used for judging if the judge system relies on the database content.
- `Migrate Test Cases to DB` is lose.

**Suggested Fix**:
If the intention is full archival, use `FileField` or check database limits. If this is just for preview, rename the fields to explicitly state `preview_input`.

---

### [C3] Flaky Test Case Extraction

**Severity**: High

**Location**: `problems/polygon_api.py` (Test case extraction logic)

**Description**:
Test case extraction is inconsistent. For the same problem, sometimes test cases are extracted correctly, and other times they are missing. This has been specifically observed once when I refetched the same problem. One of the test case was missing which was present in the table earlier.

**Impact**:
- Reliability is compromised; users cannot trust the migration tool.
- Potential data loss if the user assumes migration was successful when it wasn't.
- Hard to debug due to race condition or API inconsistency.

**Suggested Fix**:
Investigate `polygon_api.py`. Add robust error handling, retry logic for Polygon API calls, and logging to identify if the issue is with the API response or the parsing logic. Ensure unique request IDs or disable caching if applicable.

---

### [C4] Inefficient Redis Connection Handling

**Severity**: Medium

**Location**: `problems/polygon_api.py` (multiple methods)

**Description**:
A new Redis connection is created every time a cache operation is performed (e.g., in `store_test_cases_in_redis`, `get_test_cases_from_redis`, `clear_test_cases_from_redis`). This is done via repeated calls to `_get_redis_connection()` which I have added to remove duplication of redis connection and a bug while reading for SSL from env variables.

**Impact**:
- Increased latency for every cache operation.
- Unnecessary overhead and resource usage.
- Potential connection pool exhaustion under high load.

**Suggested Fix**:
Refactor to use a single, shared Redis connection or connection pool per request or per application instance.

---

### [C5] Storage Client Instantiation on Every Operation

**Severity**: Medium

**Location**: `problems/storage/factory.py`, `polygon_api.py`

**Description**:
The storage provider client (GCS, Azure, Local, GDrive) is instantiated every time `get_storage_provider()` is called, which happens in multiple places for every upload/delete operation.

**Impact**:
- Increased initialization overhead.
- Possible redundant authentication and resource allocation.
- Slower performance for batch operations.

**Suggested Fix**:
Cache the storage provider instance at the application or request level, and reuse it for all storage operations.

---

### [C6] Code Duplication

**Severity**: Low

**Location**: `polygon_api.py`, `views.py`, storage providers

**Description**:
Similar logic for uploading, deleting, and fetching test cases is repeated across multiple storage provider implementations and migration flows.

**Impact**:
- Harder to maintain and update.
- Increased risk of inconsistent behavior or bugs.
- Larger codebase with redundant code.

**Suggested Fix**:
Refactor common logic into shared utility functions or base classes. Use DRY (Don't Repeat Yourself) principles.

---

### [C7] Lack of Centralized Error Handling

**Severity**: Medium

**Location**: `polygon_api.py`, storage providers, views

**Description**:
Error handling is scattered across multiple functions, often using bare `except:` or logging errors without propagating them. This can lead to silent failures and makes debugging difficult.

**Impact**:
- Hard to trace root causes of failures.
- Inconsistent error reporting to users.
- Potential for missed exceptions and data corruption.

**Suggested Fix**:
Implement centralized error handling using custom exception classes and middleware. Ensure all errors are logged and surfaced appropriately.

---

### [C8] Insufficient Logging Granularity

**Severity**: Low

**Location**: `polygon_api.py`, views, storage providers

**Description**:
Logging is present but often lacks context (e.g., which user, which problem, which operation). Some critical operations may not be logged at all.

**Impact**:
- Harder to audit and debug issues.
- Reduced observability for production monitoring.

**Suggested Fix**:
Add more detailed logging, including user IDs, problem IDs, and operation types. Use structured logging if possible.

---

### [C9] Hardcoded Configuration Values

**Severity**: Low

**Location**: Various files (e.g., expiry times, storage provider types)

**Description**:
Some configuration values (like Redis expiry, storage provider selection) are hardcoded in the code instead of being set via environment variables or Django settings.

**Impact**:
- Difficult to change configuration without code changes.
- Reduces flexibility for deployment and testing.

**Suggested Fix**:
Move all configuration values to Django settings or environment variables.

---

### [C10] Missing Unit Tests for Edge Cases

**Severity**: Medium

**Location**: `tests/`, migration logic

**Description**:
While integration tests exist, there are few or no unit tests covering edge cases (e.g., duplicate titles, empty test cases, large test cases).

**Impact**:
- Increased risk of regressions.
- Edge cases may break silently in production.

**Suggested Fix**:
Add targeted unit tests for all documented edge cases and failure scenarios.

---

### [C11] No Rate Limiting or Throttling

**Severity**: Medium

**Location**: API endpoints, migration flows

**Description**:
There is no rate limiting or throttling for API calls to Polygon or for migration operations. This can lead to abuse or accidental overload.

**Impact**:
- Risk of hitting external API limits.
- Potential denial of service for other users.

**Suggested Fix**:
Implement rate limiting at the API or view level, and add retry/backoff logic for external calls.

---

### [C12] Lack of Transaction Management in DB Operations

**Severity**: Medium

**Location**: Database migration, views

**Description**:
Many database operations (especially bulk updates/inserts) do not use explicit transactions. This can lead to partial updates if an error occurs mid-operation.

**Impact**:
- Data inconsistency if migration fails partway.
- Harder to roll back or recover from errors.

**Suggested Fix**:
Wrap bulk DB operations in atomic transactions using Django's `transaction.atomic()` context manager.

---

### [C13] No Caching for Expensive Computations

**Severity**: Low

**Location**: Problem fetching, test case generation

**Description**:
Some expensive computations (e.g., parsing large Polygon problems, generating test cases) are performed on every request without caching.

**Impact**:
- Increased server load and slower response times.
- Redundant work for repeated requests.

**Suggested Fix**:
Cache results of expensive computations using Redis or Django's cache framework.

---

### [C14] Tight Coupling Between Views and Storage Logic

**Severity**: Medium

**Location**: `views.py`, storage providers

**Description**:
Views directly invoke storage provider logic, making it hard to test or swap out storage backends.

**Impact**:
- Reduced testability and flexibility.
- Harder to refactor or extend storage logic.

**Suggested Fix**:
Introduce service layers or use dependency injection to decouple views from storage logic.

---

### [C15] Lack of Input Validation and Sanitization

**Severity**: High

**Location**: Forms, API endpoints

**Description**:
Some user inputs (problem titles, descriptions, test case data) are not validated or sanitized before processing.

**Impact**:
- Risk of injection attacks or data corruption.
- Poor user experience due to unhandled invalid input.

**Suggested Fix**:
Add validation and sanitization for all user inputs using Django forms or serializers.

---

## Edge Case Analysis

### Question 1: Empty Sample Test Cases

> A Polygon problem has **0 sample test cases** but **15 regular test cases**. What happens when you migrate this problem?

**Your Analysis**:

It works fine. The code logic doesn't strictly require sample test cases. It will just iterate through the 15 regular test cases and save them. 
- In the database, the `SampleTestCase` table will simply have no entries for this problem. 
- The only minor side effect is that the "Sample Tests" section in the problem statement preview might look empty or blank, but the migration process itself will succeed without errors.

**Code References**:
- `views.py`
- `models.py`

---

### Question 2: Test Case Count Reduction

> A problem is migrated with **20 test cases**. Later, the problem setter removes 8 test cases on Polygon (now 12 remain). The problem is re-migrated. What happens?

**Your Analysis**:

This reveals a bug in the code for the Database migration:
- **For Cloud Storage:** It works correctly because the code intentionally deletes the entire folder before uploading the new files.
- **For Database:** It breaks. The code loops through the new 12 test cases and updates the first 12 records in the database. However, it **forgets to delete** the remaining 8 records that are no longer needed. 
- **Result:** You end up with 20 test cases in the database: the first 12 are correct/updated, but the last 8 are "zombie" test cases left over from the previous migration.

**Code References**:
- `views.py`
- `polygon_api.py`

---

### Question 3: Duplicate Problem Titles

> Two different Polygon problems have the exact same title: "Two Sum". You migrate the first one successfully. Then you try to migrate the second one. What happens?

**Your Analysis**:

The application will crash with a database error.
- When generating the "slug" (the URL-friendly name), it converts "Two Sum" to `two-sum`.
- The database enforces that the `slug` must be unique.
- The first problem claims `two-sum`. When the second one tries to use `two-sum`, the database rejects it with an Integrity Error.
- **Fix Needed:** The code should check if the slug exists and append a number (e.g., `two-sum-1`) to make it unique.

**Code References**:
- `views.py`
- `models.py`

---

### Question 4: Data Truncation

> When test cases are saved to the database via "Migrate Test Cases to DB", some data is intentionally discarded. What data is lost? Why might this cause problems?

**Your Analysis**:

The system cuts off (truncates) the input and output data after just **260 characters**.
- **What is lost:** For almost any real competitive programming problem, the input/output files are much larger than 260 characters. We lose 99% of the test data for large cases.
- **Why it's a problem:** These database records are essentially corrupted/incomplete. If you tried to use them to actually judge a user's submission, the judge would fail because it doesn't have the full input or expected output. It seems this feature was built just for "previewing" data, not for actually storing the full test cases.

**Code References**:
- `views.py`

---
