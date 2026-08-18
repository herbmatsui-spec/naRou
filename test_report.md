# Test Report Configuration

## Test Report Settings

### Output Format
- Format: Markdown
- Template: Custom
- Sections:
  - Summary
  - Passed Tests
  - Failed Tests
  - Skipped Tests
  - Coverage Summary
  - Performance Metrics

### Report Generation
- Trigger: After test execution
- Location: test_report.md
- Include: Timestamps, Git commit, Environment info

### Distribution
- Artifact: Upload to CI/CD
- Notify: On failure