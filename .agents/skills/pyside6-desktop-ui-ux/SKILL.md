---

name: pyside6-desktop-ui-ux
description: Design, review, refactor, or implement professional PySide6 Qt Widgets desktop interfaces. Use when working on PySide6 views, windows, dialogs, tables, layouts, navigation, QSS styles, user feedback, loading states, threading related to UI responsiveness, or desktop UX. Especially useful for enterprise data-processing applications. Do not use for pure backend/business-logic tasks that do not affect the desktop interface.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# PySide6 Desktop UI/UX

Build PySide6 desktop interfaces as professional, maintainable applications rather than collections of widgets.

Prefer incremental improvement of an existing application over unnecessary rewrites.

## Primary goals

Every PySide6 interface should prioritize:

1. usability
2. clarity
3. responsive layout behavior
4. maintainability
5. accessibility
6. consistent visual hierarchy
7. clear user feedback
8. separation of presentation and business logic
9. desktop performance
10. predictable behavior

Do not optimize aesthetics at the expense of usability.

---

# 1. Inspect before modifying

Before changing an existing UI, inspect:

* application entry point
* QMainWindow hierarchy
* existing QWidget subclasses
* layouts
* QStackedWidget or navigation architecture
* QTableView / QTableWidget usage
* models
* delegates
* signals and slots
* workers or QThreads
* QSS stylesheets
* reusable widgets
* services
* business rules
* file processing
* application packaging behavior

Do not redesign or rewrite major parts of the application before understanding the current architecture.

Prefer minimal, compatible improvements.

Preserve existing working business rules unless the user explicitly requests changing them.

---

# 2. Separate UI from business logic

QWidget, QMainWindow and dialog classes should coordinate presentation and user interaction.

They should not contain substantial business processing.

Prefer an architecture similar to:

```text
src/
├── app.py
│
├── ui/
│   ├── main_window.py
│   ├── pages/
│   ├── dialogs/
│   ├── widgets/
│   └── styles/
│
├── models/
│
├── services/
│
├── workers/
│
└── utils/
```

Responsibilities:

```text
ui/
    Visual state and user interaction.

models/
    Qt Model/View adapters and presentation-oriented data models.

services/
    Business rules, Excel processing, PDF generation, validation,
    file generation, APIs, database operations.

workers/
    Long-running jobs that should not block the GUI.

utils/
    Small reusable helpers.
```

Never duplicate business rules inside UI classes when they already exist in services.

---

# 3. Layout rules

Use Qt layouts.

Prefer:

* QVBoxLayout
* QHBoxLayout
* QGridLayout
* QFormLayout
* QStackedLayout / QStackedWidget where appropriate

Avoid absolute positioning.

Do not use `setGeometry()` to build normal application layouts.

Avoid arbitrary fixed heights and widths.

Use fixed dimensions only when the component genuinely requires them.

Use:

* QSizePolicy
* stretch factors
* minimum sizes
* layout margins
* layout spacing

to control responsive behavior.

The interface must remain usable when resized.

---

# 4. Target desktop resolutions

At minimum, verify the UI at:

```text
1366 x 768
1920 x 1080
```

The application must remain usable at 1366x768 without:

* hidden primary actions
* unusable tables
* overlapping widgets
* clipped text
* excessive empty space
* horizontal scrolling for the whole application

Use scrolling inside specific content areas only when necessary.

---

# 5. Visual hierarchy

Every screen should make these questions obvious:

```text
Where am I?
What information am I seeing?
What should I do next?
What happened after my previous action?
Is something wrong?
How can I fix it?
```

Use a hierarchy such as:

```text
Page title
Short explanation
Primary information
Main content
Secondary information
Actions
Status / feedback
```

Do not make every element visually equally important.

---

# 6. Enterprise data application layout

For applications that process Excel, CSV, users, certificates, records or other structured information, prefer:

