# Issues Analysis

> **Instructions**: Use this template to document all issues you find in the codebase.
> Replace the example entries with your actual findings. Add as many issues as you find.
> Rename this file to `ISSUES.md` before submitting.


## Summary

| Type | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Product Issues | 0 | 0 | 1 | 1 | 2 |
| Code Issues | 0 | 2 | 0 | 1 | 3 |

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
