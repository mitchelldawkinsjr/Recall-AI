# Viewing Architecture Diagrams

## Quick View (Recommended)

**Open the HTML file in your browser:**
```
docs/diagrams/view-diagrams.html
```

This file contains all diagrams and will render them automatically in any web browser. Just double-click the file or open it in your browser.

## Alternative Methods

### 1. Online Mermaid Editor
1. Go to https://mermaid.live/
2. Copy the Mermaid code from any diagram file (between the ` ```mermaid ` blocks)
3. Paste into the editor
4. View the rendered diagram

### 2. VS Code/Cursor Extensions
Install one of these extensions:
- **Mermaid Preview** by vstirbu
- **Markdown Preview Mermaid Support** by Matt Bierner
- **Mermaid Editor** by Tomoyuki Aota

Then open the `.md` files and use Markdown preview (`Cmd+Shift+V` or `Ctrl+Shift+V`).

### 3. GitHub/GitLab
If your repository is on GitHub or GitLab, the diagrams will render automatically when viewing the `.md` files online.

### 4. Other Markdown Viewers
- **Mark Text**: https://marktext.app/
- **Typora**: https://typora.io/
- **Obsidian**: https://obsidian.md/

These all support Mermaid diagrams.

## Diagram Files

- `system-architecture.md` - High-level system design
- `data-flow.md` - Video processing and search flows
- `search-architecture.md` - Search system details
- `api-endpoints.md` - API structure and flows
- `database-schema.md` - Database design
- `view-diagrams.html` - **All diagrams in one HTML file (easiest to view)**

## Troubleshooting

If diagrams aren't rendering:
1. **Use the HTML file** - `view-diagrams.html` works in any browser
2. **Check Mermaid syntax** - All diagrams use valid Mermaid syntax
3. **Try online editor** - https://mermaid.live/ to verify syntax
4. **Install extension** - Make sure Mermaid extension is installed and enabled