```text
┌─────────────────────────────────────────────────────────┐
│ Page title / context                                    │
├─────────────────────────────────────────────────────────┤
│ Input / selected file / process context                 │
├─────────────────────────────────────────────────────────┤
│ Summary cards / relevant metrics                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    MAIN DATA AREA                       │
│                                                         │
│                     QTableView                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Status / progress                        Primary action │
└─────────────────────────────────────────────────────────┘
```

The primary data area should normally receive most of the vertical space.

Do not restrict important tables with an unnecessarily small `maximumHeight`.

---

# 7. Tables

For non-trivial datasets prefer:

```python
QTableView
```

with:

```python
QAbstractTableModel
```

instead of manually populating large QTableWidget instances.

Especially prefer Model/View when using:

* Pandas DataFrames
* large Excel files
* filtering
* sorting
* editable records
* status visualization
* conditional formatting

Use QTableWidget only for genuinely small and simple datasets.

---

# 8. Table sizing

Tables showing business records are primary content.

Configure their headers intentionally.

Typical strategies:

```python
header = table.horizontalHeader()

header.setSectionResizeMode(
    QHeaderView.ResizeToContents
)
```

or selective behavior:

```python
header.setSectionResizeMode(
    important_column,
    QHeaderView.Stretch
)
```

Do not blindly stretch every column.

Avoid a table that shows only one record when more window space is available.

When the window grows, the table should normally grow.

Use appropriate:

```python
QSizePolicy.Expanding
```

behavior.

---

# 9. Table usability

Where relevant provide:

* sortable columns
* readable row heights
* clear headers
* alternating rows when helpful
* status indicators
* tooltips for truncated values
* filtering
* search
* row selection
* multi-selection only if the workflow needs it

Avoid excessive visual decoration.

Use color as supplemental information, not as the only way to communicate status.

Example status meanings:

```text
✓ Valid
⚠ Requires review
✕ Error
● Pending
```

Text should accompany ambiguous icons when needed.

---

# 10. Editable tables

Do not make the complete dataset editable by default.

Explicitly define editable columns.

For QAbstractTableModel implement editing through:

* flags()
* setData()
* dataChanged

Validate edited values before accepting them.

If invalid:

* explain the problem
* preserve the user's context
* do not silently discard input

Business validation should still live in the appropriate service layer.

---

# 11. Filtering and review workflows

For validation-oriented applications, support workflows such as:

```text
All
Valid
Warnings
Errors
Needs authorization
```

when useful.

Users should be able to quickly locate records requiring action.

Do not force users to manually inspect hundreds of rows to find problems.

---

# 12. Primary actions

Each screen should normally have one visually dominant primary action.

Examples:

```text
Process file
Validate records
Generate certificates
Confirm authorization
Export results
```

Secondary actions should be visually less prominent.

Avoid several equally dominant buttons.

---

# 13. Button text

Buttons should describe actions.

Prefer:

```text
Select file
Validate records
Generate certificates
Retry
Open output folder
```

Avoid vague labels such as:

```text
OK
Go
Execute
Continue
```

unless context makes their meaning completely obvious.

---

# 14. Destructive actions

Actions that:

* delete data
* overwrite files
* discard modifications
* permanently authorize exceptions
* replace output

should require an appropriate confirmation.

The confirmation should explain what will happen.

Avoid confirmation dialogs for harmless operations.

---

# 15. Dialog usage

Use dialogs for:

* confirmations
* short forms
* exception authorization
* critical errors
* focused decisions

Do not use modal dialogs for normal navigation.

Avoid chaining multiple modal dialogs.

Prefer inline feedback when the user can continue working without interruption.

---

# 16. Validation UX

Do not merely display:

```text
Invalid value
```

Explain:

```text
what is wrong
where it is wrong
what is expected
how it can be corrected
```

Example:

```text
Document number contains characters not allowed for this document type.
Review the value or request authorization from the process owner.
```

