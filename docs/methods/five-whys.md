# Five Whys

Use this after a concrete failure, regression, or surprising observation to distinguish the symptom from the mechanism that produced it.

The number five is a prompt for depth, not a quota.

## Procedure

1. **What symptom was observed?** Record the smallest reliable evidence first.
2. Ask **why did this happen?** and answer with an observable mechanism, not a guess.
3. Ask why that condition existed. Continue while each answer is supported and moves toward a cause that can be changed.
4. If the evidence branches into multiple causes, branch the analysis. Do not force one theatrical chain of five answers.
5. Fix the smallest responsible layer, then verify the exact **postcondition** or authoritative readback.

## Stop rules

- Stop when the next answer would be speculation; gather evidence instead.
- Stop when the cause is actionable and explains the observed symptom.
- Do not turn the method into blame. Prefer system, interface, process, configuration, and boundary causes that can be tested.
- A disappearing symptom is not proof that the root cause was fixed; verify the postcondition separately.

## Relationship to the Feynman checkpoint

Use the **Feynman checkpoint** to ask whether a proposed design is carrying unnecessary machinery.

Use **Five Whys** when something already failed and the task is to find the responsible mechanism.
