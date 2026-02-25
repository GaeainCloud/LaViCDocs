# HTML Review Page Standard

The HTML page should be diagram-first.

Required diagram types:

1. End-to-end business flow
2. User journey or interaction flow
3. System architecture
4. Sequence diagram for key runtime path
5. State machine for critical control object
6. Release/deployment flow

Required layout:

- Left: diagram navigation
- Center: active diagram render area
- Right: purpose, I/O, acceptance, risks

Requirements:

- Use Mermaid for diagrams.
- Map diagram to `REQ-*` tags.
- Include clear fallback note when diagram rendering fails.
- Keep mobile responsive.