For business exceptions, visually distinguish:

```text
invalid
```

from:

```text
valid only with authorization
```

---

# 17. Status and feedback

Every meaningful action should produce visible feedback.

Possible states:

```text
Idle
Loading
Processing
Success
Warning
Error
Cancelled
```

Do not allow a button press to appear to do nothing.

Use:

* status labels
* banners
* progress bars
* disabled states
* notifications

depending on context.

---

# 18. Long-running operations

Never run expensive operations directly on the GUI thread.

Examples:

* reading large Excel files
* validating thousands of rows
* generating PDFs
* generating ZIP archives
* network requests
* large transformations

Use appropriate Qt concurrency patterns such as:

```text
QThread
QObject worker moved to QThread
QRunnable + QThreadPool
```

Keep QWidget creation and modification on the GUI thread.

---

# 19. Worker communication

Workers should communicate with the interface using signals.

Useful signals:

```text
started
progress
status
result
error
finished
```

Example conceptual workflow:

```text
User action
   ↓
Disable primary action
   ↓
Start worker
   ↓
Progress signal
   ↓
Update UI
   ↓
Result / error
   ↓
Restore controls
```

Always restore UI controls after success or failure.

---

# 20. Progress indicators

Use determinate progress when real progress can be calculated.

Example:

```text
Generating certificate 24 of 148
```

Use indeterminate progress when progress cannot be reliably measured.

Do not show fake percentages.

---

# 21. Application state

Prevent conflicting operations.

Example:

while generating outputs:

```text
Generate button: disabled
Select new file: disabled when replacing input would corrupt state
Cancel: enabled if cancellation is supported
```

Use explicit state management rather than scattered boolean checks when workflows become complex.

---

# 22. Signals and slots

Prefer signals and slots over tightly coupled direct calls between unrelated UI components.

Keep connections easy to trace.

Avoid creating duplicate signal connections when screens are reopened.

Use custom signals for meaningful domain events where appropriate.

Example:

```text
file_selected
validation_finished
authorization_requested
record_updated
generation_finished
```

---

# 23. QSS styling

Centralize application styles.

Prefer:

```text
ui/styles/app.qss
```

over repeating many inline `setStyleSheet()` calls.

Inline styles are acceptable only for small dynamic cases.

Use object names or properties for specific component states.

Example:

```python
button.setProperty("role", "primary")
```

and QSS:

```css
QPushButton[role="primary"] {
    font-weight: 600;
}
```

---

# 24. Design tokens

Where useful define consistent values for:

* spacing
* border radius
* typography hierarchy
* semantic colors
* widget heights

Do not invent arbitrary values independently for every widget.

Use a small spacing scale such as:

```text
4
8
12
16
24
32
```

rather than random spacing.

---

# 25. Color

Use color intentionally.

Semantic categories may include:

```text
Primary
Success
Warning
Error
Neutral
```

Ensure text remains readable.

Do not communicate errors or status only through color.

Consider the active palette and dark/light theme compatibility where practical.

---

# 26. Icons

Prefer Qt standard icons when they communicate the intended meaning adequately.

Use:

```python
QStyle.StandardPixmap
```

where appropriate.

Use custom icons when branding or clarity requires them.

Avoid inconsistent icon styles.

Do not use decorative icons everywhere.

---

# 27. Typography

Maintain a small visual hierarchy.

Typical roles:

```text
Application/page title
Section title
Body
Supporting text
Table content
```

Avoid many unrelated font sizes.

Do not rely on tiny text to fit more content.

---

# 28. Cards and containers

Use cards or framed sections only when they help group related information.

Do not place every widget inside a card.

Avoid excessive borders and nested frames.

Whitespace and alignment should provide most of the structure.

---

# 29. Navigation

For small applications:

```text
QStackedWidget
```

with a clear sidebar or navigation bar can be appropriate.

Navigation should:

