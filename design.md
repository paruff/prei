# Design: P0 — CRM Kanban + Data Health
# Written: 2026-07-19

---

## 1. Kanban Board

### 1.1 URL + Template

- URL: `/pipeline/kanban/` (new view)
- Template: `templates/pipeline/kanban.html` (existing, needs wiring)
- CSS: existing `static/css/pipeline.css`
- JS: SortableJS via CDN for drag-and-drop

### 1.2 Backend API

New endpoint: `POST /pipeline/<id>/transition/`

```python
def transition_stage(request, pipeline_id):
    prop = get_object_or_404(PipelineProperty, id=pipeline_id)
    new_stage = request.POST["stage"]
    validate_stage_transition(prop.current_stage, new_stage)  # forward-only
    prop.current_stage = new_stage
    prop.save()
    return JsonResponse({"status": "ok", "new_stage": new_stage})
```

### 1.3 Stage Rules

```
DISCOVERED → SCREENING → UNDERWRITING → OFFER → DUE_DILIGENCE → CLOSING → ACQUIRED
```

Forward-only. No skipping. No backward movement (use admin to fix mistakes).

### 1.4 JavaScript (vanilla + SortableJS)

```javascript
// SortableJS makes columns draggable
new Sortable(column, {
  group: 'pipeline',
  onEnd: function(evt) {
    const card = evt.item;
    const newStage = evt.to.dataset.stage;
    const pipelineId = card.dataset.id;
    fetch(`/pipeline/${pipelineId}/transition/`, {
      method: 'POST',
      body: new URLSearchParams({stage: newStage}),
    });
  }
});
```

---

## 2. Data Source Health Dashboard

### 2.1 Model

```python
class DataSourceHealth(models.Model):
    source_name = models.CharField(max_length=64, unique=True)
    last_run = models.DateTimeField(null=True)
    record_count = models.IntegerField(default=0)
    status = models.CharField(max_length=16, default="unknown")  # ok | error
    error_message = models.TextField(blank=True)
```

### 2.2 View Update

Update `system_status` view to query `DataSourceHealth` and pass to template.

### 2.3 Template

Health table under the existing counts section:
```html
<table class="data-source-health">
  <thead><tr><th>Source</th><th>Last Run</th><th>Records</th><th>Status</th></tr></thead>
  {{% for h in health %}}<tr>...</tr>{{% endfor %}}
</table>
```

---

## 3. File Changes

| File | Change | Purpose |
|---|---|---|
| `templates/pipeline/kanban.html` | Modified | Wire up SortableJS + stage columns |
| `core/views/__init__.py` | Modified | Add kanban view + transition API |
| `core/models/pipeline.py` | Modified | Add DataSourceHealth model |
| `core/views/__init__.py` | Modified | Update system_status with health data |
| `templates/pipeline/system_status.html` | Modified | Add health table |
| `core/urls.py` | Modified | Add /pipeline/kanban/ + transition URL |
| `static/js/kanban.js` | New | SortableJS drag-and-drop logic |
| `requirements.txt` | Modified | Add django-cors-headers (if needed for API) |
| `core/migrations/` | New | Migration for DataSourceHealth |
