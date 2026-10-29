# Contributing to the pragmaticBIM Reference

The Reference gets better through practice. Every project shows what works, what is missing, and what is superfluous.

## Feedback without Git

Write to [info@abstract.build](mailto:info@abstract.build) with the subject `[Referenz Feedback]`. A photo of an annotated book page is enough.

## Issues

Open an issue and describe the problem briefly: element, attribute, workflow, and project context.

## Pull requests

1. Fork the repository or create a branch.
2. Edit the affected YAML files: element definitions, attributes, value lists, or workflow descriptions.
3. Run the checks: `python -m pytest`.
4. Commit with a clear reason: **what** changes and **why**, ideally with a reference to the workflow.
5. Open a pull request into `development`. Small data changes from trusted authors can merge automatically, everything else goes to the maintainer. See [MERGE_POLICY.md](MERGE_POLICY.md).

You can also edit in the [web application](https://elementplan.pragmaticbim.ch): changes to the Reference are submitted as pull requests to this repository.

## What makes a good change

- a concrete workflow instead of an abstract wish for completeness
- a small, traceable change
- a reason from practice: what was unclear, wrong, or missing?
- respect the existing structure: goal → workflow → element → attribute

Keep requirements lean: no requirement without a benefit, as little as possible, as much as necessary.

## Writing style

Descriptions are maintained in German, English, French, and Italian. The rules under [`.cursor/rules/`](.cursor/rules/) describe the structure of element, attribute, workflow, document, and usage scenario descriptions and the style per language.

## License

By contributing you agree that your contribution is published under the [PragmaticBIM Standard License](LICENSE).
