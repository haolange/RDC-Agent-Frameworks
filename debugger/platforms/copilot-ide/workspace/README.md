# Workspace Directory

This directory serves as the working area for the Copilot IDE platform.

## Usage

1. Place your `.rdc` capture files here for analysis
2. Store fix references and related resources
3. Use this space for temporary files during debugging sessions

## Rules

- Do not commit large binary files to version control
- Clean up temporary files after debugging sessions
- Ensure `.rdc` files have corresponding fix references before processing

## Workflow

1. Copy your `.rdc` capture file to this directory
2. Ensure you have a `strict_ready` fix reference
3. Run the validation: `python common/config/validate_binding.py --strict`
4. Begin your debugging session
