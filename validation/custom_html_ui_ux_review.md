# custom.html UI/UX Review: Sorting, Hash Collision, Pigeonhole

Scope: `services/api/app/skills/custom_html_app_skill.py` and `services/api/app/agents/orchestrator_agent.py`.

Constraint: this is a parallel review artifact only. No production code was changed.

## 1. Sorting Demo Acceptance Standard

The sorting demo should be judged by visible learning behavior, not by the mere presence of `<script>` or buttons.

Required first-frame elements:

- A non-empty array visualization is visible before any click: 8 to 12 vertical bars or cells, each with readable values.
- The stage has stable height and does not collapse while scripts are loading.
- The current algorithm name, current step explanation, comparison count, swap/move count, and sorted-region indicator are visible.
- Buttons are algorithm-specific: bubble sort, insertion sort, single step, reset. Disabled/playing state should be visible while autoplay runs.
- Color semantics are explicit and consistent: compare pair, moved/swapped item, sorted/finalized region, unsorted region.

Required interactions:

- Clicking bubble sort immediately changes at least one of: highlighted pair, step text, comparison counter, bar positions, sorted-region marker.
- Clicking insertion sort shows a different mental model from bubble sort: left-side sorted prefix, key element, shifts/moves, insertion point.
- Clicking single step advances exactly one queued algorithm step. If no algorithm is selected, the message must explain how to begin.
- Clicking reset produces a visibly different array and resets counters to zero.
- Autoplay must terminate with all bars/cells marked sorted and no timer continuing in the background.

Suggested visual design target:

- Treat this as an algorithm workbench, not an infographic card. Use a dense horizontal control rail, a large stage, and a compact metrics panel.
- For algorithm teaching, the memorable element should be the moving comparison focus: a bracket, cursor, or scan line that makes the algorithm's scan direction obvious.
- Avoid generic "LearnForge sandbox" branding as the highest-salience badge; the algorithm state should be more prominent than platform status.

Minimum automated acceptance:

- DOM assertion after render: `.lf-sort-stage .lf-bar` count is at least 8.
- DOM assertion after clicking `data-action="bubble"`: `data-metric="compare"` increases above 0 and `.lf-bar.compare` appears.
- DOM assertion after clicking `data-action="reset"`: bar value sequence changes and counters return to 0.
- Screenshot assertion: stage is not blank and bars occupy meaningful vertical space.

## 2. Hash Collision / Pigeonhole Should Become Topic Templates

The current generic concept fallback is not enough for "哈希冲突" or "抽屉原理" because those topics require visible mapping pressure: many inputs competing for fewer buckets.

Hash collision template:

- Use keys/cards on the left, buckets/slots on the right, and animated arrows from `hash(key) % bucket_count`.
- Controls should be semantically named: add key, bucket count, hash rule, next insertion, reset.
- Visible state should include load factor, collision count, current hash expression, bucket chain/open-addressing probe sequence, and the chosen collision strategy.
- At least two strategies should be directly switchable: separate chaining and linear probing.
- The teaching text should say "不同 key 可能映射到同一个 bucket" and then show that collision in the same bucket, not just mention it in the title.

Pigeonhole / drawer principle template:

- Use pigeons/items and drawers/boxes with an explicit `n items -> m drawers` count.
- Controls should be semantically named: items, drawers, distribute, worst case, reset.
- Visible state should include the threshold `floor((n - 1) / m) + 1`, max occupancy, and which drawer proves the principle.
- The demo should deliberately create the guaranteed-overlap case when `items > drawers`, then highlight the overcrowded drawer.
- The explanation should connect the visual result to the theorem: when more objects than boxes are assigned, at least one box contains two or more objects.

Implementation direction:

- Replace the single generic `concept_demo_widget(topic)` fallback with a dispatcher:
  - `hash_collision_demo_widget` for `哈希|hash|冲突|bucket|散列`.
  - `pigeonhole_demo_widget` for `抽屉|鸽巢|pigeonhole|drawer`.
  - `concept_demo_widget` only for topics without a known interaction model.
