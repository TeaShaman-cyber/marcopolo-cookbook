# Feynman checkpoint

Use this before adding machinery to a design, review, or experiment.

The goal is not to make a system sound simple. The goal is to expose complexity that is not required by the problem.

## Five questions

1. **What is being tested or changed?**
2. **What changes?**
3. **What stays fixed?**
4. **Can the mechanism be explained in about five lines without introducing another abstraction?**
5. **What does PASS not prove?**

A useful answer should name concrete inputs, outputs, boundaries, and the narrow claim being tested.

## Stop rule

If the explanation needs a new conceptual layer that the task itself does not require, **stop and simplify** before implementation.

Do not remove complexity that protects a real invariant merely to make the explanation shorter. The checkpoint is an overengineering detector, not a substitute for evidence, tests, or verification.