* show the current page
* preserve context where useful
* avoid opening unnecessary separate windows
* keep primary workflows predictable

Do not implement browser-style navigation unless required.

---

# 30. Application workflow

For data-processing enterprise applications prefer an explicit flow such as:

```text
1. Select input
2. Review imported information
3. Validate
4. Resolve warnings / authorize exceptions
5. Generate
6. Review results
```

The UI should communicate the current stage.

Users should not need to memorize the process.

---

# 31. Empty states

Do not display blank tables without explanation.

Example:

```text
No file loaded.

Select an Excel file to begin.
```

When filtering returns nothing:

```text
No records match the current filter.
```

Empty states should explain the next available action.

---

# 32. Error states

Do not expose raw Python exceptions to normal users.

Bad:

```text
KeyError: 'Documento'
```

Better:

```text
The selected file does not contain the required "Documento" column.
Check the template and try again.
```

Log technical details separately when useful.

---

# 33. Success states

Clearly communicate successful completion.

Example:

```text
148 certificates generated successfully.
Output folder:
C:\...\certificados_2026-08-14
```

Provide useful next actions:

```text
Open folder
Generate ZIP
Process another file
```

---

# 34. QSettings

Use QSettings for stable user preferences when beneficial.

Potential values:

* window geometry
* window state
* last input folder
* last output folder
* table column widths
* splitter position
* UI preferences

Do not store sensitive credentials in QSettings unless appropriately protected.

---

# 35. Qt Designer

Qt Designer may be used when it improves development speed.

If `.ui` files are used:

* keep business logic outside generated UI files
* do not manually edit generated Python output if regeneration will overwrite it
* establish a consistent loading/generation workflow

Programmatic layouts are equally acceptable.

Choose based on project maintainability.

---

# 36. Accessibility

Where practical:

* maintain readable contrast
* support keyboard navigation
* set sensible tab order
* give controls clear labels
* provide accessible names for icon-only controls
* avoid tiny click targets
* avoid color-only communication

Standard Qt widgets are preferred because they provide useful native accessibility behavior.

---

# 37. Keyboard behavior

Common interactions should behave predictably.

Examples:

```text
Enter → appropriate primary action where safe
Escape → close non-destructive dialog
Ctrl+F → search when a searchable table is central
Ctrl+O → open/select input when appropriate
```

Do not add shortcuts that conflict with standard desktop expectations.

---

# 38. File selection

When selecting files:

* use QFileDialog
* apply useful file filters
* remember the previous directory when appropriate
* show the selected filename
* validate file type/content
* allow reselection

Example filter:

```text
Excel files (*.xlsx *.xls)
```

Do not rely only on extension validation when file content matters.

---

# 39. Output generation

Before generating files clearly show:

```text
what will be generated
where it will be saved
whether anything will be overwritten
whether unresolved warnings remain
```

After generation show:

```text
what was generated
where it was saved
whether anything failed
```

---

# 40. Authorization workflows

When a business rule allows exceptions with human authorization:

Do not silently bypass the rule.

Represent at least three conceptual states:

```text
VALID
REQUIRES_AUTHORIZATION
INVALID
```

For authorization capture relevant information where required, such as:

```text
record
exception reason
authorized by
timestamp
optional comment
```

UI behavior should make authorized exceptions clearly distinguishable from ordinary valid records.

Authorization logic belongs in services/domain logic, not purely in widgets.

---

# 41. Reusable widgets

Create reusable widgets when a visual or interaction pattern appears repeatedly.

Good candidates:

```text
StatusBanner
MetricCard
FileSelector
FilterBar
EmptyState
AuthorizationBadge
ProgressPanel
```

Do not create abstractions for components used once without clear benefit.

---

# 42. Avoid overengineering

Prefer standard Qt functionality.

Do not introduce:

* large UI frameworks
* unnecessary third-party dependencies
* custom painting
* complex animation systems

unless the project genuinely benefits.

