# Help and Tooltip Implementation Plan for Elona

## Objective
Make Elona more beginner-friendly by implementing clear help systems and contextual tooltips that explain game mechanics, controls, and UI elements.

## Target Areas
1. CLI Menu (main.py) - The initial system menu
2. Game Client (CLI and Web) - In-game help and tooltips
3. Web Interface (web_game_client.html) - Browser-based help and hover tooltips

## Detailed Implementation

### 1. CLI Menu Enhancement (main.py)
**Problem**: The initial menu lacks explanation of what each option does, which may confuse newcomers.
**Solution**:
- Add a help option (triggered by '?' or 'help' input) that displays:
  - Brief description of Elona Clone
  - Explanation of each menu option:
    1. Start the game (explore what this entails)
    2. Run economy simulation
    3. Run workflow orchestrator
    0. Exit
- Improve menu clarity by adding short descriptions next to each option (optional)

### 2. Game Help System Enhancement (ui_fx_systems.py)
**Problem**: While a help system exists, content could be more beginner-friendly with examples and clearer explanations.
**Solution**:
- Expand HelpSystem.SECTIONS with additional sections or enhanced content:
  - Section 1: Add more survival tips (e.g., managing hunger, light sources)
  - Section 2: Clarify key bindings with common alternatives (vi keys, numpad)
  - Section 3: Expand legend with more symbols (traps, doors, special tiles)
  - Section 4: Add explanations of core systems:
    * Hunger and nutrition
    * Karma and reputation
    * Faith and piety
    * Experience and leveling
    * Pet mechanics
- Consider adding a "First Steps" guide for absolute beginners

### 3. Web Interface Enhancement (web_game_client.html)
**Problem**: The help modal is basic and lacks comprehensive guidance. UI elements could benefit from hover tooltips.
**Solution**:
**Help Modal Content Improvement**:
- Expand the help modal with more detailed sections:
  * Getting Started: Character creation and initial goals
  * Combat Basics: How attacks work, damage types
  * Exploration: Mapping, lighting, trap detection
  * Economy: Gold, platinum, shopping, selling
  * Advanced: Wishes, debug console, modding
- Improve formatting with better spacing and icons
**Hover Tooltips**:
- Add `title` attributes to status bars (HP, MP, gold) showing current/max values
- Add tooltips to control buttons explaining their function and keyboard shortcut
- Consider implementing a more sophisticated tooltip system using CSS/JavaScript for richer content

### 4. Tooltip Consistency Across Platforms
**Problem**: Tooltip information may differ between CLI and web versions.
**Solution**:
- Ensure core tooltip information is consistent where applicable
- Maintain platform-appropriate implementations (text-based for CLI, graphical for web)

## Implementation Order
1. CLI Menu help (quick win, high impact for initial confusion)
2. Web help modal enhancement (visible in the promoted web version)
3. Game HelpSystem enhancement (benefits both platforms)
4. Web hover tooltips (polish)

## Testing Approach
- Verify new help options are accessible and display correctly
- Ensure existing functionality remains intact
- Check tooltip clarity with simulated beginner scenarios
- Confirm web tooltip functionality across modern browsers

## Estimated Effort
- CLI Menu help: 30 minutes
- Web help modal: 45 minutes
- HelpSystem enhancement: 60 minutes
- Web hover tooltips: 30 minutes