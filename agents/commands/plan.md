
# Implementation Plan Guidelines

Create an implementation the user prompt.

An effective implementation plan outlines specific goals, actionable steps, assigned responsibilities, timelines, and resource allocation to transition a project from planning to execution. Key guidelines include defining SMART objectives, conducting risk assessments, establishing milestones, and maintaining clear communication with stakeholders.

## Variables
workspace_id = {{workspace_id}}
base_dir = {{base_dir}}

## Format & Conventions

- The plan describes how the implementation should be done.
- The plan is in **markdown format**.
- The plan must include **step-by-step instructions**.
- Consider the best practices for each language for maintainability.
- List relevant **references to other files**.
- Include the original prompt in the plan as: `User prompt: user-prompt`.
- IMPORTANT: If the feature includes UI components or user interactions:
  - Add a task in the `Step by Step Tasks` section to create a separate E2E test file in `{{base_dir}}/agents/commands/e2e/test_<descriptive_name>.md` based on examples in that directory
  - Add E2E test validation to your Validation Commands section
  - IMPORTANT: When you fill out the `Plan Format: Relevant Files` section, add an instruction to read `{{base_dir}}/agents/commands/test_e2e.md`, and `agents/commands/e2e/test_basic_node_server.md` to understand how to create an E2E test file. List your new E2E test file to the `Plan Format: New Files` section.
  - To be clear, we're not creating a new E2E test file, we're creating a task to create a new E2E test file in the `Plan Format` below
- IMPORTANT: Save the plan in `{{base_dir}}/specs/{{workspace_id}}/PLAN.md`

## Steps for Developing an Implementation Plan

1. **Define Goals**: Establish clear, measurable objectives (SMART).
2. **Conduct Research**: Assess the current environment and potential bottlenecks.
3. **Assign Tasks**: Detail necessary actions and assign owners.
5. **Build Timeline**: Map out dependencies and milestones.
6. **Develop Contingency Measures**: Plan for potential risks.
7. **Monitor and Evaluate**: Regularly track progress against the plan.

## Best Practices

- Ensure the plan is **actionable**, **realistic**, and tailored to the organization's (or project's) needs.
- Secure buy-in from all key stakeholders early in the process.
- Keep the document **accessible** and use **clear, simple language**.

## Report
- Follow the Plan format
- Return only the generated plan.

## Plan format

```md
# Prompt: <prompt>

## Description
<describe the request in detail, including its purpose and value to users>

## User Story
As a <type of user>
I want to <action/goal>
So that <benefit/value>

## Problem Statement
<clearly define the specific problem or opportunity this feature addresses>

## Solution Statement
<describe the proposed solution approach and how it solves the problem>

## Relevant Files
Use these files to implement the feature:

<find and list the files that are relevant to the feature describe why they are relevant in bullet points. If there are new files that need to be created to implement the feature, list them in an h3 'New Files' section.>

## Implementation Plan
### Phase 1: Foundation
<describe the foundational work needed before implementing the main feature>

### Phase 2: Core Implementation
<describe the main implementation work for the feature>

### Phase 3: Integration
<describe how the feature will integrate with existing functionality>

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

<list step by step tasks as h3 headers plus bullet points. use as many h3 headers as needed to implement the feature. Order matters, start with the foundational shared changes required then move on to the specific implementation. Include creating tests throughout the implementation process. Include commands needed to install dependencies.>

<If the feature affects UI, include a task to create a E2E test file (like `agents/commands/e2e/test_basic_node_server.md`) as one of your early tasks. That e2e test should validate the feature works as expected, be specific with the steps to demonstrate the new functionality. We want the minimal set of steps to validate the feature works as expected and screen shots to prove it if possible.>

## Testing Strategy
### Unit Tests
<describe unit tests needed for the feature>

### Edge Cases
<list edge cases that need to be tested>

## Acceptance Criteria
<list specific, measurable criteria that must be met for the feature to be considered complete>

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

<list commands you'll use to validate with 100% confidence the feature is implemented correctly with zero regressions. every command must execute without errors so be specific about what you want to run to validate the feature works as expected. Include commands to test the feature end-to-end.>

<If you created an E2E test, include the following validation step: `Read .cursor/commands/test_e2e.md`, then read and execute your new E2E `.cursor/commands/e2e/test_<descriptive_name>.md` test file to validate this functionality works.>

## Notes
<optionally list any additional notes, future considerations, or context that are relevant to the feature that will be helpful to the developer>

```

## User prompt
{{prompt}}
