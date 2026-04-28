# User Guide

## Applications

The Applications tab lists all your recorded job applications in a table. Click **Add** to open the application form and record a new entry.

**Required fields:** Company, Role Title, Application Date, Phase, Status, Employment Type, Category, and Source.

**Phase vs Status — what is the difference?**
*Phase* describes where you are in the hiring process — Applied, Final Stage, Withdrawn, or Offer. *Status* describes the current state or sub-step within a phase — for example, Reviewing, Interview #1, Interview #2, Testing, Rejected, or Ghosted. You set the phase to reflect your milestone in the process, and the status to reflect the current activity or outcome. An application has both set at all times.

**Location.** The Location field accepts free text (for example, "Berlin, Germany" or "Remote – UK"). As you type, the field suggests values from your other applications. Click the **+** button to save the current value as a permanent suggestion without leaving the form.

**Priority** is a score from 1 to 5 that you assign to reflect how much you want the role. 1 is the lowest priority and 5 is the highest. Use it to sort or filter at a glance.

**Sorting and reordering columns.** Click any column header to sort the table by that column. Click again to reverse the sort. Drag a column header left or right to reorder the columns to your preference.

**Editing and deleting.** Select a row and click **Edit**, or double-click the row. Click **Delete** to remove it permanently. The app will ask you to confirm before deleting.

**Filtering.** The toolbar above the table contains a search box and three filter dropdowns: Status, Phase, and Category. All active filters apply at the same time. Select "All" in any dropdown to clear that filter. The search box matches against company name and role title.

**Adding new sources or categories inline.** In the application form, click the **+** button next to the Source or Category field to add a new value without leaving the form.

## Companies

The Companies tab manages the organisations you have applied to. Click **Add** to create a new company record. Double-click any row to open that company's edit form directly.

**Contact details.** Each company can store a contact name, email address, and phone number (with a separate field for the country prefix, such as +44). These fields are optional and are there for your reference only.

**Industry.** The Industry field suggests existing values as you type. Click the **+** button adjacent to the field to confirm the typed value as a new industry — it becomes available for future suggestions after the company is saved.

**Platform links.** You can attach multiple web links to a company — for example, a LinkedIn page, a Glassdoor profile, and a direct careers page. Platforms are drawn from the reference list managed in Settings. If you need a platform that is not listed, choose **Other…** from the dropdown and type a custom label; it will be added to the platform list automatically. Click **+ Add link**, choose the platform, and paste the URL. Click × to remove a link. Links are saved when you click OK.

**Sorting and reordering columns** work the same way as in the Applications tab: click a header to sort, drag to reorder.

The app prevents duplicate company names and will not allow you to delete a company that still has applications linked to it.

## Analytics

The Analytics tab displays live charts and summary figures derived from your application data: total applications, active pipeline count, response rate, and average priority score. The funnel chart shows how applications progress through the key pipeline stages. Click **Refresh** to update all charts and figures after making changes in other tabs.

## Export

The Export tab lets you generate formatted reports from your application data. Select a report type from the **Type** dropdown — Application Activity Table, Application Sheet, or Analytics Summary — configure the **From** and **To** date range and any other filters, then click **Export…** to choose an output directory and the file formats you want: PDF, Word, ODT, or LaTeX. When you choose the LaTeX format, the app saves a `.tex` file to your chosen folder; to compile it to a PDF you will need TexMaker installed separately (see the [installation guide](installation.md)). The other formats (PDF, Word, ODT) are generated directly without any additional software. The status label at the bottom of the tab confirms the output path on success, or shows the error in red if something goes wrong.

## Settings

The Settings tab lets you manage the reference values used throughout the application. The left panel lists the available tables: **Phases**, **Statuses**, Categories, Employment Types, Sources, Work Modes, and Currencies. Click any table name to view and edit its rows in the right panel.

- **Add** — type a new label and click Add to insert it.
- **Edit** — select a row and click Edit to rename it.
- **Remove** — select a row and click Remove to hide it from all selection fields (soft-delete: the row is kept in the database and any existing records that used it are preserved intact). Clicking Remove on an already-removed row reactivates it.
- **Move Up / Move Down** — reorder entries within a table.

Changes to Phases, Statuses, Categories, and Sources are reflected immediately in the filter dropdowns on the Applications tab without restarting the app.
