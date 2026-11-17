# Diversity statement

The people who will use this tool differ in programming experience, in how they operate a computer and in the language they are most comfortable reading. The tool must not require a developer's background, a mouse or perfect colour vision to complete a task.

## What the product does today

- **No programming required.** Pipelines are built from blocks, and each block's form is generated from its declared schema with labels and descriptions.
- **Errors that can be acted on.** A validation problem names the block and the field, and activating it moves focus to that field. Unsaved edits are kept ([#33](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/33)).
- **Keyboard and screen-reader path for error recovery.** Verified in Chrome with the accessibility tree: status changes are announced without stealing focus, and recovery works from the keyboard ([#80](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/80), [verification](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/blob/main/docs/testing/issue-33-validation-recovery.md)).
- **Status never shown by colour alone.** Run and block states carry text labels.

## Known limits

- Building a graph on the canvas still depends on pointer dragging. A keyboard alternative for connecting blocks is not implemented.
- The interface is English only. The partner is based in Quebec, so French interface text matters.
- No testing with assistive-technology users has taken place; the checks above were done by the team.

## Commitments

- New UI stories carry an accessibility acceptance criterion.
- A keyboard alternative for connecting blocks and French interface text are candidates for Release 2 and will be raised as issues.
- Feedback is collected without recording personal or demographic information.

## The team

Work is assigned by a published plan with a primary owner and a different reviewer for every item, so that no member is limited to documentation or review. See the per-person breakdown in the [iteration and release notes](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/wiki/Iteration-and-Release-Notes).
