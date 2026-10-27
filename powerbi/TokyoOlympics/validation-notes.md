# Validation methods

- **Live:** Desktop loaded the model; read-only DAX queries returned the saved
  `live-dax-evidence.json`. Every country and the aggregate/filter cases were
  independently reconciled against the CSV at tolerance 1e-12.
- **Local snapshot:** `source-validation.json` records the fixed CSV hash and
  reconciliation results. Running the repository validator repeats those checks
  against saved evidence, not against a newly refreshed Desktop session.
- **Visual:** Four actual Desktop page captures are in `previews/`. The final
  overview has ten medal leaders in descending total-medal order; the helper
  tooltip is blank outside the ranked set. Text and charts were inspected after
  loading the dataset. The project was saved with no unsaved changes.
- **Structural:** Microsoft's report-author CLI reported zero errors and one
  unavailable-public-schema warning for visualContainer 2.14.0 after Desktop
  upgraded the report definition. Other referenced schemas validated.
- **Heuristic limitation:** The plugin's generic unified offline review did not
  parse the BIM model's DAX measures (it expected TMDL), and its sensitivity scan
  treated visual/theme names such as `card` as model columns. Its automated
  governance/release labels are therefore not evidence of model validity or
  invalidity. Direct BIM inspection, real Desktop DAX and rendered report checks
  provide the validation used here. No enterprise sign-off or Service deployment
  is claimed.
