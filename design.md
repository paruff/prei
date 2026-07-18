# Design: Remaining UX

### 1. Offer MAO visualization
Template: `templates/pipeline/offer_form.html` — add a CSS bar below MAO value:
```
MAO: $237,500  [████████░░]  95% of target
```

### 2. Portfolio equity dashboard
Template: `templates/dashboard.html` — add equity bar per property:
```
Property A: $120K equity / $300K value [████████████░░░░] 40%
```

### 3. Growth Areas seed
View: `system_status` already handles POST actions. Add `seed_growth_areas` action that calls `populate_growth_areas` management command logic via a service call.