- Do the same at the orchestrator contract fallback layer, so Hermes failure does not bypass the topic-specific widgets.
- Keep all templates self-contained, inline-script only, and compatible with the existing iframe CSP and `allow-scripts` sandbox.

## 3. Concrete Risk Points In Current Implementation

`custom_html_app_skill.py`

- Lines 44-227: `sorting_demo_widget` is topic-specific and executable, but the visual pass/fail contract is implicit. Tests currently check HTML markers, not that the stage has visible bars or that clicks mutate state.
- Lines 49 and 234: templates use `Inter, ui-sans-serif, system-ui`, which makes fallback widgets visually generic and inconsistent with the product's more distinctive canvas styling.
- Lines 82-89 and 115-123: the sorting stage is initially empty in static HTML and only gets bars after script execution. If script activation fails or is delayed, the user sees a blank stage.
- Lines 100-224: sorting relies entirely on inline script. This is acceptable for the sandbox, but it means blank-state prevention should be built into static markup or verified via browser tests.
- Lines 229-293: `concept_demo_widget` is a generic "直觉图景 / 关键变量 / 检查理解" card. It does not contain hash buckets, collision chains, drawers, occupancy counts, or theorem-specific interactions.
- Lines 321-327: `needs_interactive_fallback` treats broad words like `animation`, `stage`, and `chart` as blank-stage signals. Because it scans `combined` raw/original/sanitized HTML, a valid custom widget that merely contains these terms can be replaced unnecessarily.
- Lines 329-333: `fallback_widget` only has a sorting recognizer. Hash collision and pigeonhole topics always fall through to the generic concept demo.
- Lines 345-350: fallback selection happens after sanitization. If sanitization removes a script but leaves inert controls, the only available topic-specific rescue today is sorting.

`orchestrator_agent.py`

- Lines 143-148: interactive demos are routed to native app types only for physics and gradient descent. Algorithms, hash tables, and pigeonhole demos remain generic `custom.html` fallback candidates.
- Lines 338-394: `fallback_interactive_html` is a generic variable A / variable B / observation-step animation. It cannot express hash collision or pigeonhole because no visible entity maps into a constrained bucket/drawer set.
- Lines 368-373: control labels `变量 A`, `变量 B`, and `观察步数` are the exact source of the "学习主题互动演示" feeling. They are not domain vocabulary.
- Lines 414-417: `fallback_app_for_type` uses the generic interactive fallback for all `custom.html` interactive-demo contract failures, so Hermes failure can erase topic specificity.
- Lines 667-669: generation suggestion recognizes `算法` and `排序`, but not `哈希`, `散列`, `冲突`, `抽屉`, or `鸽巢`; these topics may not consistently request a topic-specific interactive demo unless extracted elsewhere.

Frontend renderer context:

- `apps/web/src/features/custom-html-app/CustomHtmlAppRenderer.tsx` lines 37-48 inject HTML, then replays scripts by replacing script nodes. This makes inline scripts viable, but it also means the static pre-script DOM must not look empty.
- Renderer lines 101-120 post the widget more than once around iframe readiness. Widgets should tolerate repeated initialization or ensure script state is scoped to the widget root.
- `widgetParser.ts` lines 43-55 strips scripts for preview. If preview is visible before finalize, a script-only stage will appear blank until finalize completes.

Current validation gap:

- `services/api/tests/test_agents_and_skills.py` lines 382-397 checks sorting fallback has the widget marker, `data-action="bubble"`, and `<script>`, but not visible bars or click behavior.
- Lines 400-413 explicitly accepts `concept-demo` for `哈希表冲突互动演示`, which locks in the current generic behavior instead of catching it.
- Lines 232-250 explicitly accepts orchestrator generic range controls for hash collision fallback, including `data-role="a"`.

## Recommended Stop Condition For Main Fix

- Sorting custom.html screenshot shows non-empty bars before interaction and after running one algorithm.
- Hash collision custom.html screenshot shows keys mapping into buckets with at least one collision highlighted.
- Pigeonhole custom.html screenshot shows items distributed into fewer drawers with the overcrowded drawer highlighted.
- Targeted tests no longer assert `data-role="a"` or generic `concept-demo` for hash collision; they assert topic-specific DOM markers and visible state changes instead.
