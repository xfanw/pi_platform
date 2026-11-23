# File Upload Filter Tabs Implementation

## Overview
Added clickable filter tabs ("Total Rows", "Ready", "Errors") to file upload preview pages with backend filtering support. By default, the "Errors" tab is shown.

## Features Implemented

### 1. Backend Filtering (Django Views)

#### Updated Files
- `count/app_views/input_batches.py` - `count_batch()` function
- `site_setting/app_views/counter_roster.py` - `counter_batch()` function

#### Implementation Details

Both views now:
1. Accept a `filter` query parameter from the URL (values: "all", "ready", "errors")
2. Default to "errors" if no parameter is provided
3. Query database to get filtered rows based on `is_valid` field:
   - `filter=all` → All rows
   - `filter=ready` → Only `is_valid=True` rows
   - `filter=errors` → Only `is_valid=False` rows
4. Calculate counts dynamically from database:
   - `total_count` - Total rows in batch
   - `ready_count` - Valid rows (ready for import)
   - `error_count` - Invalid rows (need fixes)

#### Code Example
```python
# Get filter parameter from request, default to 'errors'
filter_type = request.GET.get("filter", "errors").lower()
if filter_type not in ["all", "ready", "errors"]:
    filter_type = "errors"

# Get all rows and apply filter
all_rows = TempCountLoadDetail.objects.filter(batch=batch_ref).order_by("id")

if filter_type == "ready":
    rows = all_rows.filter(is_valid=True)
elif filter_type == "errors":
    rows = all_rows.filter(is_valid=False)
else:  # "all"
    rows = all_rows

# Pass to template
context["rows"] = rows
context["filter_type"] = filter_type
context["total_count"] = all_rows.count()
context["ready_count"] = all_rows.filter(is_valid=True).count()
context["error_count"] = all_rows.filter(is_valid=False).count()
```

### 2. Frontend (HTML Templates)

#### Updated Files
- `count/templates/count/batch_detail.html`
- `site_setting/templates/site_setting/counter_batch.html`

#### Changes Made

1. **Clickable KPI Cards**: 
   - Wrapped each KPI card in an `<a>` tag linking to `?filter=all|ready|errors`
   - Each link preserves the batch_id in the URL

2. **Active Tab Highlighting**:
   - Added conditional `active` class to match current `filter_type`
   - Styled with blue border and shadow effect

3. **Dynamic Counts**:
   - Displays actual counts from backend: `{{ total_count }}`, `{{ ready_count }}`, `{{ error_count }}`
   - No hardcoding of batch properties

#### HTML Structure
```html
<div class="cards bulk-preview-kpis">
  <a href="?filter=all" class="kpi-link">
    <div class="kpi cool {% if filter_type == 'all' %}active{% endif %}">
      <span>Total Rows</span>
      <strong class='fw-bold'> {{ total_count }}</strong>
    </div>
  </a>
  <a href="?filter=ready" class="kpi-link">
    <div class="kpi good {% if filter_type == 'ready' %}active{% endif %}">
      <span>Ready</span>
      <strong class='fw-bold'> {{ ready_count }}</strong>
    </div>
  </a>
  <a href="?filter=errors" class="kpi-link">
    <div class="kpi bad {% if filter_type == 'errors' %}active{% endif %}">
      <span>Errors</span>
      <strong class="{% if error_count %}negative{% endif %} fw-bold"> {{ error_count }}</strong>
    </div>
  </a>
</div>
```

### 3. Styling

Added inline CSS to both templates:
```css
.kpi-link {
  text-decoration: none;
  color: inherit;
}
.kpi-link .kpi.active {
  border: 2px solid #0066cc;
  box-shadow: 0 0 8px rgba(0, 102, 204, 0.3);
}
.kpi-link .kpi:hover {
  cursor: pointer;
  opacity: 0.9;
}
```

## User Experience Flow

1. **Upload File**
   - User uploads Excel file
   - System validates and creates batch preview
   - Page loads with "Errors" tab active by default
   - Only error rows displayed

2. **Review Errors Tab** (Default)
   - `URL: /count/count_batch/123` (or with `?filter=errors`)
   - Shows only rows with `is_valid=False`
   - User can fix these in Excel and re-upload

3. **Click "Total Rows"**
   - `URL: /count/count_batch/123?filter=all`
   - Shows all rows with their validation status
   - Blue border highlights active tab

4. **Click "Ready"**
   - `URL: /count/count_batch/123?filter=ready`
   - Shows only valid rows (`is_valid=True`)
   - Ready for import

5. **Back to Errors**
   - `URL: /count/count_batch/123?filter=errors`
   - Returns to error view
   - Blue border switches to Errors card

## URL Examples

| Scenario | URL |
|----------|-----|
| Default (Errors) | `/count/count_batch/123/` |
| All rows | `/count/count_batch/123/?filter=all` |
| Ready rows | `/count/count_batch/123/?filter=ready` |
| Error rows | `/count/count_batch/123/?filter=errors` |
| Counter batch (all) | `/site_setting/counter_batch/456/?filter=all` |

## Database Queries

The implementation performs efficient database queries:
1. Single query for `all_rows` with `.order_by("id")`
2. If needed, filtered query for `rows` with `.filter(is_valid=True|False)`
3. Aggregation using `.count()` for the three count values

This avoids N+1 query problems and efficiently filters large batches.

## Backward Compatibility

- If `filter` parameter is missing or invalid, defaults to "errors"
- Existing bookmarks and links without the parameter still work
- All existing functionality preserved (Confirm Import button, error messages, etc.)

## Testing Checklist

- [ ] Upload count file with errors → Errors tab shows by default
- [ ] Click "Total Rows" → All rows display, tab highlights
- [ ] Click "Ready" → Only valid rows display, tab highlights
- [ ] Click "Errors" → Only invalid rows display, tab highlights
- [ ] Counter roster upload → Same filtering works
- [ ] No errors parameter → Defaults to errors view
- [ ] Invalid filter value → Defaults to errors view
- [ ] Confirm import button → Still works from any filter view

## Files Changed Summary

| File | Changes |
|------|---------|
| `count/app_views/input_batches.py` | Added filter logic to `count_batch()` |
| `site_setting/app_views/counter_roster.py` | Added filter logic to `counter_batch()` |
| `count/templates/count/batch_detail.html` | Made KPI cards clickable, added styling |
| `site_setting/templates/site_setting/counter_batch.html` | Made KPI cards clickable, added styling |

No migrations required. No model changes. Pure business logic enhancement.
