# Polygon Migration Tool Documentation

## 1. User Flows

### 1.1 Login Flow
- **Trigger**: User navigates to login page.
- **Process**: 
    1. User enters credentials (superuser created via CLI).
    2. Django Auth system validates credentials.
    3. On success, redirects to the main dashboard (`/`).
- **Data**: `email`, `password`.

### 1.2 Fetch Problem from Polygon
- **Trigger**: "Fetch Problem" button on Dashboard.
- **Input**: Polygon Problem ID.
- **Process**:
    1. Backend calls `polygon_api.get_problem_info(id)`.
    2. **Authentication**: Uses `POLYGON_API_KEY` and `POLYGON_API_SECRET` to sign the request (HMAC SHA-512).
    3. **Polygon API Call**: hits `problem.info` to get title, limits, etc.
    4. **Caching/Parse**: Backend fetches `problem.html` (the statement text) from Polygon.
    5. **Redis**: Caches the fetched data using Redis to avoid repeated heavy calls.
    6. **Response**: Data is displayed in a preview format on the dashboard.
- **External API**: `problem.info`, `problem.files` (Polygon).

### 1.3 Migrate Problem to Database
- **Trigger**: "Migrate to Database" button after fetching.
- **Process**:
    1. User selects `Difficulty`, adds `Tags` in the form.
    2. **Transaction**: Backend starts a DB transaction.
    3. **Problem**: Creates/Updates row in `problems_problem` table.
    4. **Tags**: Creates/Links `ProblemTag`s in `problems_problemtag` table.
    5. **Samples**: Syncs sample test cases (from the statement) into `problems_sampletestcase`.
    6. **Checkers**: Identifies checker type.
- **Database Operations**: Insert/Update `problems_problem`, `problems_problemtag`, `problems_sampletestcase`.

### 1.4 Migrate Test Cases to Database
- **Trigger**: "Migrate to Database" logic inherently handles *Sample* Test Cases, but hidden inputs can be synced too.
- **Note**: Generally, "Test Cases" refers to the *files* used for judging (Cloud Storage), while "Sample Test Cases" are text shown to users (Database).

### 1.5 Migrate Test Cases to Cloud Storage
- **Trigger**: "Migrate to Storage" button (secondary action).
- **Process**:
    1. Backend calls `polygon_api.migrate_to_azure_blob` (generic function name, handles all providers).
    2. **Redis Check**: Checks if test case list is cached; if not, fetches from Polygon.
    3. **Download**: Backend downloads ALL inputs and output files from Polygon (`problem.file` endpoint).
    4. **Custom Checker**: Checks if a custom checker source (`checker.cpp`) exists.
    5. **Storage Provider**: Uses the configured `StorageProvider` (GCS, GDrive, or Local).
    6. **Upload**:
        - Cleans target folder: `test_cases/{db_id}/`.
        - Uploads input files (e.g., `1`, `2`).
        - Uploads output files (e.g., `1.a`, `2.a`).
- **Storage**: 
    - **Cloud**: Google Cloud Storage (Bucket), Google Drive (Folder).
    - **Local**: `media/test_cases/` folder.

---

## 2. Data Models

### Problem
| Field | Type | Description |
|-------|------|-------------|
| `polygon_id` | CharField | Unique ID from Polygon system (e.g. "69927"). |
| `title` | CharField | Problem name. |
| `slug` | SlugField | Unique URL slug. |
| `difficulty` | CharField | (Easy, Medium, Hard). |
| `time_limit` | Float | Execution time in milliseconds. |
| `memory_limit` | Int | Memory limit in MB. |
| `test_case_count` | Int | Total number of judgment test cases. |
| `checker_type` | CharField | Type of checker used (e.g., `wcmp`, `custom`). |
| `input_format` | TextField | HTML description of input. |
| `output_format` | TextField | HTML description of output. |
| `constraints` | TextField | Problem constraints (N, M limits). |
| `problem_statement` | TextField | The full problem legend/story. |
| `is_locked` | Bool | If true, prevents further editing. |
| `genie_chat` | Bool | Enabled Genie Chat feature. |
| `notes` | TextField | Internal notes from Polygon. |

### SampleTestCase
| Field | Type | Description |
|-------|------|-------------|
| `problem` | ForeignKey | Link to parent Problem. |
| `input` | TextField | Sample input data (text). |
| `output` | TextField | Expected sample output (text). |
| `order` | Int | Sequence order for display. |

### ProblemTag
| Field | Type | Description |
|-------|------|-------------|
| `tag_name` | CharField | Unique identifier (e.g., "math"). |

### User (Custom Auth)
| Field | Type | Description |
|-------|------|-------------|
| `email` | EmailField | Primary login identifier. |
| `username` | CharField | Unique username. |
| `first_name` | CharField | User's first name. |
| `is_staff` | Bool | Admin access flag. |
| `leetcode_profile` | URLField | Link to LeetCode. |
| `codeforces_profile` | URLField | Link to Codeforces. |
...

---

## 3. External Integrations

### 3.1 Polygon API
- **Base URL**: `https://polygon.codeforces.com/api/`
- **Authentication**: 
    - Requires `apiKey` and `apiSig` query parameters.
- **Endpoints**:
    - `problem.info`: Retreives core metadata (Time Limit, Memory Limit).
    - `problem.files`: Lists all files (source, resources, tests).
    - `problem.saveFile`: Downloads the actual binary/text content of a file.
    - `problem.tests`: Fetches the list of manual/script test cases.

### 3.2 Cloud Storage (Abstracted)
- **Architecture**: uses the **Strategy Pattern** via `StorageProvider` interface.
- **Factory**: `problems.storage.factory.get_storage_provider()` selects implementation based on `.env`.
- **Implementations**:
    1.  **Google Cloud Storage (GCS)**:
        -   **Library**: `google-cloud-storage`.
        -   **Auth**: Service Account JSON Key (`GCS_CREDENTIALS_FILE`).
        -   **Structure**: Objects stored as `{bucket_name}/test_cases/{problem_id}/{filename}`.
    2.  **Google Drive**:
        -   **Library**: `google-api-python-client`.
        -   **Auth**: OAuth 2.0 (Client Secret) or Service Account (Shared Drive).
        -   **Structure**: Folder hierarchy `Root -> test_cases -> {problem_id} -> files`.
    3.  **Local Storage**:
        -   **Location**: `MEDIA_ROOT/test_cases/{problem_id}/`.
        -   **Use Case**: Development/Testing without cloud costs.

### 3.3 Redis Caching
- **Purpose**: Caches Polygon API responses to reduce latency and API hitting limits.
- **Key Keys**: 
    - `polygon_migration_test_cases_{problem_id}_count`
    - `polygon_migration_test_cases_{problem_id}_test_{number}`
- **Expiry**: Configurable TTL (e.g. 1 hour).