PySide6 + Qt Widgets + QSS should be the default stack.

---

# 43. Third-party UI libraries

Before adding a library such as a Fluent or Material widget package:

1. verify compatibility with the installed PySide6 version
2. inspect license implications
3. evaluate packaging impact
4. evaluate maintenance risk
5. determine whether native Qt + QSS can solve the problem

Do not add a UI dependency only to improve appearance.

---

# 44. Packaging awareness

Remember that the application may run as a packaged executable.

When referencing assets:

* do not assume current working directory
* use robust resource paths
* account for PyInstaller or equivalent packaging
* verify QSS files and icons are bundled

UI code that works only from the source directory is incomplete.

---

# 45. Existing executable behavior

When a UI bug appears only after packaging:

inspect:

* display DPI
* screen resolution
* QSizePolicy
* fixed sizes
* layout stretch
* fonts
* resource paths
* platform-specific style behavior

Do not immediately assume the packaging tool caused the visual defect.

---

# 46. High DPI

Where relevant ensure the interface remains usable with Windows display scaling such as:

```text
100%
125%
150%
```

Avoid layouts that only work because text has a specific pixel size.

---

# 47. UX review before implementation

When asked to substantially improve a view:

First explain or internally determine:

```text
Current problem
User goal
Main task
Information hierarchy
Required components
Proposed layout
State transitions
```

Then implement.

Do not begin by randomly changing QSS.

---

# 48. UI code review

When reviewing a PySide6 interface, explicitly check for:

```text
fixed sizes
setGeometry()
deep nested layouts
duplicate styles
blocking operations
huge QWidget classes
business logic inside UI
tiny tables
unclear actions
missing feedback
raw exceptions
poor empty states
duplicate signals
```

Prioritize issues by user impact.

---

# 49. Incremental refactoring

For an existing working application:

Prefer:

```text
1. fix layout behavior
2. fix sizing
3. improve information hierarchy
4. improve feedback states
5. extract reusable widgets if justified
6. separate business logic where necessary
7. polish styling
```

Do not start with a complete rewrite.

---

# 50. Testing checklist

Before considering a PySide6 view finished verify:

* [ ] Window remains usable at 1366x768.
* [ ] Window works at 1920x1080.
* [ ] Main content expands when resized.
* [ ] No important widget relies on arbitrary fixed coordinates.
* [ ] Important text is not clipped.
* [ ] Primary action is obvious.
* [ ] Secondary actions are visually secondary.
* [ ] Tables show multiple rows when space exists.
* [ ] Table column sizing is intentional.
* [ ] Large datasets use an appropriate Model/View architecture.
* [ ] Loading operations do not freeze the interface.
* [ ] Progress/status feedback exists for long operations.
* [ ] Error messages are understandable to non-programmers.
* [ ] Business logic is not unnecessarily embedded in QWidget classes.
* [ ] Styles are reasonably centralized.
* [ ] Empty states explain what to do next.
* [ ] Success states explain what happened.
* [ ] Destructive actions are confirmed.
* [ ] Exception authorization is explicit.
* [ ] Keyboard navigation remains usable.
* [ ] Packaged executable behavior has been considered.
* [ ] Existing behavior outside the requested UI change has not been broken.

---

# 51. When modifying an existing application

Before editing files:

1. Inspect relevant views.
2. Identify the root cause.
3. Identify dependencies.
4. Describe the minimal change when useful.
5. Implement.
6. Run relevant tests.
7. Launch or validate the UI when possible.
8. Inspect resulting behavior.
9. Fix regressions.
10. Summarize changed files and behavior.

Do not claim the UI is fixed merely because the code compiles.

---

# 52. User experience principle

Optimize the interface around the user's workflow rather than around the internal implementation.

The user should not need to understand:

* DataFrames
* Python exceptions
* background workers
* file-processing internals
* Qt architecture

to successfully use the application.

The application should explain itself through clear states, actions and feedback.
